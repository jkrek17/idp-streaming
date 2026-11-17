#!/usr/bin/env python3
"""Offensive (QB/RB/WR/TE/K) weekly projections + Monte Carlo, same philosophy as the IDP model.

Opportunity first: team volume (plays, pass rate, from Vegas implied totals + pace) x player share
(targets, carries, red-zone targets, inside-10 carries, pass attempts), times shrunk efficiency, times
opponent-adjusted defense factors. Touchdowns are allocated from Vegas-implied team TDs by red-zone /
goal-line share, not from a player's own TD history. Per-play yardage is capped (40 rush/rec, 50 pass)
so one long play doesn't drive efficiency.

Usage: python offense.py [--week N] [--backtest 4-7]
"""
from __future__ import annotations
import argparse, sys
import numpy as np, pandas as pd
import idp_ratings as M

# ---- Irene's Bush League scoring (from yahoo_offense_available_week8.md) ----
SCORING = dict(pass_yd=1/20, pass_td=4, int=-1, rush_yd=1/10, rush_td=6, rec=0.5, rec_yd=1/10, rec_td=6,
               ret_td=6, two_pt=2, fum_lost=-2, fum_ret_td=6,
               bonus_pass=(375, 5), bonus_rush=(180, 5), bonus_rec=(200, 5),
               pat_made=1, pat_miss=-1, fg_yd=1/10, fg_miss_0_29=-1)
P = dict(decay=0.8, recent_w=0.5, alpha=0.8, clip=(0.75, 1.30), m_def=3.0,
         k_tgt=12, k_car=10, k_rz=6, k_i10=4, k_qb=8, k_catch=30, k_ypt=40, k_ypc=50, k_ypa=150,
         k_int=300, k_fl=300, rz_w=0.55, i10_w=0.6, fav_pass=0.006,
         cap_rush=40, cap_rec=40, cap_pass=50,
         vacated=1.0, adot_w=0.15, wr_rush_td="rate", qb_w=1.0)  # vacated: scale target games by teammates' absence
SIM = dict(n=5000, seed=11, cv_plays=0.12, cv_score=0.55, size_tgt=4.0, size_car=5.0, size_att=25.0,
           cv_rec=0.95, sd_carry=7.0, cv_comp=0.80, cv_fga=0.35)
BOOM_T = {"QB": 25, "RB": 20, "WR": 20, "TE": 15, "K": 12}
POS = ["QB", "RB", "WR", "TE"]
INJ_MULT = {"Out": 0.0, "Doubtful": 0.25, "Questionable": 0.85}
YAHOO_TAG_MULT = {"Q": 0.85, "D": 0.25, "O": 0.0, "IR": 0.0, "NA": 0.0, "SUSP": 0.0, "PUP": 0.0, "INA": 0.0}


# ============================================================================ data
def score_actual(ps: pd.DataFrame) -> pd.Series:
    s, f = SCORING, (lambda c: ps[c].fillna(0) if c in ps else 0)
    pts = (f("passing_yards") * s["pass_yd"] + f("passing_tds") * s["pass_td"] + f("passing_interceptions") * s["int"]
           + f("rushing_yards") * s["rush_yd"] + f("rushing_tds") * s["rush_td"]
           + f("receptions") * s["rec"] + f("receiving_yards") * s["rec_yd"] + f("receiving_tds") * s["rec_td"]
           + f("special_teams_tds") * s["ret_td"] + f("fumble_recovery_tds") * s["fum_ret_td"]
           + (f("passing_2pt_conversions") + f("rushing_2pt_conversions") + f("receiving_2pt_conversions")) * s["two_pt"]
           + (f("rushing_fumbles_lost") + f("receiving_fumbles_lost") + f("sack_fumbles_lost")) * s["fum_lost"]
           + (f("passing_yards") >= s["bonus_pass"][0]) * s["bonus_pass"][1]
           + (f("rushing_yards") >= s["bonus_rush"][0]) * s["bonus_rush"][1]
           + (f("receiving_yards") >= s["bonus_rec"][0]) * s["bonus_rec"][1])
    kp = (f("pat_made") * s["pat_made"] + f("pat_missed") * s["pat_miss"] + f("fg_made_distance") * s["fg_yd"]
          + (f("fg_missed_0_19") + f("fg_missed_20_29")) * s["fg_miss_0_29"])
    return np.where(ps.position == "K", kp, pts)


