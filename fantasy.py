"""Weekly offense + IDP dashboard data, start/sit, optimal lineup, and waiver suggestions.

Usage: python fantasy.py --week 8
Inputs : yahoo_offense_available_week<N>.md, yahoo_league_week<N>.md (IDP lists), roster.json (edit when your roster changes),
         ratings_week<N>.csv + boom_week<N>.csv (from idp_ratings.py / boom.py).
Outputs: offense_week<N>.csv (Yahoo tags applied), lineup_week<N>.csv, waivers_week<N>.csv, dashboard_data_week<N>.json
"""
import argparse, json, os, re, itertools, datetime as dt
import numpy as np, pandas as pd
import warnings; warnings.filterwarnings("ignore")
import idp_ratings as M
import offense as O
from idp_ratings import norm_name
from streamers import parse_league

HERE = os.path.dirname(os.path.abspath(__file__))
YT = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS"}
LAST_WEEK = 17
IR_WEEKS_OUT = 4          # IR-tagged player assumed out at least this many weeks (return date unknown)
OFF_POS = ["QB", "RB", "WR", "TE", "K"]


def team_code(t):
    t = t.strip().upper()
    return YT.get(t, t)


def parse_offense_md(path):
    rows, sec = [], None
    for line in open(path):
        m = re.match(r"^=== (QB|RB|WR|TE|K) ", line)
        if m:
            sec = m.group(1); continue
        if sec and line.count("|") in (5, 6):
            n, t, p, pct, tag, st = [x.strip() for x in line.split("|")][:6]
            rows.append(dict(player_y=n, team=team_code(t), pos=p, pct=int(pct.rstrip("%") or 0),
                             tag="" if tag == "-" else tag, waiver="W" if st.startswith("W") else "FA", status=st))
    return pd.DataFrame(rows)


def keyer(df, name_col):
    def lk(n):
        w = norm_name(n).split()
        return f"{w[-1]}|{w[0][0]}" if w else ""
    return df[name_col].map(norm_name) + "|" + df.team, df[name_col].map(lk) + "|" + df.team


def match_ids(Y, ref, name_col="player_y"):
    """Map Yahoo rows to gsis ids in ref (index gsis_id, cols player, team); exact name, then last+initial unique."""
    k1, k2 = keyer(ref.reset_index(), "player")
    ids = ref.index.values
    m1 = pd.Series(ids, index=k1.values); m1 = m1[~m1.index.duplicated(keep=False)]
    m2 = pd.Series(ids, index=k2.values); m2 = m2[~m2.index.duplicated(keep=False)]
    y1, y2 = keyer(Y, name_col)
    return y1.map(m1).fillna(y2.map(m2))


def week_offense(D, B, W, tags):
    X = O.project(D, B, W)
    X0 = O.project(D, B, W, alpha=0.0)
    X["neutral_pts"] = X0.mean_pts.reindex(X.index)
    X["matchup_ratio"] = (X.mean_pts / X.neutral_pts.where(X.neutral_pts > 0.5)).round(3)
    X["matchup_grade"] = O.matchup_grade(X.matchup_ratio)
    X["yahoo_tag"] = X.index.map(tags).fillna("")
    no_rep = X.inj_report.isna()
    ym = X.yahoo_tag.map(O.YAHOO_TAG_MULT)
    X["p_play"] = np.where(no_rep & ym.notna(), ym.fillna(1.0) * np.where(X.missed_recent > 0, 1.0, 1.0), X.p_play)
    Sm = O.simulate(X)
    X = X.join(Sm)
    X["proj_pts"] = X.sim_mean
    X["matchup"] = np.where(X.home == 1, "vs ", "@ ") + X.opp
    return X


