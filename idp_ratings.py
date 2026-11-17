#!/usr/bin/env python3
"""
Weekly IDP streaming ratings v2 (DL / LB / DB) built on nflverse data.

    python idp_ratings.py                # auto-detect season + upcoming week, write ratings_week<N>.csv
    python idp_ratings.py --week 9
    python idp_ratings.py --backtest 4-7 # walk-forward backtest vs v1 model and season-ppg baseline

v2 = component model (tackles / TFL / sacks / INT / PD / FF / other), each a recency-weighted,
shrunk per-snap rate x projected snaps x a role-specific opponent factor. Pass rushers are driven
by an opponent-adjusted offensive-line rating (+ OL injuries) and expected dropbacks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os

import numpy as np
import pandas as pd
import nflreadpy as nfl

# ============================================================================
# CONFIG: league scoring (Jason's Yahoo league). Edit freely.
# ============================================================================
SCORING = {
    "solo_tackle": 0.75, "assisted_tackle": 0.25, "tackle_for_loss": 1.5, "sack": 3.0,
    "interception": 5.0, "forced_fumble": 5.0, "fumble_recovery": 2.0, "defensive_td": 6.0,
    "safety": 3.0, "pass_defended": 1.0, "blocked_kick": 2.0,
}

# ============================================================================
# MODEL PARAMETERS (see README; tuned lightly by --backtest)
# ============================================================================
P = dict(
    decay=0.50,              # per-week recency weight (1, .5, .25, .125): last 3-4 games dominate (Nov 3 audit; was .80)
    snap_recent_games=3, snap_recent_w=0.80,  # blend last-3 snap% with season (backtest liked less recency)
    # shrinkage pseudo-snaps toward role prior, per component (rarer = more shrinkage)
    k_tackle=120, k_tfl=300, k_sack=300, k_int=900, k_pd=400, k_ff=900, k_other=1500,
    xsack_w_real=0.40,       # expected sacks = 40% realized sacks + 60% QB hits x league sack/hit ratio
    opp_alpha=0.80,          # use 80% of raw opponent deviation (backtest: 0 -> .246, .6 -> .257, .8 -> .260 Spearman)
    clip=(0.70, 1.35),
    ol_k_db=150, ol_k_run=100,  # pseudo-dropbacks / pseudo-runs shrinking OL ratings to average
    ol_miss_per=0.05,        # +5% pass-rush/run-stuff opportunity per missing OL starter (cap 3)
    script_db_per_pt=0.012,  # opponent dropbacks +1.2% per point the defense's team is favored
    script_run_per_pt=-0.010,
    total_per_pt=0.004,      # plays +0.4% per point of Vegas total above 45
    form_w=0.0,
    lb_run_w=0.45,
    # robustness to one-big-game outliers (v2.1): per-game point caps on rare big-play events before they enter
    # the per-snap rates, a downweight on each player's single best game for big-play components, and extra
    # shrinkage for the rarest events. Tackle/snap opportunity is never capped.
    robust=True,
    cap_game=dict(sack=6.0, int=5.0, ff=5.0, other=2.0),   # points per game: 2 sacks, 1 INT, 1 FF, a TD counts like a FR
    best_game_w=0.5,         # weight multiplier on the best-fpts game for the components in best_game_comps
    best_game_comps=("int", "ff", "other"),
    splash_k_mult=2.0,       # extra shrinkage multiplier on k for the rarest events (backtest wks 4-7, see README)
    splash_k_comps=("int", "ff", "other"),           # off-ball LB tackle factor: run volume share vs LB tackle points allowed              # optional blend with matchup-adjusted weighted ppg (0 = pure component model)
)
LEAGUE_AVG_TOTAL = 45.0
# Linear calibration actual ~ a + b*raw, fit on wks 4-8 backtest (Nov 3). Raw slope <1: projections spread too wide,
# so top-ranked LBs were over-projected (+0.6 pts in the 6-7 tier). Shrinks toward the position mean.
CAL = {"DB": (1.197, 0.683), "DL": (0.786, 0.745), "LB": (1.322, 0.762)}
# Nov 3 big-play audit (comp_audit.py / comp_exp*.py): separate (intercept, slope) for tackle pts and big-play pts
# (TFL, sack, INT, PD, FF, FR/TD) by role group, fit on wks 4-8 walk-forward projections. DL/EDGE big plays are left
# unshrunk (slope .99 raw); DB/LB big plays are mostly noise week to week (slope .4-.5), so they are shrunk.
CAL_MODE = "split"
CAL_SPLIT = {"DB": {"tk": (0.783, 0.633), "big": (0.750, 0.500)},
             "DL": {"tk": (0.743, 0.424), "big": (0.000, 1.000)},
             "LB": {"tk": (0.098, 0.967), "big": (1.218, 0.405)}}
LOW_SNAP_FLAG = 0.50
MIN_SNAP_SHARE_RATED = 0.15
MISSED_GAME_MULT = 0.6
POS_GROUPS = ["DL", "LB", "DB"]
EDGE_DEPTH = {"LDE", "RDE", "DE", "LOLB", "ROLB", "EDGE"}
OL_POS = {"T", "G", "C", "OL", "OT", "OG"}
BOOM_COLS = ["sim_mean", "sim_median", "floor_p10", "p90", "p_ge10", "p_ge12", "p_sack", "p_takeaway"]
LAST: dict = {}  # side outputs of the latest project() call (offense profile, OL personnel)
COMPS = ["tackle", "tfl", "sack", "int", "pd", "ff", "other"]


# ============================================================================
def load_data(season: int) -> dict:
    D = {
        "sched": nfl.load_schedules([season]).to_pandas(),
        "ps": nfl.load_player_stats([season], summary_level="week").to_pandas(),
        "snaps": nfl.load_snap_counts([season]).to_pandas(),
        "pbp": nfl.load_pbp([season]).to_pandas(),
        "rosters": nfl.load_rosters_weekly([season]).to_pandas(),
    }
    try:
        D["inj"] = nfl.load_injuries([season]).to_pandas()
    except Exception:
        D["inj"] = pd.DataFrame(columns=["week", "gsis_id", "report_status", "practice_status",
                                         "practice_primary_injury", "report_primary_injury", "team", "position"])
    try:
        D["depth"] = nfl.load_depth_charts([season]).to_pandas()
    except Exception:
        D["depth"] = pd.DataFrame(columns=["dt", "team", "gsis_id", "pos_abb", "pos_rank"])
    D["ps"] = D["ps"][D["ps"].season_type == "REG"]
    D["snaps"] = D["snaps"][D["snaps"].game_type == "REG"]
    D["pbp"] = D["pbp"][D["pbp"].season_type == "REG"]
    idmap = D["rosters"][["gsis_id", "pfr_id"]].dropna().drop_duplicates("pfr_id")
    D["snaps"] = D["snaps"].merge(idmap, left_on="pfr_player_id", right_on="pfr_id", how="left")
    # Rosters carry no pfr_id for OL (and some others): fall back to normalized name + team.
    r = D["rosters"].dropna(subset=["gsis_id"]).copy()
    r["k"] = r.full_name.map(norm_name) + "|" + r.team
    nmap = r.drop_duplicates("k", keep="last").set_index("k").gsis_id
    miss = D["snaps"].gsis_id.isna()
    keys = D["snaps"].loc[miss, "player"].map(norm_name) + "|" + D["snaps"].loc[miss, "team"]
    D["snaps"].loc[miss, "gsis_id"] = keys.map(nmap).values
    return D


def norm_name(x) -> str:
    """Lowercase, strip punctuation and suffixes (Jr, Sr, II, III, IV, V) for name joins."""
    import re
    s = re.sub(r"[^a-z ]", "", str(x).lower().replace("-", " "))
    return " ".join(w for w in s.split() if w not in {"jr", "sr", "ii", "iii", "iv", "v"})


def detect_week(sched: pd.DataFrame) -> int:
    pend = sched[(sched.game_type == "REG") & sched.result.isna()]
    if pend.empty:
        raise SystemExit("No unplayed regular-season games left.")
    return int(pend.week.min())


def score(df: pd.DataFrame) -> pd.DataFrame:
    s, df = SCORING, df.copy()
    f = lambda c: df[c].fillna(0) if c in df else 0
    df["solo"] = f("def_tackles_solo")
    df["ast"] = f("def_tackles_with_assist") + f("def_tackle_assists")  # both halves of a shared tackle
    df["tfl"], df["sacks"], df["qb_hits"] = f("def_tackles_for_loss"), f("def_sacks"), f("def_qb_hits")
    df["ints"], df["pd"], df["ff"] = f("def_interceptions"), f("def_pass_defended"), f("def_fumbles_forced")
    df["fr"], df["tds"], df["safeties"] = f("fumble_recovery_opp"), f("def_tds"), f("def_safeties")
    df["blocks"] = f("def_punt_blocks") + f("def_fg_blocks") + f("def_pat_blocks")
    df["p_tackle"] = df.solo * s["solo_tackle"] + df.ast * s["assisted_tackle"]
    df["p_tfl"] = df.tfl * s["tackle_for_loss"]
    df["p_sack"] = df.sacks * s["sack"]
    df["p_int"] = df.ints * s["interception"]
    df["p_pd"] = df.pd * s["pass_defended"]
    df["p_ff"] = df.ff * s["forced_fumble"]
    df["p_other"] = (df.fr * s["fumble_recovery"] + df.tds * s["defensive_td"] + df.safeties * s["safety"]
                     + df.blocks * s["blocked_kick"])
    df["fpts"] = df[[f"p_{c}" for c in COMPS]].sum(axis=1)
    return df


def wmean(x, w):
    w = np.asarray(w, float)
    return float(np.sum(np.asarray(x, float) * w) / w.sum()) if w.sum() > 0 else np.nan


# ============================================================================
# Opponent offense / offensive-line profile
# ============================================================================
def offense_profile(D: dict, week: int, hist: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    hm = week - 1
    pbp = D["pbp"][D["pbp"].week <= hm]
    pl = pbp[pbp.play_type.isin(["pass", "run"]) & (pbp.two_point_attempt != 1)].copy()
    pl["db"] = pl.qb_dropback.fillna(0)
    pl["designed_run"] = ((pl.play_type == "run") & (pl.qb_scramble != 1) & (pl.qb_kneel != 1)).astype(int)
    pl["stuff"] = ((pl.designed_run == 1) & (pl.yards_gained <= 0)).astype(int)
    pl["att"] = pl.pass_attempt.fillna(0) * (pl.sack != 1)
    g = pl.groupby(["posteam", "defteam", "game_id", "week"]).agg(
        plays=("play_id", "size"), db=("db", "sum"), att=("att", "sum"), runs=("designed_run", "sum"),
        sacks=("sack", "sum"), hits=("qb_hit", "sum"), stuffs=("stuff", "sum"),
        ints=("interception", "sum"), fum=("fumble", "sum"), air=("air_yards", "sum"),
    ).reset_index()
    g["w"] = P["decay"] ** (hm - g.week)

    # opponent-adjusted rates: rate ~ mu + O[off] + D[def], weighted alternating least squares, ridge-shrunk
    def adjust(num, den, k):
        mu = g[num].sum() / g[den].sum()
        r = g[num] / g[den].replace(0, np.nan)
        O = pd.Series(0.0, index=sorted(g.posteam.unique()))
        Dd = pd.Series(0.0, index=sorted(g.defteam.unique()))
        ww = g.w * g[den]
        for _ in range(25):
            res = (r - mu - g.defteam.map(Dd)).fillna(0) * ww
            O = res.groupby(g.posteam).sum() / (ww.groupby(g.posteam).sum() + k)
            res = (r - mu - g.posteam.map(O)).fillna(0) * ww
            Dd = res.groupby(g.defteam).sum() / (ww.groupby(g.defteam).sum() + k)
        raw = (g[num] * g.w).groupby(g.posteam).sum() / (g[den] * g.w).groupby(g.posteam).sum()
        return mu, O, Dd, raw

    mu_s, O_s, Def_s, raw_s = adjust("sacks", "db", P["ol_k_db"])
    mu_h, O_h, Def_h, raw_h = adjust("hits", "db", P["ol_k_db"])
    mu_st, O_st, Def_st, raw_st = adjust("stuffs", "runs", P["ol_k_run"])

    wg = lambda c: (g[c] * g.w).groupby(g.posteam).sum() / g.w.groupby(g.posteam).sum()
    off = pd.DataFrame({
        "plays_pg": wg("plays"), "db_pg": wg("db"), "att_pg": wg("att"), "runs_pg": wg("runs"),
        "sack_rate_raw": raw_s, "hit_rate_raw": raw_h, "stuff_rate_raw": raw_st,
        "sack_rate_adj": mu_s + O_s, "hit_rate_adj": mu_h + O_h, "stuff_rate_adj": mu_st + O_st,
        "fum_per_play": (g.fum * g.w).groupby(g.posteam).sum() / (g.plays * g.w).groupby(g.posteam).sum(),
        "int_rate": (g.ints * g.w).groupby(g.posteam).sum() / (g.att * g.w).groupby(g.posteam).sum(),
        "adot": (g.air * g.w).groupby(g.posteam).sum() / (g.att * g.w).groupby(g.posteam).sum(),
    })
    # pass-block / run-block indices relative to league (>1 = line is easier to beat)
    off["pr_idx"] = 0.5 * off.sack_rate_adj / mu_s + 0.5 * off.hit_rate_adj / mu_h
    off["run_idx"] = off.stuff_rate_adj / mu_st
    # WR/TE targets per game
    ps = D["ps"][D["ps"].week <= hm]
    tg = ps[ps.position_group.isin(["WR", "TE"])].groupby(["team", "week"]).targets.sum().reset_index()
    tg["w"] = P["decay"] ** (hm - tg.week)
    off["wrte_tgt_pg"] = (tg.targets * tg.w).groupby(tg.team).sum() / tg.w.groupby(tg.team).sum()
    # QB-level INT rate (shrunk 200 attempts toward league), for the expected starter
    qb = ps[ps.position == "QB"].groupby("player_id").agg(att=("attempts", "sum"), ints=("passing_interceptions", "sum"))
    lg_int = qb.ints.sum() / max(qb.att.sum(), 1)
    qb["int_rate_shr"] = (qb.ints + 200 * lg_int) / (qb.att + 200)
    # fantasy points allowed by role (tackle comp) per game
    fpa = hist.groupby(["opponent_team", "role", "week"]).p_tackle.sum().reset_index()
    fpa = fpa.groupby(["opponent_team", "role"]).p_tackle.mean()
    fpa_idx = fpa / fpa.groupby(level=1).transform("mean")
    lg = off.mean(numeric_only=True)
    meta = dict(mu_sack=mu_s, mu_hit=mu_h, mu_stuff=mu_st, lg=lg, qb=qb, lg_int=lg_int, fpa_idx=fpa_idx,
                def_adj_sack=Def_s)
    return off, meta


def ol_personnel(D: dict, week: int) -> pd.DataFrame:
    """Per team: OL starters (top-5 offense snaps over last 4 team games) unavailable / losing snaps."""
    hm = week - 1
    sn = D["snaps"][(D["snaps"].week <= hm) & D["snaps"].position.isin(OL_POS)]
    ros = D["rosters"][D["rosters"].week == week].drop_duplicates("gsis_id").set_index("gsis_id")
    inj = D["inj"][D["inj"].week == week].drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
    rows = []
    for team, t in sn.groupby("team"):
        wks = sorted(t.week.unique())[-4:]
        last = wks[-1] if wks else None
        rec = t[t.week.isin(wks)]
        top = rec.groupby(["gsis_id", "player"]).offense_snaps.sum().sort_values(ascending=False).head(5)
        miss, names = 0.0, []
        for (gid, name), _ in top.items():
            lastpct = t[(t.week == last) & (t.gsis_id == gid)].offense_pct.max()
            lastpct = 0.0 if pd.isna(lastpct) else lastpct
            rs = ros.status.get(gid) if gid in ros.index else None
            rep = inj.report_status.get(gid) if gid in inj.index else None
            prac = inj.practice_status.get(gid) if gid in inj.index else None
            m = 0.0
            if rs == "CUT":  # released: replacement likely settled in, half weight
                m, why = 0.5, rs
            elif rs is not None and rs != "ACT":
                m, why = 1.0, rs
            elif rep in ("Out", "Doubtful"):
                m, why = 1.0, rep
            elif rep == "Questionable":
                m, why = 0.4, "Q"
            elif rep is None and lastpct < 0.3:
                m, why = 0.8, f"DNP W{last}"
            elif rep is None and lastpct < 0.7:
                m, why = 0.4, f"{lastpct:.0%} snaps W{last}"
            elif isinstance(prac, str) and prac.startswith("Did Not") and rep is None:
                m, why = 0.4, "DNP practice"
            if m > 0:
                miss += m
                names.append(f"{name} ({why})")
        rows.append({"team": team, "ol_missing": min(miss, 3.0), "ol_missing_names": "; ".join(names)})
    return pd.DataFrame(rows).set_index("team")


# ============================================================================
def player_table(D: dict, week: int):
    hm = week - 1
    ps = score(D["ps"][D["ps"].week <= hm])
    dfn = ps[ps.position_group.isin(POS_GROUPS)]
    sn = D["snaps"][D["snaps"].week <= hm]
    team_def = sn.groupby(["team", "week"]).defense_snaps.max().rename("team_def_snaps").reset_index()
    team_off = sn.groupby(["team", "week"]).offense_snaps.max().rename("team_off_snaps").reset_index()
    psn = sn[sn.defense_snaps > 0][["gsis_id", "week", "team", "defense_snaps", "defense_pct"]].dropna(subset=["gsis_id"])
    log = psn.merge(dfn, left_on=["gsis_id", "week"], right_on=["player_id", "week"], how="outer", suffixes=("_snap", ""))
    log["gsis_id"] = log.gsis_id.fillna(log.player_id)
    log["team"] = log.team.fillna(log.team_snap)
    num = ["solo", "ast", "tfl", "sacks", "qb_hits", "ints", "pd", "ff", "fr", "tds", "safeties", "blocks", "fpts"] + [f"p_{c}" for c in COMPS]
    log[num] = log[num].fillna(0.0)
    ros_all = D["rosters"][D["rosters"].week <= week].sort_values("week")
    rpos = ros_all.drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
    pos_map = {"DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "OLB": "LB", "ILB": "LB", "MLB": "LB", "LB": "LB",
               "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB", "SAF": "DB"}
    log["position_group"] = log.position_group.fillna(log.gsis_id.map(rpos.position).map(pos_map))
    log = log[log.position_group.isin(POS_GROUPS)].copy()
    log["player_display_name"] = log.player_display_name.fillna(log.gsis_id.map(rpos.full_name))
    if log.opponent_team.isna().any():
        sc = D["sched"]
        opp = pd.concat([sc[["week", "home_team", "away_team"]].rename(columns={"home_team": "team", "away_team": "o"}),
                         sc[["week", "away_team", "home_team"]].rename(columns={"away_team": "team", "home_team": "o"})])
        log = log.merge(opp, on=["team", "week"], how="left")
        log["opponent_team"] = log.opponent_team.fillna(log.o)
        log = log.drop(columns="o")
    log["w"] = P["decay"] ** (hm - log.week)

    # league sack-per-QB-hit ratio (defender level)
    sack_per_hit = dfn.def_sacks.sum() / max(dfn.def_qb_hits.sum(), 1)

    # depth chart snapshot available before the week's first game (no look-ahead in backtests)
    first_game = pd.to_datetime(D["sched"][D["sched"].week == week].gameday).min()
    dc = D["depth"].copy()
    if len(dc):
        dc["dtp"] = pd.to_datetime(dc.dt, utc=True).dt.tz_localize(None)
        dc = dc[dc.dtp < first_game]
        dc = dc[dc.dtp == dc.dtp.max()] if len(dc) else dc
    dc_pos = dc.sort_values("pos_rank").drop_duplicates("gsis_id").set_index("gsis_id").pos_abb if len(dc) else pd.Series(dtype=str)

    rows = []
    for pid, g in log.groupby("gsis_id"):
        g = g.sort_values("week", ascending=False)
        gs = g[g.defense_snaps.notna()]
        r = {"gsis_id": pid, "player": g.player_display_name.iloc[0], "pos": g.position_group.iloc[0],
             "position": g.position.dropna().iloc[0] if g.position.notna().any() else rpos.position.get(pid),
             "depth_pos": rpos.depth_chart_position.get(pid) if pid in rpos.index else None,
             "dc_pos": dc_pos.get(pid), "stat_team": g.team.iloc[0], "games": len(g),
             "last_game_week": int(g.week.iloc[0]), "season_ppg": g.fpts.mean(),
             "recent_ppg": wmean(g.head(4).fpts, [0.4, 0.3, 0.2, 0.1][:len(g.head(4))]),
             "season_snap_pct": gs.defense_pct.mean() if len(gs) else np.nan,
             "recent_snap_pct": gs.head(P["snap_recent_games"]).defense_pct.mean() if len(gs) else np.nan,
             "snaps_total": gs.defense_snaps.sum(), "w_snaps": (gs.defense_snaps * gs.w).sum()}
        for c in ["solo", "ast", "tfl", "sacks", "qb_hits", "ints", "pd", "ff", "fr", "tds"]:
            r[c] = g[c].sum()
        # consistency (games he took defensive snaps)
        fp = gs.fpts.to_numpy()
        r["median_ppg"] = float(np.median(fp)) if len(fp) else np.nan
        r["games_ge6_rate"] = float((fp >= 6).mean()) if len(fp) else np.nan
        r["games_ge6"] = f"{int((fp >= 6).sum())}/{len(fp)}"
        r["cv_pts"] = float(fp.std(ddof=0) / fp.mean()) if len(fp) and fp.mean() > 0 else np.nan
        r["best_game_pts"] = float(fp.max()) if len(fp) else np.nan
        r["ppg_ex_best"] = float((fp.sum() - fp.max()) / (len(fp) - 1)) if len(fp) > 1 else np.nan
        r["best_game_share"] = float(fp.max() / fp.sum()) if len(fp) and fp.sum() > 0 else np.nan
        gw = gs.w.copy()
        gsx = gs.copy()
        if P["robust"]:
            for c, cap in P["cap_game"].items():
                gsx[f"p_{c}"] = gsx[f"p_{c}"].clip(upper=cap)
            gsx["sacks"] = gsx.sacks.clip(upper=P["cap_game"]["sack"] / SCORING["sack"])
        ws = gw.copy()
        if P["robust"] and len(gs) >= 3:
            ws.loc[gs.fpts.idxmax()] *= P["best_game_w"]
        for c in COMPS:
            wc = ws if c in P["best_game_comps"] else gw
            r[f"w_{c}"] = (gsx[f"p_{c}"] * wc).sum()
            r[f"wraw_{c}"] = (gs[f"p_{c}"] * gw).sum()
        # expected-sack points from QB hits (stable) + realized sacks (noisy)
        wsk = ws if "sack" in P["best_game_comps"] else gw
        r["w_sack"] = SCORING["sack"] * (P["xsack_w_real"] * (gsx.sacks * wsk).sum()
                                          + (1 - P["xsack_w_real"]) * (gs.qb_hits * wsk).sum() * sack_per_hit)
        # splash components were accumulated with ws; keep their exposure consistent
        r["w_snaps_splash"] = (gs.defense_snaps * ws).sum()
        r["wraw_sack"] = SCORING["sack"] * (P["xsack_w_real"] * (gs.sacks * gw).sum()
                                             + (1 - P["xsack_w_real"]) * (gs.qb_hits * gw).sum() * sack_per_hit)
        rows.append(r)
    T = pd.DataFrame(rows)
    T["tackles_per_snap"] = (T.solo + T.ast) / T.snaps_total.replace(0, np.nan)
    T["hits_per_snap"] = T.qb_hits / T.snaps_total.replace(0, np.nan)

    # roles: EDGE / IDL / LB / CB / S
    def role(r):
        dp, dcp = r.depth_pos or "", r.dc_pos or ""
        if r.pos == "DL":
            if dcp in {"LDT", "RDT", "NT", "DT"} or (not dcp and dp in {"DT", "NT"}):
                return "IDL"
            return "EDGE"
        if r.pos == "LB":
            if dcp in EDGE_DEPTH:
                return "EDGE"
            # pass-rush profile: QB hits with few tackles. Off-ball LBs run ~0.12-0.17 tackles/snap, edges ~0.05-0.08.
            # (ESPN often lists 3-4 edges as WLB/SLB, e.g. Watt, Van Ginkel, so the depth label alone is not enough.)
            if r.snaps_total >= 100 and ((r.hits_per_snap >= 0.030 and r.tackles_per_snap < 0.11)
                                         or (r.hits_per_snap >= 0.015 and r.tackles_per_snap < 0.09)):
                return "EDGE"
            return "LB"
        return "S" if (dp in {"FS", "SS", "S"} or dcp in {"FS", "SS"} or r.position in ("S", "FS", "SS", "SAF")) else "CB"
    T["role"] = T.apply(role, axis=1)

    # recency-weighted per-snap rates shrunk toward role prior
    reg = T[T.snaps_total >= 100]
    for c in COMPS:
        expo_col = "w_snaps_splash" if c in P["best_game_comps"] else "w_snaps"
        prior = reg.groupby("role")[f"w_{c}"].sum() / reg.groupby("role")[expo_col].sum()
        # caps remove real points league-wide; rescale so each role's average rate is unchanged (ranks-only effect)
        lvl = ((reg.groupby("role")[f"wraw_{c}"].sum() / reg.groupby("role").w_snaps.sum()) / prior)
        lvl = lvl.replace([np.inf, -np.inf], np.nan).fillna(1.0)   # roles with no such events (e.g. IDL INTs)
        T[f"w_{c}"] = T[f"w_{c}"] * T.role.map(lvl).fillna(1.0)
        prior = prior * lvl
        expo = T[expo_col]
        k = P[f"k_{c}"] * (P["splash_k_mult"] if P["robust"] and c in P["splash_k_comps"] else 1.0)
        T[f"rate_{c}"] = (T[f"w_{c}"] + k * T.role.map(prior)) / (expo + k)
    rs = T.recent_snap_pct.fillna(T.season_snap_pct)
    T["proj_snap_pct"] = (P["snap_recent_w"] * rs + (1 - P["snap_recent_w"]) * T.season_snap_pct).fillna(0)
    T["snap_trend"] = T.recent_snap_pct - T.season_snap_pct

    log = log.merge(T[["gsis_id", "role"]], on="gsis_id", how="left")
    return T, log, team_def, team_off


# ============================================================================
def project(D: dict, week: int) -> pd.DataFrame:
    hm = week - 1
    sched = D["sched"]
    T, log, team_def, team_off = player_table(D, week)
    off, meta = offense_profile(D, week, log)
    olp = ol_personnel(D, week)
    lg = meta["lg"]

    ros = D["rosters"][D["rosters"].week == week].drop_duplicates("gsis_id").set_index("gsis_id")
    T["team"] = T.gsis_id.map(ros.team).fillna(T.stat_team)
    T["roster_status"] = T.gsis_id.map(ros.status)
    T["yahoo_id"] = T.gsis_id.map(ros.yahoo_id)
    T = T[T.roster_status.isna() | (T.roster_status == "ACT")].copy()
    inj = D["inj"]
    iw = inj[inj.week == week].drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
    il = inj[inj.week == hm].drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
    T["inj_report"] = T.gsis_id.map(iw.report_status)
    T["inj_practice"] = T.gsis_id.map(iw.practice_status)
    T["injury"] = T.gsis_id.map(iw.practice_primary_injury).fillna(T.gsis_id.map(iw.report_primary_injury))
    T["last_week_status"] = T.gsis_id.map(il.report_status)

    wk = sched[(sched.week == week) & (sched.game_type == "REG")]
    gm = pd.concat([
        pd.DataFrame({"team": wk.home_team, "opp": wk.away_team, "home": 1, "spread_for": wk.spread_line,
                      "total": wk.total_line, "gameday": wk.gameday, "opp_qb_id": wk.away_qb_id, "opp_qb": wk.away_qb_name}),
        pd.DataFrame({"team": wk.away_team, "opp": wk.home_team, "home": 0, "spread_for": -wk.spread_line,
                      "total": wk.total_line, "gameday": wk.gameday, "opp_qb_id": wk.home_qb_id, "opp_qb": wk.home_qb_name}),
    ])  # spread_line > 0 = home favored -> spread_for > 0 = this defense's team favored
    T = T.merge(gm, on="team", how="left")
    T = T[T.opp.notna()].copy()   # drop byes

    played = sched[(sched.game_type == "REG") & (sched.week <= hm) & sched.result.notna()]
    tw = pd.concat([played[["home_team", "week"]].rename(columns={"home_team": "team"}),
                    played[["away_team", "week"]].rename(columns={"away_team": "team"})]).groupby("team").week.apply(list).to_dict()
    T["missed_recent"] = [sum(1 for w in tw.get(t, []) if w > lw) for t, lw in zip(T.team, T.last_game_week)]

    own_def_pg = team_def.assign(w=P["decay"] ** (hm - team_def.week)).groupby("team").apply(
        lambda x: wmean(x.team_def_snaps, x.w), include_groups=False)
    opp_off_pg = team_off.assign(w=P["decay"] ** (hm - team_off.week)).groupby("team").apply(
        lambda x: wmean(x.team_off_snaps, x.w), include_groups=False)
    lg_snaps = own_def_pg.mean()
    a, lo, hi = P["opp_alpha"], *P["clip"]
    shr = lambda raw: float(np.clip(1 + a * (raw - 1), lo, hi))

    fac_rows = []
    for _, r in T.iterrows():
        o = off.loc[r.opp]
        spread = r.spread_for if pd.notna(r.spread_for) else 0.0
        total = r.total if pd.notna(r.total) else LEAGUE_AVG_TOTAL
        tot_f = 1 + P["total_per_pt"] * (total - LEAGUE_AVG_TOTAL)
        exp_snaps = (0.5 * own_def_pg.get(r.team, lg_snaps) + 0.5 * opp_off_pg.get(r.opp, lg_snaps)) * tot_f
        exp_db = o.db_pg * (1 + P["script_db_per_pt"] * spread) * tot_f
        exp_runs = o.runs_pg * (1 + P["script_run_per_pt"] * spread) * tot_f
        db_f, run_f = exp_db / lg.db_pg, exp_runs / lg.runs_pg
        # per-snap factors: volume of the relevant play type per defensive snap
        snap_f = exp_snaps / lg_snaps
        db_share_f, run_share_f = db_f / snap_f, run_f / snap_f
        olm = olp.ol_missing.get(r.opp, 0.0) if len(olp) else 0.0
        ol_f = 1 + P["ol_miss_per"] * olm
        pr = o.pr_idx * ol_f                  # pass-rush opportunity quality
        stuff = o.run_idx * ol_f              # run-stuff quality
        qb_int = meta["qb"].int_rate_shr.get(r.opp_qb_id, np.nan) if pd.notna(r.opp_qb_id) else np.nan
        if pd.isna(qb_int):  # unknown / no attempts yet -> team rate, nudged up for an unproven QB
            qb_int = o.int_rate * (1.10 if pd.notna(r.opp_qb_id) else 1.0)
        int_f = qb_int / meta["lg_int"]
        adot_f = o.adot / lg.adot
        tgt_f = (o.wrte_tgt_pg / lg.wrte_tgt_pg) / snap_f
        fum_f = o.fum_per_play / lg.fum_per_play
        fpa = meta["fpa_idx"].get((r.opp, r.role), 1.0)
        role = r.role
        if role in ("EDGE", "IDL"):
            f = dict(sack=shr(pr * db_share_f), tfl=shr(stuff * run_share_f),
                     tackle=shr(0.5 * run_share_f + 0.5 * fpa), int=shr(db_share_f), pd=shr(db_share_f),
                     ff=shr(0.5 * fum_f + 0.5 * pr * db_share_f), other=1.0)
        elif role == "LB":
            f = dict(tackle=shr(P["lb_run_w"] * run_share_f + (1 - P["lb_run_w"]) * fpa),
                     tfl=shr(stuff * run_share_f), sack=shr(pr * db_share_f),
                     int=shr(int_f * db_share_f), pd=shr(db_share_f), ff=shr(fum_f), other=1.0)
        else:  # CB / S
            f = dict(tackle=shr(0.5 * tgt_f + 0.5 * fpa), int=shr(int_f * db_share_f * adot_f ** 0.5),
                     pd=shr(db_share_f * adot_f ** 0.5), ff=shr(fum_f), tfl=shr(stuff * run_share_f),
                     sack=shr(pr * db_share_f), other=1.0)
        f.update(dict(exp_snaps=exp_snaps, exp_opp_db=exp_db, exp_opp_runs=exp_runs, ol_pr_idx=o.pr_idx,
                      ol_run_idx=o.run_idx, ol_missing=olm,
                      ol_missing_names=olp.ol_missing_names.get(r.opp, "") if len(olp) else "",
                      opp_sack_rate_adj=o.sack_rate_adj, opp_hit_rate_adj=o.hit_rate_adj,
                      opp_stuff_rate_adj=o.stuff_rate_adj, opp_qb_int_rate=qb_int, opp_adot=o.adot,
                      opp_plays_pg=o.plays_pg, opp_runs_pg=o.runs_pg, opp_db_pg=o.db_pg,
                      opp_wrte_tgt_pg=o.wrte_tgt_pg, opp_fpa_idx=fpa))
        fac_rows.append({**{f"f_{k}" if k in COMPS else k: v for k, v in f.items()}})
    F = pd.DataFrame(fac_rows, index=T.index)
    T = pd.concat([T, F], axis=1)

    T["proj_snaps"] = T.proj_snap_pct * T.exp_snaps
    for c in COMPS:
        T[f"proj_{c}"] = T.proj_snaps * T[f"rate_{c}"] * T[f"f_{c}"]
    model = T[[f"proj_{c}" for c in COMPS]].sum(axis=1)
    form = T.recent_ppg * (T.exp_snaps / lg_snaps)
    T["proj_raw"] = (1 - P["form_w"]) * model + P["form_w"] * form
    T["proj_uncal"] = T.proj_raw
    if CAL_MODE == "split" and CAL_SPLIT:
        # Nov 3 big-play audit: calibrate tackle points and big-play points separately by role group.
        # The old total-points CAL (DL slope .745) also shrank pass rushers' sack/TFL upside, which the raw
        # model already had calibrated (DL/EDGE big-play slope .99), so rankings leaned on tackle volume.
        grp = np.where(T.role.isin(["EDGE", "IDL"]), "DL", np.where(T.role == "LB", "LB", "DB"))
        big = [c for c in COMPS if c != "tackle"]
        bsum = T[[f"proj_{c}" for c in big]].sum(axis=1)
        tk_ab = [CAL_SPLIT[g]["tk"] for g in grp]; bg_ab = [CAL_SPLIT[g]["big"] for g in grp]
        T["proj_tackle"] = [max(a + b * x, 0.0) for (a, b), x in zip(tk_ab, T.proj_tackle)]
        bnew = pd.Series([max(a + b * x, 0.0) for (a, b), x in zip(bg_ab, bsum)], index=T.index)
        br = (bnew / bsum.replace(0, np.nan)).fillna(1.0)
        for c in big:
            T[f"proj_{c}"] = T[f"proj_{c}"] * br
        T["proj_raw"] = T[[f"proj_{c}" for c in COMPS]].sum(axis=1)
    else:
        ca = T.pos.map(lambda p: CAL.get(p, (0.0, 1.0)))
        T["proj_raw"] = [a + b * x for (a, b), x in zip(ca, T.proj_raw)]
        cr = (T.proj_raw / T.proj_uncal.replace(0, np.nan)).fillna(1.0)
        for c in COMPS:   # keep components (used by boom.py sims) consistent with the calibrated total
            T[f"proj_{c}"] = T[f"proj_{c}"] * cr
    mult = T.inj_report.map({"Out": 0.0, "Doubtful": 0.25, "Questionable": 0.85}).fillna(1.0)
    dnp = T.inj_practice.fillna("").str.startswith("Did Not")
    mult = np.where(T.inj_report.isna() & dnp, 0.85, mult)
    mult = np.where((T.missed_recent > 0) & T.inj_report.isna(), mult * MISSED_GAME_MULT, mult)
    T["proj_pts"] = (T.proj_raw * mult).round(2)
    T = T[T.proj_snap_pct >= MIN_SNAP_SHARE_RATED].copy()
    LAST["off"], LAST["olp"] = off, olp
    return T


# ============================================================================
def finalize(T: pd.DataFrame, week: int) -> pd.DataFrame:
    hm = week - 1
    rate = lambda s: (100 * (s / s.max()).clip(0, 1)).round(0)
    T["rating_pos"] = T.groupby("pos").proj_pts.transform(rate)
    T["rating_overall"] = rate(T.proj_pts)
    T["rank_pos"] = T.groupby("pos").proj_pts.rank(ascending=False, method="first").astype(int)
    T["rank_overall"] = T.proj_pts.rank(ascending=False, method="first").astype(int)
    T["matchup"] = np.where(T.home == 1, "vs " + T.opp, "@ " + T.opp)
    T["proj_tackle_pts"] = T.proj_tackle
    T["proj_splash_pts"] = T[[f"proj_{c}" for c in COMPS if c != "tackle"]].sum(axis=1)
    T["x_sacks_per_game"] = T.proj_sack / SCORING["sack"]

    def ol_note(r):
        q = "weak" if r.ol_pr_idx >= 1.12 else "below-avg" if r.ol_pr_idx >= 1.04 else "strong" if r.ol_pr_idx <= 0.88 else "above-avg" if r.ol_pr_idx <= 0.96 else "average"
        s = (f"{r.opp} OL {q} in pass pro (adj sack {r.opp_sack_rate_adj:.1%}, hit {r.opp_hit_rate_adj:.1%}/dropback), "
             f"~{r.exp_opp_db:.0f} exp dropbacks")
        if r.ol_missing >= 0.4:
            s += f"; OL banged up: {r.ol_missing_names}"
        return s
    T["ol_matchup"] = np.where(T.role.isin(["EDGE", "IDL"]) | (T.f_sack >= 1.10), T.apply(ol_note, axis=1), "")

    def flags(r):
        f = []
        if r.proj_snap_pct < LOW_SNAP_FLAG: f.append(f"LOW_SNAP({r.proj_snap_pct:.0%})")
        if r.snap_trend <= -0.10: f.append("SNAPS_DOWN")
        if r.snap_trend >= 0.10: f.append("SNAPS_UP")
        if r.missed_recent > 0:
            st = f",W{hm}:{r.last_week_status}" if pd.notna(r.last_week_status) else ""
            f.append(f"MISSED_LAST_{r.missed_recent}(last played W{r.last_game_week}{st})")
        if pd.notna(r.inj_report) or pd.notna(r.inj_practice):
            f.append(f"INJ:{r.inj_report if pd.notna(r.inj_report) else r.inj_practice}")
        if r.games < 3: f.append("SMALL_SAMPLE")
        if r.pos == "LB" and r.role == "EDGE": f.append("EDGE_LB")
        return ";".join(f)
    T["flags"] = T.apply(flags, axis=1)

    def reason(r):
        b = [f"{r.recent_ppg:.1f} wtd-L4 ({r.season_ppg:.1f} ssn), {r.proj_snap_pct:.0%} snaps"]
        if r.role in ("EDGE", "IDL"):
            b.append(f"{r.qb_hits:g} QB hits/{r.sacks:g} sk -> {r.x_sacks_per_game:.2f} xSk")
            b.append("soft OL" if r.f_sack >= 1.08 else "tough OL" if r.f_sack <= 0.92 else "neutral OL")
        elif r.role == "LB":
            b.append(f"{r.tackles_per_snap:.3f} tkl/snap")
            b.append("run-heavy/tackle-friendly opp" if r.f_tackle >= 1.05 else "low-volume opp" if r.f_tackle <= 0.95 else "neutral volume")
        else:
            b.append(f"{r.ints:g} INT/{r.pd:g} PD, {r.tackles_per_snap:.3f} tkl/snap")
            if r.f_int >= 1.08: b.append(f"INT-prone QB ({r.opp_qb})")
            if r.f_tackle >= 1.05: b.append("high WR/TE target volume")
        if pd.notna(r.spread_for) and abs(r.spread_for) >= 6:
            b.append("big fav: pass script" if r.spread_for > 0 else "big dog: run script")
        return "; ".join(b)
    T["reason"] = T.apply(reason, axis=1)
    cols = ["rank_overall", "rank_pos", "pos", "role", "position", "player", "team", "matchup", "gameday",
            "proj_pts"] + [c for c in BOOM_COLS if c in T] + \
           ["rating_pos", "rating_overall", "proj_tackle_pts", "proj_splash_pts"] + \
           [f"proj_{c}" for c in COMPS if c != "tackle"] + \
           ["x_sacks_per_game", "season_ppg", "recent_ppg", "median_ppg", "games_ge6", "games_ge6_rate", "cv_pts",
            "ppg_ex_best", "best_game_pts", "best_game_share", "games", "season_snap_pct", "recent_snap_pct",
            "proj_snap_pct", "snap_trend", "proj_snaps", "tackles_per_snap", "hits_per_snap", "solo", "ast",
            "tfl", "sacks", "qb_hits", "ints", "pd", "ff", "fr", "tds", "spread_for", "total", "opp_qb"] + \
           [f"f_{c}" for c in COMPS if c != "other"] + \
           ["ol_pr_idx", "ol_run_idx", "ol_missing", "ol_missing_names", "opp_sack_rate_adj", "opp_hit_rate_adj",
            "opp_stuff_rate_adj", "exp_opp_db", "exp_opp_runs", "opp_plays_pg", "opp_qb_int_rate", "opp_adot",
            "opp_wrte_tgt_pg", "opp_fpa_idx", "missed_recent", "last_week_status", "inj_report", "inj_practice",
            "injury", "ol_matchup", "flags", "reason", "gsis_id", "yahoo_id"]
    out = T.sort_values("proj_pts", ascending=False)[cols].copy()
    fl = out.select_dtypes("float").columns
    out[fl] = out[fl].round(3)
    return out


# ============================================================================
def baseline_project(D: dict, week: int, v2: pd.DataFrame) -> pd.Series:
    """Naive Yahoo-like baseline: season-to-date points per game."""
    return v2.season_ppg


def backtest(D: dict, weeks: list[int], verbose=True) -> pd.DataFrame:
    import legacy_v1
    from scipy.stats import spearmanr
    ps_all = score(D["ps"])
    res = []
    for wk in weeks:
        v2 = project(D, wk)
        v1 = legacy_v1.project(D, wk).set_index("gsis_id").proj_pts
        act = ps_all[ps_all.week == wk].set_index("player_id").fpts
        pool = v2[v2.proj_snap_pct >= 0.5].copy()  # fantasy-relevant regulars on teams playing
        pool["actual"] = pool.gsis_id.map(act).fillna(0.0)
        pool["m_v2"] = pool.proj_pts
        pool["m_v1"] = pool.gsis_id.map(v1).fillna(0.0)
        pool["m_base"] = pool.season_ppg
        for pos, g in pool.groupby("pos"):
            top_act = set(g.nlargest(24, "actual").gsis_id)
            for m in ["m_base", "m_v1", "m_v2"]:
                top = g.nlargest(24, m)
                res.append({"week": wk, "pos": pos, "model": m[2:], "n": len(g),
                            "spearman": spearmanr(g[m], g.actual).statistic,
                            "top24_hit": len(set(top.gsis_id) & top_act) / 24,
                            "top24_avg_pts": top.actual.mean(),
                            "mae": (g[m] - g.actual).abs().mean()})
    R = pd.DataFrame(res)
    if verbose:
        pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
        print(R.pivot_table(index=["pos"], columns="model", values=["spearman", "top24_hit", "top24_avg_pts"]).round(3))
        print("\nAll positions, mean over weeks:")
        print(R.groupby("model")[["spearman", "top24_hit", "top24_avg_pts", "mae"]].mean().round(3))
        print("\nBy week (Spearman, mean over positions):")
        print(R.pivot_table(index="week", columns="model", values="spearman").round(3))
    return R


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--backtest", default=None, help="e.g. 4-7")
    args = ap.parse_args()
    season = args.season or nfl.get_current_season()
    D = load_data(season)
    if args.backtest:
        a, b = map(int, args.backtest.split("-"))
        backtest(D, list(range(a, b + 1))).to_csv(os.path.join(args.out, f"backtest_weeks{a}-{b}.csv"), index=False)
        return
    week = args.week or detect_week(D["sched"])
    T = project(D, week)
    import boom
    T = T.merge(boom.simulate(T, D, week).drop(columns=["p_play"]), on="gsis_id", how="left")
    out = finalize(T, week)
    bcols = ["rank_overall", "pos", "role", "player", "team", "matchup", "proj_pts"] + BOOM_COLS + \
            ["median_ppg", "games_ge6", "cv_pts", "ppg_ex_best", "best_game_pts", "season_ppg", "proj_snap_pct",
             "flags", "gsis_id"]
    out[bcols].sort_values("p_ge12", ascending=False).to_csv(os.path.join(args.out, f"boom_week{week}.csv"), index=False)
    path = os.path.join(args.out, f"ratings_week{week}.csv")
    out.to_csv(path, index=False)
    hm = week - 1
    print(f"Season {season}, target week {week}. Generated {dt.datetime.now():%Y-%m-%d %H:%M} ET")
    print("Data through week:", {k: int(D[k].week.max()) for k in ["ps", "snaps", "pbp"]},
          "| rosters/injuries week:", int(D["rosters"].week.max()), int(D["inj"].week.max()) if len(D["inj"]) else None)
    wk = D["sched"][D["sched"].week == week]
    allt = set(D["sched"].home_team) | set(D["sched"].away_team)
    print("Bye teams:", ", ".join(sorted(allt - set(wk.home_team) - set(wk.away_team))))
    print(f"Wrote {len(out)} players -> {path}")
    # OL matchup table for pass rushers this week
    off, olp = LAST["off"], LAST["olp"]
    playing = sorted(set(wk.home_team) | set(wk.away_team))
    ol = off.loc[playing, ["pr_idx", "sack_rate_adj", "hit_rate_adj", "stuff_rate_adj", "db_pg"]].copy()
    ol["ol_missing"] = olp.ol_missing.reindex(ol.index).fillna(0)
    ol["pr_idx_inj"] = ol.pr_idx * (1 + P["ol_miss_per"] * ol.ol_missing)
    ol["missing"] = olp.ol_missing_names.reindex(ol.index).fillna("")
    ol = ol.sort_values("pr_idx_inj", ascending=False)
    ol.to_csv(os.path.join(args.out, f"ol_matchups_week{week}.csv"))
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print("\nOpponent OL pass-pro index (>1 = easier for pass rushers):")
    print(ol.round(3).to_string())
    for p in POS_GROUPS:
        print(f"\n=== Top 10 {p} ===")
        print(out[out.pos == p].head(10)[["rank_pos", "player", "role", "team", "matchup", "proj_pts", "rating_pos",
                                          "flags", "reason"]].to_string(index=False))


if __name__ == "__main__":
    main()