def build(D: dict) -> dict:
    """Per team-game and player-game opportunity tables from pbp (computed once per season)."""
    pb = D["pbp"]
    pb = pb[pb.play_type.isin(["pass", "run"]) & (pb.two_point_attempt.fillna(0) == 0) & pb.posteam.notna()].copy()
    num = lambda c: pb[c].fillna(0).astype(float)
    pb["is_att"] = ((num("pass_attempt") == 1) & (num("sack") == 0)).astype(float)
    pb["is_rush"] = (num("rush_attempt") == 1).astype(float)
    pb["is_db"] = num("qb_dropback")
    pb["rz"] = (pb.yardline_100 <= 20).astype(float)
    pb["i10"] = (pb.yardline_100 <= 10).astype(float)
    pb["pyds"] = num("passing_yards").clip(upper=P["cap_pass"]) * pb.is_att
    pb["ryds"] = num("rushing_yards").clip(upper=P["cap_rush"]) * pb.is_rush
    pb["ptd"], pb["rtd"] = num("pass_touchdown"), num("rush_touchdown")
    pb["intc"], pb["sk"], pb["scr"] = num("interception"), num("sack"), num("qb_scramble")
    pb["pepa"] = num("epa") * pb.is_db
    pb["repa"] = num("epa") * pb.is_rush * (1 - pb.scr)
    pb["dsr"] = pb.is_rush * (1 - pb.scr)
    keys = ["game_id", "week", "posteam", "defteam"]
    TG = pb.groupby(keys).agg(plays=("is_db", "size"), db=("is_db", "sum"), att=("is_att", "sum"),
                              rush=("is_rush", "sum"), dsr=("dsr", "sum"), pyds=("pyds", "sum"), ryds=("ryds", "sum"),
                              ptd=("ptd", "sum"), rtd=("rtd", "sum"), intc=("intc", "sum"), sk=("sk", "sum"),
                              scr=("scr", "sum"), pepa=("pepa", "sum"), repa=("repa", "sum")).reset_index()
    rz_t = pb[(pb.is_att == 1) & pb.receiver_player_id.notna()]
    TG = TG.merge(rz_t.groupby(keys).rz.sum().rename("rz_tgt").reset_index(), on=keys, how="left")
    TG = TG.merge(pb[pb.is_rush == 1].groupby(keys).i10.sum().rename("i10_car").reset_index(), on=keys, how="left")
    # kicking per team-game
    kk = D["pbp"][D["pbp"].season_type == "REG"]
    fg = kk[kk.field_goal_attempt == 1]
    xp = kk[kk.extra_point_attempt == 1]
    TG = TG.merge(fg.groupby(keys).size().rename("fga").reset_index(), on=keys, how="left")
    TG = TG.merge(xp.groupby(keys).size().rename("xpa").reset_index(), on=keys, how="left")
    sch = D["sched"][D["sched"].game_type == "REG"]
    pts = pd.concat([sch[["game_id", "home_team", "home_score"]].set_axis(["game_id", "posteam", "pts"], axis=1),
                     sch[["game_id", "away_team", "away_score"]].set_axis(["game_id", "posteam", "pts"], axis=1)])
    TG = TG.merge(pts, on=["game_id", "posteam"], how="left").fillna(0)
    # player-game
    rec = pb[(pb.is_att == 1) & pb.receiver_player_id.notna()].assign(
        cmp=lambda d: d.complete_pass.fillna(0), ryd=lambda d: d.receiving_yards.fillna(0).clip(upper=P["cap_rec"]),
        air=lambda d: d.air_yards.fillna(0))
    R = rec.groupby(["game_id", "receiver_player_id"]).agg(tgt=("is_att", "sum"), rec=("cmp", "sum"),
                                                           recyd=("ryd", "sum"), air=("air", "sum"), rz_tgt=("rz", "sum"),
                                                           rectd=("ptd", "sum")).reset_index().rename(columns={"receiver_player_id": "gsis_id"})
    ru = pb[(pb.is_rush == 1) & pb.rusher_player_id.notna()]
    U = ru.groupby(["game_id", "rusher_player_id"]).agg(car=("is_rush", "sum"), rushyd=("ryds", "sum"),
                                                        i10_car=("i10", "sum"), rushtd=("rtd", "sum")).reset_index().rename(columns={"rusher_player_id": "gsis_id"})
    pa = pb[(pb.is_db == 1) & (pb.scr == 0) & pb.passer_player_id.notna()].assign(cmp=lambda d: d.complete_pass.fillna(0))
    Q = pa.groupby(["game_id", "passer_player_id"]).agg(db=("is_db", "sum"), att=("is_att", "sum"), cmp=("cmp", "sum"),
                                                        pyds=("pyds", "sum"), ptd=("ptd", "sum"), intc=("intc", "sum"),
                                                        sk=("sk", "sum")).reset_index().rename(columns={"passer_player_id": "gsis_id"})
    ps = D["ps"].copy()
    ps["position"] = ps.position.replace({"FB": "RB"})
    ps = ps[ps.position.isin(POS + ["K"])]
    ps["fpts"] = score_actual(ps)
    ps["fl"] = ps[["rushing_fumbles_lost", "receiving_fumbles_lost", "sack_fumbles_lost"]].fillna(0).sum(axis=1)
    G = ps[["player_id", "player_display_name", "position", "team", "opponent_team", "week", "game_id", "fpts", "fl",
            "fg_att", "fg_made", "pat_att", "pat_made"]].rename(columns={"player_id": "gsis_id", "player_display_name": "player"})
    for t in (R, U, Q.rename(columns={"db": "q_db", "att": "q_att", "cmp": "q_cmp", "sk": "q_sk"})):
        G = G.merge(t, on=["game_id", "gsis_id"], how="left")
    sn = D["snaps"][["game_id", "gsis_id", "offense_snaps", "offense_pct"]].dropna(subset=["gsis_id"]).drop_duplicates(["game_id", "gsis_id"])
    G = G.merge(sn, on=["game_id", "gsis_id"], how="left")
    num_cols = [c for c in G.columns if c not in ("gsis_id", "player", "position", "team", "opponent_team", "game_id")]
    G[num_cols] = G[num_cols].fillna(0)
    G = G.merge(TG.drop(columns=["defteam"]).add_prefix("t_").rename(columns={"t_game_id": "game_id", "t_posteam": "team", "t_week": "week"}),
                on=["game_id", "team", "week"], how="left")
    # positional receiving per team-game (for coverage tendencies)
    pos_map = G.drop_duplicates("gsis_id").set_index("gsis_id").position
    rec["pos"] = rec.receiver_player_id.map(pos_map)
    PR = rec[rec.pos.isin(["WR", "TE", "RB"])].groupby(keys + ["pos"]).agg(tgt=("is_att", "sum"), yds=("ryd", "sum")).reset_index()
    return dict(TG=TG, G=G, PR=PR, fg=fg, xp=xp)


# ============================================================================ helpers
def wts(week_col, W):
    return P["decay"] ** (W - 1 - week_col)