def ros_offense(D, B, W, Xw, tags):
    """Weeks W..17 analytic means using current rates, future opponents (no-line implied totals), byes = 0."""
    per, sos = [], []
    for w in range(W, LAST_WEEK + 1):
        gm = O.games_for_week(D, w)
        if w == W:
            v = Xw.proj_pts
            r = Xw.matchup_ratio
        else:
            Xa = O.project(D, B, W, gm=gm); Xn = O.project(D, B, W, gm=gm, alpha=0.0)
            v = Xa.mean_pts
            r = Xa.mean_pts / Xn.mean_pts.reindex(Xa.index).where(lambda s: s > 0.5)
            t = v.index.map(tags).fillna("")
            out = np.isin(t, ["NA", "SUSP", "PUP"]) | (np.isin(t, ["IR", "INA"]) & (w < W + IR_WEEKS_OUT))
            v = v.where(~out, 0.0)
        per.append(v.rename(w)); sos.append(r.rename(w))
    P = pd.concat(per, axis=1).fillna(0.0)
    S = pd.concat(sos, axis=1)
    rates = O.player_rates(B, D, W)
    played = (P > 0).sum(1)
    R = pd.DataFrame({"ros_total": P.sum(1), "ros_games": played,
                      "ros_ppg": (P.sum(1) / played.where(played > 0)).fillna(0.0),
                      "ros_sos": S.iloc[:, 1:].mean(1)}, index=P.index)
    R = R.join(rates[["player", "team", "pos", "opp_trend", "season_ppg", "ppg_l3"]], how="left")
    return R, P


def team_byes(D, W):
    s = D["sched"][(D["sched"].game_type == "REG") & (D["sched"].week.between(W, LAST_WEEK))]
    teams = set(s.home_team) | set(s.away_team)
    return {t: [w for w in range(W, LAST_WEEK + 1)
                if not ((s.week == w) & ((s.home_team == t) | (s.away_team == t))).any()] for t in teams}


def best_lineup(C, key, tie):
    """C: roster offense rows (pos, key cols). Slots QB, RB×2, WR×2, TE, W/R/T, K. Brute force."""
    best, bv = None, -1e9
    by = {p: C[C.pos == p].sort_values(key, ascending=False).index.tolist()[:5] for p in OFF_POS}
    for qb in by["QB"][:2] or [None]:
        for rb in itertools.combinations(by["RB"], 2) if len(by["RB"]) >= 2 else [tuple(by["RB"])]:
            for wr in itertools.combinations(by["WR"], 2) if len(by["WR"]) >= 2 else [tuple(by["WR"])]:
                for te in by["TE"][:3] or [None]:
                    used = {qb, te, *rb, *wr}
                    flex = [i for i in C.index if C.pos[i] in ("RB", "WR", "TE") and i not in used]
                    for fx in flex or [None]:
                        for k in by["K"][:2] or [None]:
                            ids = [i for i in [qb, *rb, *wr, te, fx, k] if i is not None]
                            v = C.loc[ids, key].sum() + 1e-3 * C.loc[ids, tie].sum()
                            if v > bv:
                                bv, best = v, dict(QB=[qb], RB=list(rb), WR=list(wr), TE=[te], **{"W/R/T": [fx]}, K=[k])
    return best


