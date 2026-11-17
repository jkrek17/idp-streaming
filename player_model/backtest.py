"""Season-held-out backtest.

Train 2019-2024, early-stop + calibrate on 2025, test on 2026 weeks played so far (never seen in training).
Compares against simple baselines and, on the same player-weeks, the existing offense.py / idp_ratings.py
projections saved in backtest_*.csv. Writes player_model_backtest.txt and player_model_backtest.csv.

Usage: python -m player_model.backtest
"""
from __future__ import annotations
import json, os, sys, warnings
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from . import data, model as Mo, features as F

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPN = {"QB": 12, "RB": 24, "WR": 24, "TE": 12, "K": 12, "DL": 24, "LB": 24, "DB": 24}


def relevant(X):
    """Evaluation pool: players with a real role (decayed snap share >= 40% or top usage)."""
    return (X.snap >= 0.4) | (X.ppg >= X.pos.map({p: v[0] * 0.5 for p, v in F.THR.items()}))


def pinball(y, q, a):
    d = y - q
    return np.mean(np.maximum(a * d, (a - 1) * d))


def logloss(y, p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))


def week_metrics(d: pd.DataFrame, col: str, pos: str) -> dict:
    n = TOPN[pos]
    if len(d) < 8:
        return {}
    rho = spearmanr(d[col], d.fpts).statistic
    top_pred = d.nlargest(n, col)
    top_act = set(d.nlargest(n, "fpts").player_id)
    return dict(spearman=rho, hit=np.mean([p in top_act for p in top_pred.player_id]),
                top_avg=top_pred.fpts.mean(), mae=np.mean(np.abs(d[col] - d.fpts)))