def team_tables(B: dict, W: int):
    TG = B["TG"][B["TG"].week < W].copy()
    TG["w"] = wts(TG.week, W)
    lg = {c: TG[c].sum() for c in ["plays", "db", "att", "rush", "pyds", "ryds", "ptd", "rtd", "intc", "sk", "scr",
                                   "pepa", "repa", "dsr", "fga", "xpa", "pts", "rz_tgt", "i10_car"]}
    ng = len(TG)
    L = dict(plays=lg["plays"] / ng, pr=lg["db"] / lg["plays"], ypa=lg["pyds"] / lg["att"], ypc=lg["ryds"] / lg["rush"],
             ptd_sh=lg["ptd"] / (lg["ptd"] + lg["rtd"]), td_per_pt=(lg["ptd"] + lg["rtd"]) / lg["pts"],
             int_r=lg["intc"] / lg["att"], sk_r=lg["sk"] / lg["db"], scr_r=lg["scr"] / lg["db"], fga=lg["fga"] / ng,
             xpa_per_td=lg["xpa"] / (lg["ptd"] + lg["rtd"]), ppg=lg["pts"] / ng,
             pepa=lg["pepa"] / lg["db"], repa=lg["repa"] / lg["dsr"])
    # offense (shrunk) rates
    def agg(df, by):
        g = df.assign(**{c + "_w": df[c] * df.w for c in lg}).groupby(by)
        return g[[c + "_w" for c in lg] + ["w"]].sum().rename(columns=lambda c: c.replace("_w", "") if c != "w" else "w")
    O = agg(TG, "posteam")
    k = 2.0
    OFF = pd.DataFrame({
        "plays": (O.plays + k * L["plays"]) / (O.w + k),
        "pr": (O.db + 60 * L["pr"]) / (O.plays + 60),
        "ypa": (O.pyds + 150 * L["ypa"]) / (O.att + 150),
        "ypc": (O.ryds + 100 * L["ypc"]) / (O.rush + 100),
        "ptd_sh": (O.ptd + 6 * L["ptd_sh"]) / (O.ptd + O.rtd + 6),
        "sk_r": (O.sk + 80 * L["sk_r"]) / (O.db + 80),
        "scr_r": (O.scr + 80 * L["scr_r"]) / (O.db + 80),
        "fga": (O.fga + 3 * L["fga"]) / (O.w + 3),
        "ppg": (O.pts + k * L["ppg"]) / (O.w + k),
        "pepa": O.pepa / O.db, "repa": O.repa / O.dsr})
    # defense: opponent-adjusted ratios (allowed vs what those offenses usually do)
    T2 = TG.merge(OFF[["plays", "pr", "ypa", "ypc", "sk_r", "pepa", "repa"]].add_prefix("o_"), left_on="posteam", right_index=True)
    off_ppg_raw = (O.pts / O.w)
    T2["o_ppg"] = T2.posteam.map(off_ppg_raw)
    T2["o_int"] = L["int_r"]
    T2["o_ptdr"] = L["ptd_sh"] * L["td_per_pt"] * T2.posteam.map(off_ppg_raw) / T2.posteam.map(O.att / O.w)
    T2["o_rtdr"] = (1 - L["ptd_sh"]) * L["td_per_pt"] * T2.posteam.map(off_ppg_raw) / T2.posteam.map(O.rush / O.w)
    T2["e_plays"], T2["e_db"] = T2.o_plays, T2.plays * T2.o_pr
    T2["e_pyds"], T2["e_ryds"] = T2.att * T2.o_ypa, T2.rush * T2.o_ypc
    T2["e_ptd"], T2["e_rtd"] = T2.att * T2.o_ptdr, T2.rush * T2.o_rtdr
    T2["e_intc"], T2["e_sk"], T2["e_pts"] = T2.att * T2.o_int, T2.db * T2.o_sk_r, T2.o_ppg
    T2["e_pepa"], T2["e_repa"] = T2.db * T2.o_pepa, T2.dsr * T2.o_repa
    stats = ["plays", "db", "pyds", "ryds", "ptd", "rtd", "intc", "sk", "pts"]
    DEF = {}
    m = P["m_def"]
    for s in stats:
        a = (T2[s] * T2.w).groupby(T2.defteam).sum()
        e = (T2["e_" + s] * T2.w).groupby(T2.defteam).sum()
        ebar = (T2["e_" + s]).groupby(T2.defteam).mean()
        DEF[s] = (a + m * ebar) / (e + m * ebar)
    for s in ["pepa", "repa"]:  # EPA allowed over expectation per play (additive)
        a = ((T2[s] - T2["e_" + s]) * T2.w).groupby(T2.defteam).sum()
        v = (T2.db if s == "pepa" else T2.dsr) * T2.w
        DEF[s] = a / (v.groupby(T2.defteam).sum() + 150)
    DEF = pd.DataFrame(DEF)
    DEF["ppg_allowed"] = (TG.pts * TG.w).groupby(TG.defteam).sum() / TG.w.groupby(TG.defteam).sum()
    # coverage tendencies: share of targets + yards/target to each position group, vs league
    PR = B["PR"][B["PR"].week < W].copy()
    PR["w"] = wts(PR.week, W)
    tot = (PR.tgt * PR.w).groupby(PR.defteam).sum()
    lg_sh = PR.groupby("pos").tgt.sum() / PR.tgt.sum()
    lg_ypt = PR.groupby("pos").yds.sum() / PR.groupby("pos").tgt.sum()
    for pos in ["WR", "TE", "RB"]:
        x = PR[PR.pos == pos]
        t = (x.tgt * x.w).groupby(x.defteam).sum().reindex(DEF.index).fillna(0)
        y = (x.yds * x.w).groupby(x.defteam).sum().reindex(DEF.index).fillna(0)
        DEF[f"tsh_{pos}"] = ((t + 60 * lg_sh[pos]) / (tot.reindex(DEF.index) + 60)) / lg_sh[pos]
        DEF[f"ypt_{pos}"] = ((y + 40 * lg_ypt[pos]) / (t + 40)) / lg_ypt[pos]
    return L, OFF, DEF


def fac(r, alpha=None):
    a = P["alpha"] if alpha is None else alpha
    return np.clip(1 + a * (r - 1), *P["clip"])


