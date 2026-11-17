"""Value layer: mode scores (consistency / balanced / ceiling), replacement level, VORP, position and flex ranks.

Mode score per game, with lam in [-1, 1]:
    lam < 0 (consistency): mean + |lam| * 0.5 * (q25 - mean)   -> at -1 it is the average of mean and 25th pct
    lam > 0 (ceiling):     mean +  lam  * 0.5 * (q90 - mean)   -> at +1 it is the average of mean and 90th pct
Rest-of-season scores are sums of weekly scores, so the same formula applies to the summed mean/q25/q90.

Replacement level = average of the 3 best players left after filling 12 teams' starting lineups
(QB 12, RB 24, WR 24, TE 12, W/R/T 12, K 12; LB 12 from LB-eligible, D 12 from any IDP). IDP uses one level for
DL/LB/DB because the D slot takes any of them. Free-agent comparisons (Waivers tab) use the league rosters file. The page (page.py) repeats this in JavaScript so the mode slider is live.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import idp_ratings as M
from .league import TEAMS, SLOTS, FLEX_ELIG, POOL_POS, PLAYOFF_WEEKS

KEEP_N = {"QB": 40, "RB": 85, "WR": 115, "TE": 50, "K": 32, "DL": 90, "LB": 90, "DB": 110}
USAGE = ["snap", "snap_s", "tgt_sh", "tgt_sh_s", "car_sh", "car_sh_s", "rz_tgt_sh", "rz_car_sh", "att_sh",
         "ay_sh", "tkl_sh", "tkl_sh_s", "solo_sh", "sack_rate", "hit_rate", "tfl_rate", "pd_rate", "hit_rate_s", "sack_rate_s", "tfl_rate_s", "pd_rate_s", "solo_sh_s", "exp_tgt",
         "exp_car", "exp_tkl", "fga_g", "fgyd_g"]
CONS = ["roll_mean", "roll_sd", "roll_q20", "roll_q80", "rate_start", "rate_boom", "rate_bust", "cv", "cons_n",
        "ppg", "ppg_s"]


def mode_score(mean, q25, q90, lam):
    mean, q25, q90 = map(np.asarray, (mean, q25, q90))
    return np.where(lam < 0, mean + (-lam) * 0.5 * (q25 - mean), mean + lam * 0.5 * (q90 - mean))


def replacement(df: pd.DataFrame, score: str, pool: str, use_rosters: bool) -> dict:
    out = {}
    if use_rosters:
        for pos in POOL_POS[pool]:
            fa = df[(df.pos == pos) & df.owner.isna()][score].nlargest(3)
            out[pos] = float(fa.mean()) if len(fa) else 0.0
        return out
    used, cnt = set(), {k: v * TEAMS for k, v in SLOTS[pool].items()}
    for i, r in df.sort_values(score, ascending=False).iterrows():
        slots = [r.pos] if r.pos in cnt else []
        if pool == "idp" and r.lb_elig:
            slots = ["LB"]
        slots += [s for s, el in FLEX_ELIG.items() if s in cnt and r.pos in el]
        for s in slots:
            if cnt.get(s, 0) > 0:
                cnt[s] -= 1
                used.add(i)
                break
    rest = df.drop(index=list(used))
    if pool == "idp":   # the D slot takes any IDP, so one replacement level for the pool
        lvl = float(rest[score].nlargest(3).mean() or 0.0)
        return {pos: lvl for pos in POOL_POS[pool]}
    for pos in POOL_POS[pool]:
        out[pos] = float(rest[rest.pos == pos][score].nlargest(3).mean() or 0.0)
    return out


def assemble(R: pd.DataFrame, S_hist: pd.DataFrame, yahoo: pd.DataFrame, W: int, cur: int) -> dict:
    QC = ["q10", "q25", "q50", "q75", "q90"]
    wk = R[R.week == W].set_index("player_id")
    g = R.groupby("player_id")
    QS5 = ["q10", "q25", "q50", "q75", "q90"]
    ros = g[["mean"] + QS5].sum().add_prefix("ros_")
    ros["ros_games"] = g.size()
    ros["ros_avail"] = g.avail.mean()
    ros["ros_p_start"] = g.p_start.mean()
    ros["ros_p_boom"] = g.p_boom.mean()
    po = R[R.week.isin(PLAYOFF_WEEKS)].groupby("player_id")[["mean"] + QS5].sum().add_prefix("po_")
    po["po_games"] = R[R.week.isin(PLAYOFF_WEEKS)].groupby("player_id").size()
    base = g[["player_display_name", "pos", "team"]].first()
    T = base.join(ros).join(po)
    T = T.join(wk[["opp", "home", "implied", "avail", "mean"] + QC + ["p_start", "p_boom"]].add_prefix("w_"))
    last = S_hist.sort_values("t").groupby("player_id").tail(1).set_index("player_id")
    T = T.join(last[[c for c in USAGE + CONS if c in last]])
    # season game log (this season, weeks 1..W-1; None = no game)
    lg = S_hist[S_hist.season == cur].pivot_table(index="player_id", columns="week", values="fpts", aggfunc="sum")
    T["log"] = [[(None if pd.isna(v) else round(float(v), 1)) for v in lg.loc[i].reindex(range(1, W)).values]
                if i in lg.index else [None] * (W - 1) for i in T.index]
    # Yahoo ownership / eligibility
    T["key"] = T.player_display_name.map(M.norm_name)
    if len(yahoo):
        y = yahoo.set_index("key")
        T["owner"] = T.key.map(y.owner)
        T["mine"] = T.key.map(y.mine).fillna(False).astype(bool)
        T["ypos"] = T.key.map(y.positions).fillna("")
        T["ystatus"] = T.key.map(y.status).fillna("")
    else:
        T["owner"], T["mine"], T["ypos"], T["ystatus"] = None, False, "", ""
    T["lb_elig"] = (T.pos == "LB") | T.ypos.str.contains("LB")
    T["pool"] = np.where(T.pos.isin(["DL", "LB", "DB"]), "idp", "offense")
    # keep the relevant part of each position
    T = T.sort_values("ros_mean", ascending=False)
    T = T[T.groupby("pos").cumcount() < T.pos.map(KEEP_N).fillna(50)]

    # python-side values for the CSV (page recomputes live)
    use_rosters = False   # value = points above a fringe starter (12-team starting-lineup fill); FA comparisons live on the page
    for lam, tag in [(-1, "cons"), (0, "bal"), (1, "ceil")]:
        T[f"ros_score_{tag}"] = mode_score(T.ros_mean, T.ros_q25, T.ros_q90, lam)
        T[f"w_score_{tag}"] = mode_score(T.w_mean, T.w_q25, T.w_q90, lam)
        for pool in ["offense", "idp"]:
            m = T.pool == pool
            rep = replacement(T[m], f"ros_score_{tag}", pool, use_rosters)
            T.loc[m, f"ros_vorp_{tag}"] = T.loc[m, f"ros_score_{tag}"] - T.loc[m, "pos"].map(rep)
        T[f"pos_rank_{tag}"] = T.groupby("pos")[f"ros_score_{tag}"].rank(ascending=False, method="first")
        T[f"pool_rank_{tag}"] = T.groupby("pool")[f"ros_vorp_{tag}"].rank(ascending=False, method="first")
    T = T.reset_index().rename(columns={"player_display_name": "name", "index": "player_id"})

    def clean(v):
        if isinstance(v, (list, tuple)):
            return v
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        if isinstance(v, (np.floating, float)):
            return round(float(v), 3)
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.bool_,)):
            return bool(v)
        return v
    pcols = (["player_id", "name", "pos", "team", "pool", "owner", "mine", "ypos", "ystatus", "lb_elig", "log"]
             + [c for c in T.columns if c.startswith(("ros_", "po_", "w_")) and "_score_" not in c and "_vorp_" not in c]
             + [c for c in USAGE + CONS if c in T])
    players = [{c: clean(r[c]) for c in pcols} for _, r in T.iterrows()]
    table = T.drop(columns=["log", "key"])
    return {"table": table, "players": players}