def summarize(T: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows = []
    for (pos, wk), d in T.groupby(["pos", "week"]):
        for c in cols:
            m = week_metrics(d.dropna(subset=[c]), c, pos)
            if m:
                rows.append(dict(pos=pos, week=wk, model=c, **m))
    R = pd.DataFrame(rows)
    return R.groupby(["pos", "model"])[["spearman", "hit", "top_avg", "mae"]].mean()


def main():
    D = data.load(list(range(2018, 2027)), refresh_current=False)
    X, feats, S, pri = Mo.training_table(D, prior_max_season=2024)
    cur = D["season"]
    X["base_ppg"] = np.where(X.games_season > 0, np.nan, np.nan)
    # baselines: season-to-date ppg (what Yahoo's default sort shows) and decayed ppg
    S2 = S[["player_id", "season", "week", "fpts"]].copy()
    S2["cum"] = S2.groupby(["player_id", "season"]).fpts.cumsum()
    S2["n"] = S2.groupby(["player_id", "season"]).cumcount() + 1
    S2["ssn_ppg"] = S2.cum / S2.n
    prev = S2.groupby("player_id")[["ssn_ppg", "season"]].shift(1)
    X["base_ssn"] = np.where(prev.loc[X.index, "season"] == X.season, prev.loc[X.index, "ssn_ppg"], np.nan)
    X["base_decay"] = X.ppg

    out, models = [], {}
    for pool in Mo.POOLS:
        P = X[Mo.pool_mask(X, pool)]
        tr = P[(P.season >= 2019) & (P.season <= 2024)]
        va = P[P.season == 2025]
        te = P[P.season == cur].copy()
        pm = Mo.PoolModel(pool, feats).fit(tr, va).calibrate(va)
        models[pool] = pm
        pr = pm.predict(te)
        te = te.join(pr)
        te["pool"] = pool
        out.append(te)
        print(pool, "iters", pm.iters, "raw 10-90 coverage on 2025:", round(pm.cover_raw, 3), file=sys.stderr)
    T = pd.concat(out)
    T = T[relevant(T) & (T.week >= 3)]
    T["base_ssn"] = T.base_ssn.fillna(T.base_decay)

    # existing models on the same player-weeks
    ex = []
    for f in ["backtest_offense_weeks4-7.csv", "backtest_offense_weeks5-8.csv"]:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            e = pd.read_csv(p, usecols=["gsis_id", "week", "model"])
            ex.append(e)
    if ex:
        E = pd.concat(ex).drop_duplicates(["gsis_id", "week"]).rename(columns={"gsis_id": "player_id", "model": "current_model"})
        T = T.merge(E, on=["player_id", "week"], how="left")

    lines = []
    w = lines.append
    w(f"Player model backtest: trained 2019-2024, calibrated on 2025, tested on {cur} weeks "
      f"{T.week.min()}-{T.week.max()} (out of sample). Pool: players with a real role.\n")
    w("== Ranking skill (mean over weeks) ==")
    w(summarize(T, ["mean", "q50", "base_ssn", "base_decay"]).round(3).to_string())
    if "current_model" in T:
        H = T.dropna(subset=["current_model"])
        w(f"\n== Head-to-head vs current offense.py on the same {len(H)} player-weeks (weeks {min(H.week)}-{max(H.week)}) ==")
        w(summarize(H, ["mean", "current_model", "base_ssn"]).round(3).to_string())
        allpos = []
        for c in ["mean", "current_model", "base_ssn"]:
            allpos.append(dict(model=c, mae=np.mean(np.abs(H[c] - H.fpts)),
                               spearman=np.mean([spearmanr(d[c], d.fpts).statistic for _, d in H.groupby(["pos", "week"]) if len(d) > 8])))
        w(pd.DataFrame(allpos).round(3).to_string(index=False))
    w("\n== Distribution quality ==")
    rows = []
    for pos, d in T.groupby("pos"):
        y = d.fpts.to_numpy()
        thr_s, thr_b = F.THR[pos]
        ys, yb = (y >= thr_s).astype(int), (y >= thr_b).astype(int)
        base_s, base_b = ys.mean(), yb.mean()
        rows.append(dict(pos=pos, n=len(d), cover_10_90=np.mean((y >= d.q10) & (y <= d.q90)),
                         below_q25=np.mean(y < d.q25), above_q75=np.mean(y > d.q75),
                         pinball_q10=pinball(y, d.q10, .1), pinball_q90=pinball(y, d.q90, .9),
                         start_rate=base_s, p_start_mean=d.p_start.mean(),
                         ll_start=logloss(ys, d.p_start), ll_start_base=logloss(ys, np.full(len(y), base_s)),
                         boom_rate=base_b, p_boom_mean=d.p_boom.mean(),
                         ll_boom=logloss(yb, d.p_boom), ll_boom_base=logloss(yb, np.full(len(y), base_b))))
    w(pd.DataFrame(rows).round(3).to_string(index=False))
    w("\n== Calibration of P(start-worthy week), all positions ==")
    T["bin"] = pd.cut(T.p_start, [0, .1, .2, .3, .4, .5, .6, .7, .8, 1])
    w(T.groupby("bin", observed=True).apply(lambda d: pd.Series(dict(n=len(d), pred=d.p_start.mean(),
                                                         obs=(d.fpts >= d.pos.map({p: v[0] for p, v in F.THR.items()})).mean())))
      .round(3).to_string())
    w("\n== Top features (gain, mean model) ==")
    for pool, pm in models.items():
        m = pm.models["mean"]
        imp = pd.Series(m.feature_importance("gain"), index=feats).sort_values(ascending=False)
        w(f"{pool}: " + ", ".join(f"{k} {v / imp.sum():.0%}" for k, v in imp.head(12).items()))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(ROOT, "player_model_backtest.txt"), "w").write(txt + "\n")
    keep = ["player_id", "player_display_name", "pos", "team", "season", "week", "fpts", "mean", "q10", "q25",
            "q50", "q75", "q90", "p_start", "p_boom", "base_ssn", "base_decay"] + (["current_model"] if "current_model" in T else [])
    T[keep].to_csv(os.path.join(ROOT, "player_model_backtest.csv"), index=False)
    json.dump({p: m.iters for p, m in models.items()}, open(os.path.join(ROOT, "player_model_iters.json"), "w"))


if __name__ == "__main__":
    main()