def games_for_week(D: dict, W: int) -> pd.DataFrame:
    s = D["sched"][(D["sched"].game_type == "REG") & (D["sched"].week == W)]
    rows = []
    for g in s.itertuples():
        sp = g.spread_line if pd.notna(g.spread_line) else np.nan
        tot = g.total_line if pd.notna(g.total_line) else np.nan
        rows.append(dict(team=g.home_team, opp=g.away_team, home=1, fav=sp, total=tot, gameday=g.gameday, game_id=g.game_id))
        rows.append(dict(team=g.away_team, opp=g.home_team, home=0, fav=-sp if pd.notna(sp) else np.nan, total=tot,
                         gameday=g.gameday, game_id=g.game_id))
    return pd.DataFrame(rows)


def team_context(GM: pd.DataFrame, L: dict, OFF: pd.DataFrame, DEF: pd.DataFrame, alpha=None) -> pd.DataFrame:
    """Expected team volume and TDs for each (team, opp) row. Missing Vegas -> implied from ppg vs ppg allowed."""
    C = GM.copy()
    o, d = OFF.reindex(C.team), DEF.reindex(C.opp)
    est = 0.5 * (o.ppg.values + d.ppg_allowed.values)
    no_line = C.total.isna()
    C["implied"] = np.where(no_line, est, C.total / 2 + C.fav / 2)
    C["fav"] = C.fav.fillna(0)
    C["plays"] = o.plays.values * fac(d.plays.values, (alpha if alpha is not None else P["alpha"]) * 0.5)
    C["pr"] = np.clip(o.pr.values * fac(d.db.values / d.plays.values, alpha) - P["fav_pass"] * C.fav, 0.40, 0.75)
    C["db"] = C.plays * C.pr
    C["sk_r"] = o.sk_r.values * fac(d.sk.values / d.db.values, alpha)
    C["scr_r"] = o.scr_r.values
    C["att"] = C.db * (1 - C.sk_r - C.scr_r)
    C["rush"] = C.plays - C.db + C.db * C.scr_r
    C["f_ypa"] = fac(d.pyds.values / d.db.values * 1.0, alpha)  # yards allowed per opportunity
    C["f_ypc"] = fac(d.ryds.values / d.plays.values * d.plays.values, alpha) if False else fac(d.ryds.values, alpha)
    C["f_int"] = fac(d.intc.values, alpha)
    tds = C.implied * L["td_per_pt"]
    psh = o.ptd_sh.values * fac(d.ptd.values, alpha)
    rsh = (1 - o.ptd_sh.values) * fac(d.rtd.values, alpha)
    C["ptd"], C["rtd"] = tds * psh / (psh + rsh), tds * rsh / (psh + rsh)
    C["fga"] = o.fga.values * np.sqrt(np.clip(C.implied / L["ppg"], 0.5, 1.6))
    C["xpa"] = tds * L["xpa_per_td"]
    for pos in ["WR", "TE", "RB"]:
        C[f"tsh_{pos}"] = fac(d[f"tsh_{pos}"].values, alpha)
        C[f"ypt_{pos}"] = fac(d[f"ypt_{pos}"].values, alpha) * np.sqrt(C.f_ypa)
    C["def_pepa"], C["def_repa"] = d.pepa.values, d.repa.values
    return C