def faab_range(gain_ppg, pct, budget):
    if gain_ppg >= 3: lo, hi = 0.20, 0.30
    elif gain_ppg >= 1.5: lo, hi = 0.10, 0.20
    elif gain_ppg >= 0.5: lo, hi = 0.04, 0.10
    else: return 0.0, 0.01, "$0-1 (depth only)"
    if pct >= 60:  # widely rostered -> likely contested
        lo, hi = lo * 1.25, hi * 1.25
    return lo, hi, f"${max(1, round(lo * budget))}-{max(1, round(hi * budget))} ({lo:.0%}-{hi:.0%} of ${budget})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int)
    ap.add_argument("--season", type=int)
    a = ap.parse_args()
    season = a.season or M.nfl.get_current_season()
    D = M.load_data(season)
    W = a.week or M.detect_week(D["sched"])
    B = O.build(D)
    cfg = json.load(open(os.path.join(HERE, "roster.json")))
    budget = cfg["faab"]
    Y = parse_offense_md(os.path.join(HERE, f"yahoo_offense_available_week{W}.md"))
    rates = O.player_rates(B, D, W)

    # ---- ids + tags
    Y["gsis_id"] = match_ids(Y, rates[["player", "team"]])
    R0 = pd.DataFrame(cfg["offense"]).rename(columns={"name": "player_y"})
    R0["gsis_id"] = match_ids(R0, rates[["player", "team"]])
    tags = {**{g: t for g, t in zip(Y.gsis_id, Y.tag) if pd.notna(g) and t},
            **{g: t for g, t in zip(R0.gsis_id, R0.get("tag", pd.Series([""] * len(R0))).fillna("")) if pd.notna(g) and t}}
    print("unmatched yahoo offense:", Y[Y.gsis_id.isna() & (Y.pct > 0)].player_y.tolist())
    print("roster ids:", dict(zip(R0.player_y, R0.gsis_id)))

    # ---- week projections (Yahoo tags applied where no NFL report)
    X = week_offense(D, B, W, tags)
    X = X[(X.proj_pts > 0.3) | (X.pos == "K")]
    X = X[~((X.pos == "K") & (X.m_fga == 0))].copy()
    X["rank_pos"] = X.groupby("pos").proj_pts.rank(ascending=False, method="first").astype(int)
    ros, Pw = ros_offense(D, B, W, X, tags)
    X = X.join(ros[["ros_total", "ros_ppg", "ros_games", "ros_sos"]])
    cols = ["rank_pos", "pos", "player", "team", "matchup", "gameday", "implied", "proj_pts", "sim_median", "floor_p10",
            "p90", "p_ge15", "p_ge20", "p_ge25", "p_boom", "boom_thr", "matchup_grade", "matchup_ratio", "p_play",
            "inj_report", "yahoo_tag", "snap", "tsh", "csh", "rzsh", "i10sh", "qsh", "adot", "m_tgt", "m_rec", "m_recyd",
            "m_rectd", "m_car", "m_rushyd", "m_rushtd", "m_att", "m_pyds", "m_ptd", "m_int", "m_fga", "m_xpa",
            "season_ppg", "median_ppg", "ppg_l3", "games", "games_ge_thr", "cv_pts", "best_game", "ppg_ex_best",
            "opp_trend", "def_pepa", "def_repa", "team_plays", "team_pr", "ros_total", "ros_ppg", "ros_games", "ros_sos"]
    X = X.sort_values(["pos", "proj_pts"], ascending=[True, False])
    X[cols].round(3).rename_axis("gsis_id").to_csv(os.path.join(HERE, f"offense_week{W}.csv"))

    byes = team_byes(D, W)

    # ---- roster start/sit + lineup
    R0["pos"] = R0.pos
    RR = R0.set_index("player_y")
    rows = []
    for nm, r in RR.iterrows():
        g = r.gsis_id
        x = X.loc[g] if pd.notna(g) and g in X.index else None
        ro = ros.loc[g] if pd.notna(g) and g in ros.index else None
        rows.append(dict(player=nm, team=r.team, pos=r.pos, gsis_id=g, tag=r.get("tag") if pd.notna(r.get("tag")) else "",
                         note=r.get("note") if pd.notna(r.get("note")) else "",
                         matchup=x.matchup if x is not None else ("BYE" if W in byes.get(r.team, []) else "-"),
                         mean=float(x.proj_pts) if x is not None else 0.0,
                         floor=float(x.floor_p10) if x is not None else 0.0,
                         median=float(x.sim_median) if x is not None else 0.0,
                         p90=float(x.p90) if x is not None else 0.0,
                         p_boom=float(x.p_boom) if x is not None else 0.0,
                         grade=x.matchup_grade if x is not None else "",
                         implied=float(x.implied) if x is not None else np.nan,
                         snap=float(x.snap) if x is not None else np.nan,
                         ros_ppg=float(ro.ros_ppg) if ro is not None else 0.0,
                         ros_total=float(ro.ros_total) if ro is not None else 0.0,
                         byes=",".join(str(b) for b in byes.get(r.team, []) if b > W)))
    C = pd.DataFrame(rows).set_index("player")
    L_safe = best_lineup(C, "mean", "floor")
    L_boom = best_lineup(C, "p90", "p_boom")
    lineup_rows = []
    for which, L in [("safe", L_safe), ("boom", L_boom)]:
        for slot, ids in L.items():
            for i in ids:
                if i is None: continue
                lineup_rows.append(dict(version=which, slot=slot, player=i, **C.loc[i].drop("gsis_id").to_dict()))
    # IDP starters
    IR_ = pd.read_csv(os.path.join(HERE, f"ratings_week{W}.csv"))
    IR_["k"] = IR_.player.map(norm_name) + "|" + IR_.team
    idp_rows = {}
    for slot, (nm, tm) in cfg["idp_start"].items():
        r = IR_[IR_.k == norm_name(nm) + "|" + tm].iloc[0]
        idp_rows[slot] = dict(player=nm, team=tm, pos=r.pos, matchup=r.matchup, mean=r.proj_pts, floor=r.floor_p10,
                              median=r.sim_median, p90=r.p90, p_boom=r.p_ge10, grade=O.matchup_grade(pd.Series([r.opp_fpa_idx]))[0],
                              snap=r.proj_snap_pct, note=r.reason)
        for which in ["safe", "boom"]:
            lineup_rows.append(dict(version=which, slot=slot, **idp_rows[slot]))
    LU = pd.DataFrame(lineup_rows)
    started_safe = set(LU[(LU.version == "safe")].player)
    started_boom = set(LU[(LU.version == "boom")].player)
    C["start_safe"] = C.index.isin(started_safe)
    C["start_boom"] = C.index.isin(started_boom)
    bench = C[~C.start_safe].copy()
    bench_rows = [dict(version="bench", slot="IR" if (r.tag in ("IR", "INA")) else "BN", player=i, **r.drop("gsis_id").to_dict())
                  for i, r in bench.iterrows()]
    LU = pd.concat([LU, pd.DataFrame(bench_rows)], ignore_index=True)
    LU.round(3).to_csv(os.path.join(HERE, f"lineup_week{W}.csv"), index=False)

    # ---- waiver suggestions (offense)
    act = C[(C.tag != "IR")]
    bars = {}
    for p in ["QB", "TE", "K"]:
        v = act[act.pos == p].ros_ppg.sort_values(ascending=False)
        bars[p] = v.iloc[0] if len(v) else 0.0
    flex = act[act.pos.isin(["RB", "WR", "TE"])].ros_ppg.sort_values(ascending=False)
    rb = act[act.pos == "RB"].ros_ppg.sort_values(ascending=False)
    wr = act[act.pos == "WR"].ros_ppg.sort_values(ascending=False)
    flex_bar = sorted([*rb.iloc[2:], *wr.iloc[2:], *act[act.pos == "TE"].ros_ppg.sort_values(ascending=False).iloc[1:]],
                      reverse=True)
    flex_bar = flex_bar[0] if flex_bar else 0.0
    bars["RB"] = min(rb.iloc[1] if len(rb) > 1 else 0, flex_bar)
    bars["WR"] = min(wr.iloc[1] if len(wr) > 1 else 0, flex_bar)
    bars["TE"] = min(bars["TE"], max(flex_bar, 0))  if False else bars["TE"]
    wk_bar = {p: C[(C.pos == p) & C.start_safe].mean_min if False else C[(C.pos == p) & C.start_safe]["mean"].min()
              for p in OFF_POS}
    # droppable: lowest ROS among active non-starters (IR players go to IR slot instead)
    drop_pool = C[(~C.start_safe) & (C.tag != "IR")].sort_values("ros_ppg")
    Yx = Y.copy()
    Yx["week_mean"] = Yx.gsis_id.map(X.proj_pts).fillna(0.0)
    Yx["week_floor"] = Yx.gsis_id.map(X.floor_p10).fillna(0.0)
    Yx["week_p90"] = Yx.gsis_id.map(X.p90).fillna(0.0)
    Yx["week_pboom"] = Yx.gsis_id.map(X.p_boom).fillna(0.0)
    Yx["matchup"] = Yx.gsis_id.map(X.matchup).fillna("BYE/-")
    Yx["grade"] = Yx.gsis_id.map(X.matchup_grade).fillna("")
    for c in ["ros_ppg", "ros_total", "ros_games", "ros_sos", "opp_trend", "season_ppg", "ppg_l3"]:
        Yx[c] = Yx.gsis_id.map(ros[c])
    Yx["bar_ros"] = Yx.pos.map(bars)
    Yx["gain_ros_ppg"] = (Yx.ros_ppg - Yx.bar_ros).round(2)
    Yx["bar_week"] = Yx.pos.map(wk_bar)
    Yx["gain_week"] = (Yx.week_mean - Yx.bar_week).round(2)
    def verdict(r):
        if pd.isna(r.ros_ppg): return "no 2026 data"
        if r.gain_ros_ppg > 0.5: return "clear ROS upgrade"
        if r.gain_ros_ppg > 0: return "toss-up (within model error)"
        if r.gain_week > 0.5: return "week-%d streamer" % W
        return "depth/bye cover"
    Yx["verdict"] = Yx.apply(verdict, axis=1)
    fa = [faab_range(g if pd.notna(g) else -1, p, budget) for g, p in zip(Yx.gain_ros_ppg, Yx.pct)]
    Yx["faab_lo_pct"] = [f[0] for f in fa]; Yx["faab_hi_pct"] = [f[1] for f in fa]
    Yx["faab"] = np.where(Yx.waiver == "W", [f[2] for f in fa], "FA - free add, no bid")
    Yx = Yx.sort_values("ros_ppg", ascending=False)
    Yx["rank_ros_pos"] = Yx.groupby("pos").ros_ppg.rank(ascending=False, method="first")
    Yx["rank_week_pos"] = Yx.groupby("pos").week_mean.rank(ascending=False, method="first")

    # ---- IDP waiver adds (ROS approx = week projection × remaining games)
    Lg = parse_league(os.path.join(HERE, f"yahoo_league_week{W}.md"))
    Lg["k"] = Lg.player_y.map(norm_name) + "|" + Lg.team
    J = Lg.merge(IR_.drop(columns=["yahoo_pos"], errors="ignore"), on=["k", "team"], how="left").dropna(subset=["proj_pts"])
    J = J.drop_duplicates("k")
    J["ros_games"] = J.team.map(lambda t: LAST_WEEK - W + 1 - len(byes.get(t, [])))
    J["ros_ppg"] = pd.to_numeric(J.proj_pts, errors="coerce").astype(float)
    J["ros_games"] = pd.to_numeric(J.ros_games).astype(float)
    J["ros_total"] = J.ros_ppg * J.ros_games
    st_lb = idp_rows["LB"]["mean"]; st_d = idp_rows["D"]["mean"]
    J["slot"] = np.where(J.yahoo_pos.str.contains("LB"), "LB/D", "D")
    J["bar"] = np.where(J.slot == "LB/D", min(st_lb, st_d), st_d)
    J["gain_ros_ppg"] = (J.ros_ppg - J.bar).round(2)
    fa = [faab_range(g, 50, budget) for g in J.gain_ros_ppg]
    J["faab"] = np.where(J.waiver.str.startswith("W"), [f[2] for f in fa], "FA - free add, no bid")
    J = J.sort_values("ros_total", ascending=False)

    # ---- assemble waivers CSV
    W1 = Yx.assign(group="offense", player=Yx.player_y)[["group", "pos", "player", "team", "waiver", "pct", "tag",
         "rank_ros_pos", "ros_ppg", "ros_total", "ros_games", "ros_sos", "opp_trend", "rank_week_pos", "week_mean",
         "week_floor", "week_p90", "week_pboom", "matchup", "grade", "bar_ros", "gain_ros_ppg", "bar_week", "gain_week",
         "verdict", "faab"]]
    J2 = J.assign(group="idp", pos=J.list, player=J.player_y, tag=J.yahoo_tag, pct=np.nan,
                  week_mean=J.proj_pts, week_floor=J.floor_p10, week_p90=J.p90, week_pboom=J.p_ge10,
                  grade=O.matchup_grade(J.opp_fpa_idx), bar_ros=J.bar, verdict=np.where(J.gain_ros_ppg > 0.3, "upgrade over starter", "depth"))
    J2["rank_ros_pos"] = J2.groupby("pos").ros_total.rank(ascending=False, method="first")
    J2["rank_week_pos"] = J2.groupby("pos").week_mean.rank(ascending=False, method="first")
    J2 = J2.reindex(columns=W1.columns)
    WV = pd.concat([W1, J2], ignore_index=True)
    WV.round(3).to_csv(os.path.join(HERE, f"waivers_week{W}.csv"), index=False)

    # roster moves (rule-based)
    moves = []
    for i, r in C.iterrows():
        if r.tag == "IR":
            moves.append(dict(type="IR", player=i, text=f"Move {i} to an IR slot (Yahoo IR; frees a bench spot, no drop needed)."))
    k = C[C.pos == "K"].sort_values("mean", ascending=False)
    if len(k) > 1:
        k2 = k.iloc[1]
        moves.append(dict(type="drop", player=k.index[1],
                          text=f"Drop candidate: {k.index[1]} (2nd K, {k2.matchup} wk{W}, ROS {k2.ros_ppg:.1f}/g); one K is enough outside bye weeks."))
    for i, r in drop_pool.head(3).iterrows():
        if r.pos != "K" and r.tag != "IR":
            moves.append(dict(type="drop?", player=i, text=f"Low-value bench: {i} ROS {r.ros_ppg:.1f}/g ({r.note or r.matchup})."))
    cover = []
    for p in ["QB", "TE", "K"]:
        mine = C[(C.pos == p) & (C.tag != "IR")]
        if len(mine) == 1:
            t = mine.iloc[0]
            if t.byes:
                cover.append(f"{p}: {mine.index[0]} bye wk {t.byes} - stream that week")
    J_top = J.head(12)

    # ---- dashboard data
    def offrow(g, x):
        return [x.player, x.team, x.pos, x.matchup, round(x.proj_pts, 1), round(x.floor_p10, 1), round(x.sim_median, 1),
                round(x.p90, 1), round(x.p_boom, 3), x.matchup_grade, None if pd.isna(x.snap) else round(x.snap, 2),
                f"{int(x.games_ge_thr)}/{int(x.games)}", None if pd.isna(x.cv_pts) else round(x.cv_pts, 2),
                round(x.ros_ppg, 1) if pd.notna(x.ros_ppg) else None, x.yahoo_tag or (x.inj_report if pd.notna(x.inj_report) else ""),
                round(x.implied, 1)]
    avail = {g: (w, p) for g, w, p in zip(Y.gsis_id, Y.waiver, Y.pct) if pd.notna(g)}
    mine_ids = set(R0.gsis_id.dropna())
    players = []
    for g, x in X.iterrows():
        if x.rank_pos > {"QB": 40, "RB": 70, "WR": 100, "TE": 45, "K": 32}[x.pos] and g not in avail and g not in mine_ids:
            continue
        st = "mine" if g in mine_ids else (avail[g][0] if g in avail else "")
        players.append(offrow(g, x) + [st, avail.get(g, (None, None))[1]])
    BM = pd.read_csv(os.path.join(HERE, f"boom_week{W}.csv"))
    Ja = {k: w for k, w in zip(Lg.k, Lg.waiver)}
    IR_["st"] = IR_.k.map(lambda k: ("W" if Ja[k].startswith("W") else "FA") if k in Ja else "")
    mine_idp = {norm_name(d["name"]) + "|" + d["team"] for d in cfg["idp"]}
    IR_.loc[IR_.k.isin(mine_idp), "st"] = "mine"
    IR_ = IR_.sort_values("proj_pts", ascending=False)
    IR_["rk"] = IR_.groupby("pos").proj_pts.rank(ascending=False, method="first")
    for _, r in IR_.iterrows():
        if r.rk > 60 and not r.st:
            continue
        tag = r.inj_report if pd.notna(r.inj_report) else ""
        players.append([r.player, r.team, r.pos, r.matchup, round(r.proj_pts, 1), round(r.floor_p10, 1), round(r.sim_median, 1),
                        round(r.p90, 1), round(r.p_ge10, 3), O.matchup_grade(pd.Series([r.opp_fpa_idx]))[0],
                        round(r.proj_snap_pct, 2), r.games_ge6, round(r.cv_pts, 2), round(r.proj_pts, 1), tag, None,
                        r.st, None, "LB" in str(r.position) or r.pos == "LB"])
    rep = open(os.path.join(HERE, "backtest_offense_latest.txt")).read() if os.path.exists(os.path.join(HERE, "backtest_offense_latest.txt")) else ""
    def lrow(r):
        return dict(slot=r.slot, player=r.player, team=r.team, pos=r.pos, matchup=r.matchup, mean=round(r["mean"], 1),
                    floor=round(r.floor, 1), p90=round(r.p90, 1), p_boom=round(r.p_boom, 3), grade=r.grade,
                    note=(r.note if isinstance(r.note, str) else ""))
    data = dict(
        week=W, season=season, generated=dt.datetime.now().strftime("%Y-%m-%d %H:%M ET"),
        league="Irene's Bush League (Yahoo 54162) - Breeces Pieces", faab=budget, waivers_clear=cfg["waivers_clear"],
        cols=["player", "team", "pos", "opp", "mean", "floor", "median", "p90", "p_boom", "grade", "snap", "useful",
              "cv", "ros", "inj", "implied", "status", "pct", "lb_elig"],
        players=players,
        lineup={v: [lrow(r) for _, r in LU[LU.version == v].iterrows()] for v in ["safe", "boom"]},
        bench=[lrow(r) for _, r in LU[LU.version == "bench"].iterrows()],
        moves=[m["text"] for m in moves] + cover + ([cfg["idp_start_note"]] if cfg.get("idp_start_note") else []),
        waivers=[dict(pos=r.pos, player=r.player, team=r.team, status=r.waiver, pct=None if pd.isna(r.pct) else int(r.pct),
                      ros=None if pd.isna(r.ros_ppg) else round(r.ros_ppg, 1), wk=round(r.week_mean, 1),
                      gain=None if pd.isna(r.gain_ros_ppg) else round(r.gain_ros_ppg, 1), verdict=r.verdict, faab=r.faab,
                      opp=r.matchup)
                 for _, r in WV.sort_values("gain_ros_ppg", ascending=False).groupby("pos").head(6).iterrows()],
        boom_thr=O.BOOM_T,
        scoring="Pass 20 yd/pt (+5 at 375), TD 4, INT -1; Rush 10 yd/pt (+5 at 180), TD 6; Rec 0.5 PPR, 10 yd/pt (+5 at 200), TD 6; FL -2; 2pt 2. K: PAT +1/-1, FG 0.1 pt per made-FG yard, missed FG 0-29 yds -1. IDP: solo .75, ast .25, sack 3, INT 5, FF 5, FR 2, TD 6, PD 1, TFL 1.5, safety 3.",
        backtest=rep,
    )
    js = json.dumps(data, separators=(",", ":"), default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else (o.item() if hasattr(o, "item") else str(o)))
    js = js.replace("NaN", "null")
    open(os.path.join(HERE, f"dashboard_data_week{W}.json"), "w").write(js)
    print(f"wrote offense/lineup/waivers/dashboard_data for week {W}; players={len(players)} json={len(js)/1e3:.0f}KB")
    print("SAFE:", L_safe); print("BOOM:", L_boom)
    print(C[["pos", "matchup", "mean", "floor", "p90", "p_boom", "grade", "ros_ppg", "byes", "start_safe", "start_boom"]].round(2).to_string())
    print("bars", bars, "wk_bar", wk_bar)
    print("\n".join(m["text"] for m in moves)); print(cover)
    print(WV[WV.group == "offense"].sort_values("gain_ros_ppg", ascending=False).head(25)[["pos", "player", "team", "waiver", "pct", "ros_ppg", "week_mean", "gain_ros_ppg", "gain_week", "verdict", "faab"]].to_string())
    print(J_top[["player_y", "team", "yahoo_pos", "waiver", "proj_pts", "ros_total", "gain_ros_ppg", "faab"]].to_string())


if __name__ == "__main__":
    main()
