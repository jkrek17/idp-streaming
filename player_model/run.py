"""Weekly + rest-of-season player rankings and values for Irene's Bush League.

    python -m player_model.run              # auto week (first week with unplayed games)
    python -m player_model.run --week 11

Writes player_values_week<N>.csv, player_values_week<N>.json (page data) and player_values.html.
"""
from __future__ import annotations
import argparse, json, os, sys, warnings
import numpy as np, pandas as pd
import idp_ratings as M
from . import data, model as Mo, features as F, value as V, page
from .league import FANTASY_LAST_WEEK, PLAYOFF_WEEKS

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QC = ["q10", "q25", "q50", "q75", "q90"]
INJ = {"Out": 0.0, "Doubtful": 0.25, "Questionable": 0.85}
YTAG = {"Q": 0.85, "D": 0.25, "O": 0.0, "IR": 0.0, "NA": 0.0, "SUSP": 0.0, "PUP": 0.0, "INA": 0.0}
TEAM_FIX = {"WSH": "WAS", "JAC": "JAX", "LVR": "LV", "OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}


def next_week(sched, season):
    s = sched[(sched.season == season)]
    pend = s[s.result.isna()]
    return int(pend.week.min())


def fit_models(X, feats, cur, W):
    """A: train <= cur-2, early-stop + calibrate on cur-1. B: train through the last completed week
    with A's iterations (x1.15 for the extra data); B uses A's isotonic calibrators."""
    out = {}
    for pool in Mo.POOLS:
        P = X[Mo.pool_mask(X, pool)]
        tr = P[(P.season >= 2019) & (P.season <= cur - 2)]
        va = P[P.season == cur - 1]
        A = Mo.PoolModel(pool, feats).fit(tr, va).calibrate(va)
        full = P[(P.season >= 2019) & ((P.season < cur) | (P.week < W))]
        B = Mo.PoolModel(pool, feats).fit(full, None, {k: int(v * 1.15) for k, v in A.iters.items()})
        B.cal = A.cal
        out[pool] = B
        print(f"{pool}: trained on {len(full):,} player-games", file=sys.stderr)
    return out


def team_strength(sched, cur, W):
    """Shrunk points for / against per team from this season's results -> lines for weeks without odds."""
    s = sched[(sched.season == cur) & (sched.week < W) & sched.result.notna()]
    h = s[["home_team", "home_score", "away_score"]].set_axis(["team", "pf", "pa"], axis=1)
    a = s[["away_team", "away_score", "home_score"]].set_axis(["team", "pf", "pa"], axis=1)
    g = pd.concat([h, a]).groupby("team").agg(pf=("pf", "sum"), pa=("pa", "sum"), n=("pf", "size"))
    mu = (g.pf.sum() / g.n.sum())
    k = 4.0
    g["pf_s"] = (g.pf + k * mu) / (g.n + k)
    g["pa_s"] = (g.pa + k * mu) / (g.n + k)
    return g, mu


def future_rows(S, D, cur, W, ros_latest):
    """One row per player per remaining week (W..17) with that player's latest state."""
    last = S.sort_values("t").groupby("player_id").tail(1)
    last = last[(last.season == cur) | ((last.season == cur - 1) & last.player_id.isin(
        ros_latest[ros_latest.status == "ACT"].gsis_id))]
    ros = ros_latest.set_index("gsis_id")
    last = last.assign(team=last.player_id.map(ros.team).fillna(last.team),
                       nfl_status=last.player_id.map(ros.status).fillna("UNK"))
    last = last[~last.nfl_status.isin(["CUT", "RET", "EXE", "UNK"])]
    last["team"] = last.team.replace(TEAM_FIX)
    sched = D["sched"]
    weeks = list(range(W, FANTASY_LAST_WEEK + 1))
    sw = sched[(sched.season == cur) & sched.week.isin(weeks)]
    tw = pd.concat([sw[["week", "home_team"]].rename(columns={"home_team": "team"}),
                    sw[["week", "away_team"]].rename(columns={"away_team": "team"})])
    R = last.drop(columns=["season", "week"]).merge(tw, on="team", how="inner")
    R["season"] = cur
    R["gap"] = (F.tcode(cur, W) - R.t - 1).clip(lower=0)     # same rest gap for every future week
    R = Mo.add_target_ctx(R, sched, D["games"])
    # fill missing Vegas lines from team strength
    g, mu = team_strength(sched, cur, W)
    est_imp = 0.5 * (R.team.map(g.pf_s) + R.opp.map(g.pa_s)) + np.where(R.home == 1, 0.75, -0.75)
    est_opp = 0.5 * (R.opp.map(g.pf_s) + R.team.map(g.pa_s)) - np.where(R.home == 1, 0.75, -0.75)
    miss = R.total_line.isna()
    R.loc[miss, "implied"] = est_imp[miss]
    R.loc[miss, "total_line"] = (est_imp + est_opp)[miss]
    R.loc[miss, "spread"] = (est_imp - est_opp)[miss]
    R["rest"] = R.rest.fillna(7)
    for c, src in [("imp_tgt", "tgt_sh"), ("imp_car", "car_sh"), ("imp_att", "att_sh"), ("imp_snap", "snap")]:
        R[c] = R.implied * R[src]
    R["imp_rz"] = R.implied * (R.rz_tgt_sh + R.rz_car_sh)
    return R


def availability(R, D, cur, W, yahoo):
    """P(plays) for each player-week from NFL roster status, injury reports, Yahoo tags and missed games."""
    a = pd.Series(1.0, index=R.index)
    inj = D["inj"]
    inj = inj[(inj.season == cur)] if "season" in inj else inj
    rep_w = inj[inj.week == W].drop_duplicates("gsis_id", keep="last").set_index("gsis_id").report_status
    rep_prev = inj[inj.week == W - 1].drop_duplicates("gsis_id", keep="last").set_index("gsis_id").report_status
    G = D["games"]
    played_prev = set(G[(G.season == cur) & (G.week == W - 1)].player_id)
    teams_prev = set(G[(G.season == cur) & (G.week == W - 1)].team)
    a0 = R.player_id.map(rep_w).map(INJ)
    missed = (~R.player_id.isin(played_prev)) & R.team.isin(teams_prev) & (R.t < F.tcode(cur, W - 1))
    a0 = a0.fillna(pd.Series(np.where(missed, 0.6, 1.0), index=R.index))
    a0 = np.where(R.player_id.map(rep_prev).eq("Out") & missed & a0.eq(1.0), 0.6, a0)
    a0 = pd.Series(a0, index=R.index)
    yk = R.player_display_name.map(M.norm_name)
    ytag = yk.map(yahoo.set_index("key").status if len(yahoo) else {}).fillna("")
    a0 = np.minimum(a0, ytag.map(YTAG).fillna(1.0))
    a0 = np.where(R.nfl_status == "INA", np.minimum(a0, 0.6), a0)
    a0 = np.where(R.nfl_status == "DEV", 0.1, a0)
    a0 = pd.Series(a0, index=R.index)
    dw = R.week - W
    a = 1 - (1 - a0) * 0.5 ** dw                    # short-term injuries heal
    ir = (R.nfl_status == "RES") | ytag.eq("IR")
    a = np.where(ir, np.where(dw < 4, 0.0, 0.5), a)
    return pd.Series(np.clip(a, 0, 1), index=R.index)


def mix_quantiles(Q: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Quantiles of a mixture: 0 points w.p. (1-a), else the model distribution."""
    levels = np.array([0.1, 0.25, 0.5, 0.75, 0.9])
    out = np.empty_like(Q)
    for i in range(len(Q)):
        if a[i] >= 0.999:
            out[i] = Q[i]
            continue
        for j, p in enumerate(levels):
            if p <= 1 - a[i]:
                out[i, j] = 0.0
            else:
                pp = (p - (1 - a[i])) / max(a[i], 1e-6)
                out[i, j] = np.interp(pp, levels, Q[i], left=Q[i, 0] - (Q[i, 1] - Q[i, 0]) * (0.1 - pp) / 0.15)
    return out


def load_yahoo(W):
    """League rosters (every team) -> owner + Yahoo eligibility + tags. Uses the newest file <= W."""
    cands = sorted([f for f in os.listdir(ROOT) if f.startswith("league_rosters_week") and f.endswith(".json")],
                   key=lambda f: int(f.split("week")[1].split(".")[0]))
    cands = [f for f in cands if int(f.split("week")[1].split(".")[0]) <= W] or cands
    if not cands:
        return pd.DataFrame(columns=["key", "owner", "positions", "status", "mine"]), None
    f = cands[-1]
    d = json.load(open(os.path.join(ROOT, f)))
    rows = []
    for t in d["teams"]:
        mine = "Jason" in str(t.get("manager", ""))
        for p in t["players"]:
            rows.append(dict(key=M.norm_name(p["name"]), owner=t["name"], positions=p.get("positions", ""),
                             status=p.get("status", ""), mine=mine, slot=p.get("slot", "")))
    return pd.DataFrame(rows).drop_duplicates("key"), f


def use_idp_threshold_model(R: pd.DataFrame, W: int) -> pd.DataFrame:
    """One IDP model for week W: take P(6+), P(12+) and expected points (all given he plays) from the threshold
    model (idp_threshold.py -> threshold_week<W>.csv) and shift this model's quantiles to its mean.
    Head-to-head at 6+/12+, 2023-2026 (scratch backtest, Nov 17): threshold model AUC within position
    0.643 / 0.666 vs this model's 0.641 / 0.660, ahead in 2023-2025 and behind in 2026; a stacked blend added
    only ~0.003. Later weeks (rest of season, playoffs) still come from this model, trained on the same 6/12 lines."""
    path = os.path.join(ROOT, f"threshold_week{W}.csv")
    if not os.path.exists(path):
        print(f"no {os.path.basename(path)}: IDP week {W} uses this model's own numbers", file=sys.stderr)
        return R
    t = pd.read_csv(path).drop_duplicates("gsis_id").set_index("gsis_id")
    m = (R.week == W) & R.pos.isin(Mo.POOLS["idp"]) & R.player_id.isin(t.index)
    pid = R.loc[m, "player_id"]
    shift = pid.map(t.xpts_play) - R.loc[m, "mean"]
    R.loc[m, ["mean"] + QC] = R.loc[m, ["mean"] + QC].add(shift, axis=0).clip(lower=0)
    R.loc[m, "p_start"] = pid.map(t.p6_play)
    R.loc[m, "p_boom"] = pid.map(t.p12_play)
    R.loc[m, "idp_v3"] = True
    R.loc[m, "v3_p_play"] = pid.map(t.p_play)
    R.loc[m, "v3_has_report"] = pid.map(t.inj_report).notna()
    print(f"IDP week {W}: {m.sum()} players from {os.path.basename(path)}", file=sys.stderr)
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int)
    ap.add_argument("--no-refresh", action="store_true")
    args = ap.parse_args()
    D = data.load(list(range(data.FIRST_SEASON, data.nfl.get_current_season() + 1)),
                  refresh_current=not args.no_refresh)
    cur = D["season"]
    W = args.week or next_week(D["sched"], cur)
    print(f"season {cur}, week {W}", file=sys.stderr)

    X, feats, S, pri = Mo.training_table(D, prior_max_season=cur - 1)
    X = X[(X.season < cur) | (X.week < W)]
    models = fit_models(X, feats, cur, W)

    ros = D["rosters"]
    # latest weekly roster row per player (teams on bye are missing from the newest week)
    ros_latest = ros.sort_values("week").drop_duplicates("gsis_id", keep="last")
    S_hist = S[(S.season < cur) | (S.week < W)]
    R = future_rows(S_hist, D, cur, W, ros_latest)
    yahoo, yfile = load_yahoo(W)

    preds = []
    for pool, pm in models.items():
        P = R[Mo.pool_mask(R, pool)]
        preds.append(P[[]].join(pm.predict(P)))
    R = R.join(pd.concat(preds))
    R["idp_v3"] = False
    R = use_idp_threshold_model(R, W)
    R["avail"] = availability(R, D, cur, W, yahoo)
    if R.idp_v3.any():
        # same play probability as the streamer lists: the threshold model's (2018-2025 history), with the Yahoo
        # tag standing in when the NFL report is not out yet (streamers.TAG_PLAY)
        from streamers import TAG_PLAY
        m = R.idp_v3
        ytag = R.loc[m, "player_display_name"].map(M.norm_name).map(
            yahoo.set_index("key").status if len(yahoo) else {}).fillna("")
        tagp = ytag.map(TAG_PLAY).astype(float)
        pp = R.loc[m, "v3_p_play"].astype(float)
        use_tag = ~R.loc[m, "v3_has_report"].astype(bool) & tagp.notna()
        R.loc[m, "avail"] = np.where(use_tag, np.minimum(pp, tagp), pp)
    a = R.avail.to_numpy()
    R[QC] = mix_quantiles(R[QC].to_numpy(), a)
    R["mean"] = R["mean"] * a
    R["p_start"] *= a
    R["p_boom"] *= a

    # optional blend with the existing offense.py weekly projection (backtest: +0.02 Spearman, -1% MAE)
    off_csv = os.path.join(ROOT, f"offense_week{W}.csv")
    R["blend"] = False
    if os.path.exists(off_csv):
        o = pd.read_csv(off_csv)
        col = next((c for c in ["proj_pts", "model", "sim_mean"] if c in o), None)
        if "gsis_id" in o and col:
            om = o.set_index("gsis_id")[col]
            m = (R.week == W) & R.player_id.isin(om.index)
            shift = 0.5 * (R.loc[m, "player_id"].map(om) - R.loc[m, "mean"])
            R.loc[m, ["mean"] + QC] = R.loc[m, ["mean"] + QC].add(shift, axis=0).clip(lower=0)
            R.loc[m, "blend"] = True
            print(f"blended {m.sum()} offense projections with {os.path.basename(off_csv)}", file=sys.stderr)

    if os.environ.get("PM_DEBUG"):
        import pickle
        pickle.dump((R, S_hist, yahoo, yfile, W, cur), open(os.path.join(data.CACHE, "run_debug.pkl"), "wb"))
    out = V.assemble(R, S_hist, yahoo, W, cur)
    stem = os.path.join(ROOT, f"player_values_week{W}")
    out["table"].to_csv(stem + ".csv", index=False)
    meta = dict(season=cur, week=W, weeks_left=list(range(W, FANTASY_LAST_WEEK + 1)),
                playoff_weeks=list(PLAYOFF_WEEKS), yahoo_file=yfile, generated=pd.Timestamp.now().isoformat(timespec="minutes"),
                blend=bool(R.blend.any()))
    if os.path.exists(os.path.join(ROOT, "player_model_backtest.txt")):
        meta["backtest"] = open(os.path.join(ROOT, "player_model_backtest.txt")).read()
    payload = dict(meta=meta, players=out["players"])
    json.dump(payload, open(stem + ".json", "w"), separators=(",", ":"))
    html = page.render(payload)
    open(os.path.join(ROOT, "player_values.html"), "w").write(html)
    print(f"wrote {stem}.csv, {stem}.json, player_values.html", file=sys.stderr)


if __name__ == "__main__":
    main()