# ============================================================================ players
def player_rates(B: dict, D: dict, W: int) -> pd.DataFrame:
    G = B["G"][B["G"].week < W].copy()
    G = G[(G.offense_snaps > 0) | (G.tgt + G.car + G.q_db + G.fg_att + G.pat_att > 0)]
    G["w"] = wts(G.week, W)
    G["w"] = G.w / G.groupby("gsis_id").w.transform("mean")  # weights average 1 per player -> k in game units
    last = G.sort_values("week").groupby("gsis_id").tail(1).set_index("gsis_id")
    pos = last.position
    # league per-position efficiency priors
    pri = {}
    for p in ["QB", "RB", "WR", "TE"]:
        x = G[G.position == p]
        pri[p] = dict(catch=x.rec.sum() / max(x.tgt.sum(), 1), ypt=x.recyd.sum() / max(x.tgt.sum(), 1),
                      adot=x.air.sum() / max(x.tgt.sum(), 1), ypc=x.rushyd.sum() / max(x.car.sum(), 1),
                      fl=x.fl.sum() / max((x.car + x.rec + x.q_db).sum(), 1),
                      rtd_car=x.rushtd.sum() / max(x.car.sum(), 1))
    qb = G[G.position == "QB"]
    pri_q = dict(ypa=qb.pyds.sum() / qb.q_att.sum(), cmp=qb.q_cmp.sum() / qb.q_att.sum(), int=qb.intc.sum() / qb.q_att.sum())
    G["t_att"], G["t_rush"] = G.t_att.clip(lower=1), G.t_rush.clip(lower=1)
    G["t_rz_tgt"], G["t_i10_car"] = G.t_rz_tgt.fillna(0), G.t_i10_car.fillna(0)
    # Vacated targets: a game where a current teammate (played the team's latest game) sat out inflates everyone
    # else's share. Scale those games' targets by (1 - absent teammates' season target share).
    G["tgt_adj"], G["rz_adj"], G["absent_sh"] = G.tgt, G.rz_tgt, 0.0
    if P["vacated"] > 0:
        ssn = (G.groupby("gsis_id").tgt.sum() / G.groupby("gsis_id").t_att.sum()).rename("ssn")
        lastwk = G.groupby("team").week.max()
        core = G[G.week == G.team.map(lastwk)][["team", "gsis_id"]].drop_duplicates()
        core["ssn"] = core.gsis_id.map(ssn)
        core = core[core.ssn >= 0.05]
        played = G.groupby(["team", "week"]).gsis_id.apply(set)
        ab = {}
        for (t, w), ids in played.items():
            c = core[core.team == t]
            ab[(t, w)] = min(0.5, c.loc[~c.gsis_id.isin(ids), "ssn"].sum())
        G["absent_sh"] = [ab.get((t, w), 0.0) for t, w in zip(G.team, G.week)]
        f = 1 - P["vacated"] * G.absent_sh
        G["tgt_adj"], G["rz_adj"] = G.tgt * f, G.rz_tgt * f
    def share(num, den, k, prior):
        sw = ((G[num] * G.w).groupby(G.gsis_id).sum() + k * prior) / ((G[den] * G.w).groupby(G.gsis_id).sum() + k)
        g3 = G.sort_values("week").groupby("gsis_id").tail(3)
        r3 = (g3[num].groupby(g3.gsis_id).sum() + 0.5 * k * prior) / (g3[den].groupby(g3.gsis_id).sum() + 0.5 * k)
        return P["recent_w"] * r3 + (1 - P["recent_w"]) * sw, r3, sw
    out = pd.DataFrame(index=last.index)
    out["player"], out["pos"], out["team"] = last.player, pos, last.team
    out["last_week"] = last.week
    out["tsh"], out["tsh_l3"], out["tsh_ssn"] = share("tgt_adj", "t_att", P["k_tgt"], 0.03)
    out["csh"], out["csh_l3"], out["csh_ssn"] = share("car", "t_rush", P["k_car"], 0.02)
    out["rzsh"], _, _ = share("rz_adj", "t_rz_tgt", P["k_rz"], 0.03)
    out["i10sh"], _, _ = share("i10_car", "t_i10_car", P["k_i10"], 0.02)
    out["qsh"], _, _ = share("q_att", "t_att", P["k_qb"], 0.0)
    snw = G[G.offense_pct > 0]
    s_ssn = (snw.offense_pct * snw.w).groupby(snw.gsis_id).sum() / snw.w.groupby(snw.gsis_id).sum()
    s_l3 = snw.sort_values("week").groupby("gsis_id").tail(3).groupby("gsis_id").offense_pct.mean()
    out["snap"] = (P["recent_w"] * s_l3 + (1 - P["recent_w"]) * s_ssn).reindex(out.index)
    sm = lambda c: (G[c] * G.w).groupby(G.gsis_id).sum().reindex(out.index).fillna(0)
    tg, rc, ry, air, car, rsy = sm("tgt"), sm("rec"), sm("recyd"), sm("air"), sm("car"), sm("rushyd")
    pp = lambda key: out.pos.map(lambda p: pri.get(p, pri["WR"])[key])
    out["catch"] = (rc + P["k_catch"] * pp("catch")) / (tg + P["k_catch"])
    out["adot"] = (air + 30 * pp("adot")) / (tg + 30)
    adot_rel = ((out.adot - pp("adot")) / 8.0).clip(-0.8, 1.2)  # aDOT diff vs position prior, per ~8 yds
    prior_ypt = pp("ypt") * (1 + P["adot_w"] * adot_rel)
    if P["qb_w"] > 0:  # receiver efficiency prior follows the current team's passing efficiency (QB/OL), shrunk
        TGw = B["TG"][B["TG"].week < W]
        tm = TGw.groupby("posteam")[["pyds", "att"]].sum()
        lg_ypa = tm.pyds.sum() / tm.att.sum()
        t_ypa = (tm.pyds + 150 * lg_ypa) / (tm.att + 150) / lg_ypa
        prior_ypt = prior_ypt * out.team.map(t_ypa).fillna(1.0).pow(P["qb_w"])
    out["ypt"] = ((ry + P["k_ypt"] * prior_ypt) / (tg + P["k_ypt"])).clip(2.0, 16.0)
    out["ypc"] = (rsy + P["k_ypc"] * pp("ypc")) / (car + P["k_ypc"])
    out["rtd_car"] = pp("rtd_car")  # position-level rush TD per carry (WR/TE gadget carries)
    qa, qy, qc, qi = sm("q_att"), sm("pyds"), sm("q_cmp"), sm("intc")
    out["ypa"] = (qy + P["k_ypa"] * pri_q["ypa"]) / (qa + P["k_ypa"])
    out["cmp"] = (qc + 100 * pri_q["cmp"]) / (qa + 100)
    out["int_r"] = (qi + P["k_int"] * pri_q["int"]) / (qa + P["k_int"])
    tch = sm("car") + sm("rec") + sm("q_db")
    out["fl_r"] = (sm("fl") + P["k_fl"] * pp("fl")) / (tch + P["k_fl"])
    # consistency (league points, games played)
    gp = G.groupby("gsis_id").fpts
    out["games"] = gp.size()
    out["season_ppg"] = gp.mean()
    out["median_ppg"] = gp.median()
    out["ppg_l3"] = G.sort_values("week").groupby("gsis_id").tail(3).groupby("gsis_id").fpts.mean()
    out["cv_pts"] = (gp.std(ddof=0) / gp.mean().where(gp.mean() > 0)).round(3)
    out["best_game"] = gp.max()
    out["ppg_ex_best"] = ((gp.sum() - gp.max()) / (gp.size() - 1).where(gp.size() > 1))
    thr = out.pos.map({"QB": 15, "RB": 10, "WR": 10, "TE": 8, "K": 7}).fillna(10)
    out["games_ge_thr"] = pd.Series(G.fpts.values >= G.gsis_id.map(thr).values, index=G.index).groupby(G.gsis_id).sum()
    out["opp_trend"] = ((out.tsh_l3 + out.csh_l3) / (out.tsh_ssn + out.csh_ssn) - 1).round(3)
    # kickers
    K = G[G.position == "K"]
    out["k_fga"], out["k_fgm"] = (K.fg_att).groupby(K.gsis_id).sum(), (K.fg_made).groupby(K.gsis_id).sum()
    out["k_xpa"], out["k_xpm"] = (K.pat_att).groupby(K.gsis_id).sum(), (K.pat_made).groupby(K.gsis_id).sum()
    # missed team's latest game?
    tl = B["TG"][B["TG"].week < W].groupby("posteam").week.max()
    out["missed_recent"] = (out.team.map(tl) > out.last_week).astype(int)
    return out


def fg_model(B: dict, W: int):
    fg = B["fg"][B["fg"].week < W]
    d = fg.kick_distance.dropna().astype(int)
    made = (fg.field_goal_result == "made").astype(float)
    bins = np.arange(15, 70, 5)
    b = np.digitize(fg.kick_distance, bins)
    rate = made.groupby(b).mean()
    cnt = made.groupby(b).size()
    p_by_bin = {k: (rate[k] * cnt[k] + 0.75 * 5) / (cnt[k] + 5) for k in rate.index}
    pmake = lambda dist: np.vectorize(lambda x: p_by_bin.get(np.digitize([x], bins)[0], 0.5))(dist)
    xp = B["xp"][B["xp"].week < W]
    xp_rate = (xp.extra_point_result == "good").mean()
    return d.values, pmake, xp_rate


def project(D: dict, B: dict, W: int, alpha=None, gm=None, ctx_only=False) -> pd.DataFrame:
    L, OFF, DEF = team_tables(B, W)
    GM = games_for_week(D, W) if gm is None else gm
    C = team_context(GM, L, OFF, DEF, alpha).set_index("team")
    X = player_rates(B, D, W)
    X = X[X.team.isin(C.index)].copy()
    c = C.reindex(X.team)
    v = lambda col: c[col].values
    X["opp"], X["home"], X["implied"], X["total"], X["fav"] = v("opp"), v("home"), v("implied"), v("total"), v("fav")
    X["gameday"] = v("gameday")
    grp = X.pos.where(X.pos.isin(["WR", "TE", "RB"]), "WR")
    tsh_f = np.array([c[f"tsh_{g}"].values[i] for i, g in enumerate(grp)])
    ypt_f = np.array([c[f"ypt_{g}"].values[i] for i, g in enumerate(grp)])
    X["m_tgt"] = v("att") * X.tsh * np.where(X.pos == "QB", 0, tsh_f)
    X["m_rec"] = X.m_tgt * X.catch
    X["m_recyd"] = X.m_tgt * X.ypt * ypt_f
    X["m_rectd"] = v("ptd") * (P["rz_w"] * X.rzsh + (1 - P["rz_w"]) * X.tsh) * np.where(X.pos == "QB", 0, 1)
    X["m_car"] = v("rush") * X.csh
    X["m_rushyd"] = X.m_car * X.ypc.clip(1.0, 9.0) * v("f_ypc")
    X["m_rushtd"] = v("rtd") * (P["i10_w"] * X.i10sh + (1 - P["i10_w"]) * X.csh)
    if P["wr_rush_td"] == "rate":  # WR/TE: gadget carries score at the WR/TE league rate, not by goal-line share
        wt = X.pos.isin(["WR", "TE"])
        X.loc[wt, "m_rushtd"] = X.loc[wt, "m_car"] * X.loc[wt, "rtd_car"]
    isq = (X.pos == "QB").astype(float)
    X["m_att"] = v("att") * X.qsh * isq
    X["m_pyds"] = X.m_att * X.ypa * v("f_ypa")
    X["m_ptd"] = v("ptd") * X.qsh * isq
    X["m_int"] = X.m_att * X.int_r * v("f_int")
    X["m_fl"] = (X.m_car + X.m_rec + X.m_att) * X.fl_r
    # kickers: the team's most recent kicker
    isk = X.pos == "K"
    X["m_fga"] = np.where(isk, v("fga"), 0.0)
    X["m_xpa"] = np.where(isk, v("xpa"), 0.0)
    kl = X[isk].sort_values("last_week").groupby("team").tail(1).index
    X.loc[isk & ~X.index.isin(kl), ["m_fga", "m_xpa"]] = 0.0
    dists, pmake, xp_rate = fg_model(B, W)
    lg_make = np.mean(pmake(dists))
    X["k_skill"] = np.where(isk, ((X.k_fgm.fillna(0) + 15 * lg_make) / (X.k_fga.fillna(0) + 15)) / lg_make, 1.0)
    X["k_xp"] = np.where(isk, (X.k_xpm.fillna(0) + 40 * xp_rate) / (X.k_xpa.fillna(0) + 40), xp_rate)
    X["def_pepa"], X["def_repa"] = v("def_pepa"), v("def_repa")
    X["team_plays"], X["team_pr"] = v("plays"), v("pr")
    X["mean_pts"] = analytic_mean(X, dists, pmake)
    # injury: nflverse report for this week, else missed-latest-game rule
    inj = D["inj"]
    iw = inj[inj.week == W].drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
    X["inj_report"] = X.index.map(iw.report_status) if len(iw) else np.nan
    mult = X.inj_report.map(INJ_MULT).fillna(1.0)
    mult = np.where((X.missed_recent > 0) & X.inj_report.isna(), mult * M.MISSED_GAME_MULT, mult)
    X["p_play"] = mult
    X.attrs.update(L=L, OFF=OFF, DEF=DEF, C=C, dists=dists, pmake=pmake)
    return X


def analytic_mean(X, dists, pmake) -> np.ndarray:
    s = SCORING
    pts = (X.m_rec * s["rec"] + X.m_recyd * s["rec_yd"] + X.m_rectd * s["rec_td"] + X.m_rushyd * s["rush_yd"]
           + X.m_rushtd * s["rush_td"] + X.m_pyds * s["pass_yd"] + X.m_ptd * s["pass_td"] + X.m_int * s["int"]
           + X.m_fl * s["fum_lost"])
    pm = pmake(dists)
    ev_fg = np.mean(pm * dists * s["fg_yd"] + (1 - pm) * (dists < 30) * s["fg_miss_0_29"])
    pts = pts + X.m_fga * ev_fg * X.k_skill + X.m_xpa * (X.k_xp * s["pat_made"] + (1 - X.k_xp) * s["pat_miss"])
    return pts.values


# ============================================================================ Monte Carlo
def _nb(rng, mu, size, S):
    mu = np.maximum(mu, 1e-9)
    p = size / (size + mu)
    return rng.negative_binomial(size, p, size=(S, len(p)) if np.ndim(p) else S) if False else rng.negative_binomial(size, p)


def simulate(X: pd.DataFrame, n=None, seed=None, sim=None) -> pd.DataFrame:
    sp = dict(SIM, **(sim or {}))
    S = n or sp["n"]
    rng = np.random.default_rng(seed if seed is not None else sp["seed"])
    N = len(X)
    sh = lambda a: np.broadcast_to(np.asarray(a, float), (S, N))
    z = rng.gamma(1 / sp["cv_plays"] ** 2, sp["cv_plays"] ** 2, size=(S, N))
    sc = rng.gamma(1 / sp["cv_score"] ** 2, sp["cv_score"] ** 2, size=(S, N))
    def nb(mu, size):
        mu = np.maximum(mu, 1e-9)
        return rng.negative_binomial(size, size / (size + mu))
    s = SCORING
    mt, mc, ma = sh(X.m_tgt), sh(X.m_car), sh(X.m_att)
    tgt = nb(mt * z, sp["size_tgt"])
    rec = rng.binomial(tgt, sh(X.catch))
    ypr = sh((X.ypt / X.catch).values) * sh(np.where(X.m_tgt > 0, X.m_recyd / np.maximum(X.m_tgt * X.ypt, 1e-9), 1))
    k = 1 / sp["cv_rec"] ** 2
    recyd = np.where(rec > 0, rng.gamma(np.maximum(rec, 1) * k, ypr / k), 0.0)
    car = nb(mc * z, sp["size_car"])
    ypc_eff = sh(np.clip(np.where(X.m_car > 0, X.m_rushyd / np.maximum(X.m_car, 1e-9), 0), 1.0, 9.0))
    cs = sp["sd_carry"] / (ypc_eff + 3)
    kc = 1 / np.maximum(cs, 0.2) ** 2
    rushyd = np.where(car > 0, rng.gamma(np.maximum(car, 1) * kc, (ypc_eff + 3) / kc) - 3 * car, 0.0)
    att = np.where(ma > 0.5, nb(ma * z, sp["size_att"]), 0)
    cmp = rng.binomial(att, sh(X.cmp.clip(0.3, 0.8)))
    ypcomp = sh(np.where(X.m_att > 0, X.m_pyds / np.maximum(X.m_att * X.cmp, 1e-9), 0))
    kp = 1 / sp["cv_comp"] ** 2
    pyds = np.where(cmp > 0, rng.gamma(np.maximum(cmp, 1) * kp, np.maximum(ypcomp, 1e-6) / kp), 0.0)
    rel = lambda sim_v, mu: np.where(mu > 1e-6, sim_v / np.maximum(mu, 1e-6), 1.0)
    rectd = rng.poisson(sh(X.m_rectd) * sc * rel(tgt, mt))
    rushtd = rng.poisson(sh(X.m_rushtd) * sc * rel(car, mc))
    ptd = rng.poisson(sh(X.m_ptd) * sc * rel(att, ma))
    ints = rng.poisson(np.maximum(att, 0) * sh(X.m_int / np.maximum(X.m_att, 1e-9)))
    fl = rng.poisson((tgt * sh(X.catch) + car + att) * sh(X.fl_r))
    pts = (rec * s["rec"] + recyd * s["rec_yd"] + rectd * s["rec_td"] + rushyd * s["rush_yd"] + rushtd * s["rush_td"]
           + pyds * s["pass_yd"] + ptd * s["pass_td"] + ints * s["int"] + fl * s["fum_lost"]
           + (pyds >= s["bonus_pass"][0]) * s["bonus_pass"][1] + (rushyd >= s["bonus_rush"][0]) * s["bonus_rush"][1]
           + (recyd >= s["bonus_rec"][0]) * s["bonus_rec"][1])
    # kickers
    isk = (X.pos == "K").values
    if isk.any():
        dists, pmake = X.attrs["dists"], X.attrs["pmake"]
        g = rng.gamma(1 / sp["cv_fga"] ** 2, sp["cv_fga"] ** 2, size=(S, N))
        nfg = rng.poisson(sh(X.m_fga) * g)
        maxk = 7
        dd = rng.choice(dists, size=(S, N, maxk))
        pm = np.clip(pmake(dd) * sh(X.k_skill)[..., None], 0, 0.995)
        made = rng.random((S, N, maxk)) < pm
        use = np.arange(maxk)[None, None, :] < nfg[..., None]
        kpts = (use * made * dd * s["fg_yd"]).sum(-1) + (use * ~made * (dd < 30) * s["fg_miss_0_29"]).sum(-1)
        nxp = rng.poisson(sh(X.m_xpa) * sc)
        xpm = rng.binomial(nxp, sh(X.k_xp))
        kpts = kpts + xpm * s["pat_made"] + (nxp - xpm) * s["pat_miss"]
        pts = np.where(isk[None, :], kpts, pts)
    play = rng.random((S, N)) < sh(X.p_play)
    pts = np.where(play, pts, 0.0)
    q = np.quantile(pts, [0.1, 0.5, 0.9], axis=0)
    thr = X.pos.map(BOOM_T).fillna(20).values
    out = pd.DataFrame({"sim_mean": pts.mean(0), "sim_median": q[1], "floor_p10": q[0], "p90": q[2],
                        "p_ge15": (pts >= 15).mean(0), "p_ge20": (pts >= 20).mean(0), "p_ge25": (pts >= 25).mean(0),
                        "p_boom": (pts >= thr[None, :]).mean(0), "boom_thr": thr}, index=X.index)
    out.attrs["draws"] = pts
    return out


def matchup_grade(ratio: pd.Series) -> pd.Series:
    bins = [-np.inf, 0.90, 0.95, 0.985, 1.015, 1.05, 1.10, np.inf]
    return pd.cut(ratio, bins, labels=["F", "D", "C-", "C", "B", "A", "A+"]).astype(str)


def full_week(D, B, W, sims=None, sim=None) -> pd.DataFrame:
    X = project(D, B, W)
    X0 = project(D, B, W, alpha=0.0)  # neutral matchup (same Vegas script)
    X["neutral_pts"] = X0.mean_pts.reindex(X.index)
    X["matchup_ratio"] = (X.mean_pts / X.neutral_pts.where(X.neutral_pts > 0.5)).round(3)
    X["matchup_grade"] = matchup_grade(X.matchup_ratio)
    Sm = simulate(X, n=sims, sim=sim)
    X = X.join(Sm)
    X["proj_pts"] = X.sim_mean
    return X


# ============================================================================ backtest
def pool_mask(X):
    return (((X.pos.isin(["RB", "WR", "TE"])) & (X.snap >= 0.40))
            | ((X.pos == "QB") & (X.qsh >= 0.6)) | ((X.pos == "K") & (X.m_fga > 0)))


def backtest(D, B, weeks, sims=2000, sim=None, verbose=True):
    rows = []
    for W in weeks:
        X = project(D, B, W)
        X = X[pool_mask(X)]
        Sm = simulate(X, n=sims, sim=sim)
        X = X.join(Sm)
        act = B["G"][B["G"].week == W].groupby("gsis_id").fpts.sum()
        X["actual"] = X.index.map(act).fillna(0.0)
        X["base"] = X.season_ppg
        X["base_inj"] = X.season_ppg * X.p_play
        X["model"] = X.sim_mean
        X["week"] = W
        rows.append(X)
    R = pd.concat(rows)
    if verbose:
        report(R)
    return R


TOPN = {"QB": 12, "RB": 24, "WR": 36, "TE": 12, "K": 12}


def report(R, out=sys.stdout):
    from scipy.stats import spearmanr  # noqa
    res = []
    for (W, pos), g in R.groupby(["week", "pos"]):
        n = TOPN[pos]
        top_act = set(g.nlargest(n, "actual").index)
        for m in ["base", "base_inj", "model"]:
            top = g.nlargest(n, m)
            res.append(dict(week=W, pos=pos, model=m, n=len(g), spearman=g[m].corr(g.actual, method="spearman"),
                            hit=len(set(top.index) & top_act) / n, top_avg=top.actual.mean(),
                            mae=(g[m] - g.actual).abs().mean(), bias=(g[m] - g.actual).mean()))
    T = pd.DataFrame(res)
    S = T.groupby(["pos", "model"])[["spearman", "hit", "top_avg", "mae", "bias"]].mean().round(3)
    A = T.groupby("model")[["spearman", "hit", "top_avg", "mae"]].mean().round(3)
    print("Offense backtest (mean over weeks, by position):\n", S.to_string(), "\n\nAll positions:\n", A.to_string(), file=out)
    # calibration
    lines = [f"\nCalibration (n={len(R)}): below P10 {(R.actual < R.floor_p10).mean():.3f}, above P90 {(R.actual > R.p90).mean():.3f}"]
    for c, t in [("p_ge15", 15), ("p_ge20", 20), ("p_boom", None)]:
        obs = (R.actual >= (R.boom_thr if t is None else t)).mean()
        lines.append(f"  {c}: predicted {R[c].mean():.3f} observed {obs:.3f}")
    R["_o20"] = (R.actual >= 20).astype(int)
    R["_b"] = pd.cut(R.p_ge20, [-0.01, 0.03, 0.08, 0.15, 0.25, 0.4, 1])
    rel = R.groupby("_b", observed=True).agg(n=("_o20", "size"), pred=("p_ge20", "mean"), obs=("_o20", "mean")).round(3)
    lines.append("  P(>=20) reliability:\n" + rel.to_string())
    print("\n".join(lines), file=out)
    return T


# ============================================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int)
    ap.add_argument("--season", type=int)
    ap.add_argument("--backtest")
    a = ap.parse_args()
    season = a.season or M.nfl.get_current_season()
    D = M.load_data(season)
    B = build(D)
    if a.backtest:
        lo, hi = map(int, a.backtest.split("-"))
        R = backtest(D, B, list(range(lo, hi + 1)))
        R.to_csv(f"backtest_offense_weeks{lo}-{hi}.csv")
        with open(f"backtest_offense_weeks{lo}-{hi}.txt", "w") as f:
            report(R, f)
        return
    W = a.week or M.detect_week(D["sched"])
    X = full_week(D, B, W)
    X = X[(X.proj_pts > 0.3) | (X.pos == "K")]
    X = X[~((X.pos == "K") & (X.m_fga == 0))]
    X["rank_pos"] = X.groupby("pos").proj_pts.rank(ascending=False, method="first").astype(int)
    X["matchup"] = np.where(X.home == 1, "vs ", "@ ") + X.opp
    cols = ["rank_pos", "pos", "player", "team", "matchup", "gameday", "implied", "proj_pts", "sim_median", "floor_p10",
            "p90", "p_ge15", "p_ge20", "p_ge25", "p_boom", "boom_thr", "matchup_grade", "matchup_ratio", "p_play",
            "inj_report", "snap", "tsh", "csh", "rzsh", "i10sh", "qsh", "adot", "m_tgt", "m_rec", "m_recyd", "m_rectd",
            "m_car", "m_rushyd", "m_rushtd", "m_att", "m_pyds", "m_ptd", "m_int", "m_fga", "m_xpa", "season_ppg",
            "median_ppg", "ppg_l3", "games", "games_ge_thr", "cv_pts", "best_game", "ppg_ex_best", "opp_trend",
            "def_pepa", "def_repa", "team_plays", "team_pr"]
    X = X.sort_values(["pos", "proj_pts"], ascending=[True, False])
    X[cols].round(3).rename_axis("gsis_id").to_csv(f"offense_week{W}.csv")
    print(f"week {W}: wrote offense_week{W}.csv ({len(X)} players)")
    for p in ["QB", "RB", "WR", "TE", "K"]:
        print(X[X.pos == p].head(12)[["player", "team", "matchup", "proj_pts", "floor_p10", "p90", "p_boom", "matchup_grade"]].round(2).to_string())


if __name__ == "__main__":
    main()
