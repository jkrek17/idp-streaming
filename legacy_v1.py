"""LEGACY v1 model, refactored to a function for backtesting. Not used for weekly output."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import nflreadpy as nfl

# ----------------------------------------------------------------------------
# CONFIG: league scoring (Jason's Yahoo league IDP settings). Edit freely.
# ----------------------------------------------------------------------------
SCORING = {
    "solo_tackle": 0.75,
    "assisted_tackle": 0.25,
    "tackle_for_loss": 1.5,
    "sack": 3.0,
    "interception": 5.0,
    "forced_fumble": 5.0,
    "fumble_recovery": 2.0,
    "defensive_td": 6.0,
    "safety": 3.0,
    "pass_defended": 1.0,
    "blocked_kick": 2.0,
}

# Model knobs ----------------------------------------------------------------
RECENT_GAME_WEIGHTS = [0.4, 0.3, 0.2, 0.1]   # most recent game first (last 4 games played)
RECENT_VS_SEASON = 0.6                       # weight on recent form vs full-season rate
SNAP_RECENT_GAMES = 3                        # snap-share trend window
# Empirical-Bayes shrinkage (pseudo-snaps of position-average rate added)
SHRINK_SNAPS_TACKLE = 120
SHRINK_SNAPS_SPLASH = 350                    # splash plays are noisier -> more shrinkage
MATCHUP_SHRINK = 0.5                         # use 50% of the raw opponent deviation (small samples)
MATCHUP_CLIP = (0.80, 1.20)
LOW_SNAP_FLAG = 0.50                         # flag players projected under 50% of defensive snaps
MIN_SNAP_SHARE_RATED = 0.15                  # players below this projected share are dropped
MISSED_GAME_MULT = 0.6                       # player missed his team's most recent game(s): likely injured
LEAGUE_AVG_TOTAL = 45.0                      # fallback Vegas total if line missing
POS_GROUPS = ["DL", "LB", "DB"]

# How much the game script (Vegas spread from the defense's perspective; + = defense's team favored)
# moves splash vs tackle opportunity, per point of spread, by position. Favorites' defenses face
# more pass attempts (sacks/INT/PD up); underdogs' defenses face more runs / clock-killing (tackles up).
SCRIPT_SPLASH_PER_PT = {"DL": 0.012, "LB": 0.006, "DB": 0.012}
SCRIPT_TACKLE_PER_PT = {"DL": -0.003, "LB": -0.006, "DB": -0.002}


# ----------------------------------------------------------------------------
def fantasy_points(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-component and total fantasy points to a nflverse weekly player-stats frame."""
    s = SCORING
    f = lambda c: df[c].fillna(0) if c in df else 0
    df = df.copy()
    df["solo"] = f("def_tackles_solo")
    # nflverse splits a shared tackle into 'tackle_with_assist' (one player) and 'tackle_assists'
    # (the other(s)); Yahoo counts both as assisted tackles.
    df["ast"] = f("def_tackles_with_assist") + f("def_tackle_assists")
    df["tfl"] = f("def_tackles_for_loss")
    df["sacks"] = f("def_sacks")
    df["qb_hits"] = f("def_qb_hits")
    df["ints"] = f("def_interceptions")
    df["pd"] = f("def_pass_defended")
    df["ff"] = f("def_fumbles_forced")
    df["fr"] = f("fumble_recovery_opp")
    df["tds"] = f("def_tds")
    df["safeties"] = f("def_safeties")
    df["blocks"] = f("def_punt_blocks") + f("def_fg_blocks") + f("def_pat_blocks")
    df["pts_tackle"] = df.solo * s["solo_tackle"] + df.ast * s["assisted_tackle"]
    df["pts_splash"] = (
        df.tfl * s["tackle_for_loss"] + df.sacks * s["sack"] + df.ints * s["interception"]
        + df.ff * s["forced_fumble"] + df.fr * s["fumble_recovery"] + df.tds * s["defensive_td"]
        + df.safeties * s["safety"] + df.pd * s["pass_defended"] + df.blocks * s["blocked_kick"]
    )
    df["fpts"] = df.pts_tackle + df.pts_splash
    return df


def detect_week(sched: pd.DataFrame) -> int:
    reg = sched[sched.game_type == "REG"]
    pending = reg[reg.result.isna()]
    if pending.empty:
        raise SystemExit("No unplayed regular-season games left in schedule.")
    return int(pending.week.min())


def wavg_recent(vals: list[float]) -> float:
    w = RECENT_GAME_WEIGHTS[: len(vals)]
    if not w:
        return np.nan
    return float(np.dot(vals[: len(w)], w) / sum(w))


def project(D: dict, week: int) -> pd.DataFrame:
    """v1 model (kept only for backtest comparison). D = preloaded full-season frames."""
    sched = D["sched"].copy()
    hist_max = week - 1

    # ---------------- load ----------------
    ps = D["ps"].copy()
    ps = ps[(ps.season_type == "REG") & (ps.week <= hist_max)]
    if ps.empty:
        raise SystemExit(f"No player stats available before week {week}.")
    snaps = D["snaps"].drop(columns=["gsis_id", "pfr_id"], errors="ignore").copy()
    snaps = snaps[(snaps.game_type == "REG") & (snaps.week <= hist_max)]
    pbp = D["pbp"]
    pbp = pbp[(pbp.season_type == "REG") & (pbp.week <= hist_max)]
    rosters = D["rosters"][D["rosters"].week <= week].copy()
    inj = D["inj"][D["inj"].week <= week].copy()

    freshness = {
        "player_stats_max_week": int(ps.week.max()),
        "snap_counts_max_week": int(snaps.week.max()) if len(snaps) else None,
        "pbp_max_week": int(pbp.week.max()) if len(pbp) else None,
        "rosters_max_week": int(rosters.week.max()),
        "injuries_max_week": int(inj.week.max()) if len(inj) else None,
    }

    # ---------------- player game log (defenders) ----------------
    ps = fantasy_points(ps)
    dfn = ps[ps.position_group.isin(POS_GROUPS)].copy()

    # map snap counts (pfr id) -> gsis id
    idmap = rosters[["gsis_id", "pfr_id"]].dropna().drop_duplicates("pfr_id")
    snaps = snaps.merge(idmap, left_on="pfr_player_id", right_on="pfr_id", how="left")
    team_def_snaps = snaps.groupby(["team", "week"]).defense_snaps.max().rename("team_def_snaps").reset_index()
    team_off_snaps = snaps.groupby(["team", "week"]).offense_snaps.max().rename("team_off_snaps").reset_index()
    psnap = snaps[snaps.defense_snaps > 0][["gsis_id", "week", "team", "defense_snaps", "defense_pct"]].dropna(subset=["gsis_id"])

    # base = every game a defender logged defensive snaps OR a stat row (stat rows w/o snaps keep NaN snaps)
    log = psnap.merge(dfn, left_on=["gsis_id", "week"], right_on=["player_id", "week"], how="outer", suffixes=("_snap", ""))
    log["gsis_id"] = log.gsis_id.fillna(log.player_id)
    log["team"] = log.team.fillna(log.team_snap)
    for c in ["solo", "ast", "tfl", "sacks", "qb_hits", "ints", "pd", "ff", "fr", "tds", "safeties", "blocks",
              "pts_tackle", "pts_splash", "fpts"]:
        log[c] = log[c].fillna(0.0)
    log = log.merge(team_def_snaps, on=["team", "week"], how="left")

    # position group from roster when stats row missing
    rpos = rosters.sort_values("week").drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
    pos_map = {"DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "OLB": "LB", "ILB": "LB", "MLB": "LB", "LB": "LB",
               "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB", "SAF": "DB"}
    log["position_group"] = log.position_group.fillna(log.gsis_id.map(rpos.position).map(pos_map))
    log = log[log.position_group.isin(POS_GROUPS)]
    log["player_display_name"] = log.player_display_name.fillna(log.gsis_id.map(rpos.full_name))
    log = log.sort_values(["gsis_id", "week"])

    # ---------------- player features ----------------
    rows = []
    for pid, g in log.groupby("gsis_id"):
        g = g.sort_values("week", ascending=False)  # most recent first
        snaps_known = g.defense_snaps.notna()
        gs = g[snaps_known]
        n = len(g)
        rec = g.head(len(RECENT_GAME_WEIGHTS))
        tot_snaps = gs.defense_snaps.sum()
        rec_s = gs.head(len(RECENT_GAME_WEIGHTS))
        rows.append({
            "gsis_id": pid,
            "player": g.player_display_name.iloc[0],
            "pos": g.position_group.iloc[0],
            "position": g.position.dropna().iloc[0] if g.position.notna().any() else rpos.position.get(pid),
            "stat_team": g.team.iloc[0],
            "games": n,
            "last_game_week": int(g.week.iloc[0]),
            "season_ppg": g.fpts.mean(),
            "recent_ppg": wavg_recent(rec.fpts.tolist()),
            "season_snap_pct": gs.defense_pct.mean() if len(gs) else np.nan,
            "recent_snap_pct": gs.head(SNAP_RECENT_GAMES).defense_pct.mean() if len(gs) else np.nan,
            "snaps_total": tot_snaps,
            "tkl_pts_season": gs.pts_tackle.sum(), "spl_pts_season": gs.pts_splash.sum(),
            "tkl_pts_recent": rec_s.pts_tackle.sum(), "spl_pts_recent": rec_s.pts_splash.sum(),
            "snaps_recent": rec_s.defense_snaps.sum(),
            "solo": g.solo.sum(), "ast": g.ast.sum(), "tfl": g.tfl.sum(), "sacks": g.sacks.sum(),
            "qb_hits": g.qb_hits.sum(), "ints": g.ints.sum(), "pd": g.pd.sum(), "ff": g.ff.sum(),
            "fr": g.fr.sum(), "tds": g.tds.sum(),
        })
    P = pd.DataFrame(rows)

    # position priors (points per defensive snap) among regulars
    reg_mask = P.snaps_total >= 100
    prior_tkl = (P[reg_mask].groupby("pos").tkl_pts_season.sum() / P[reg_mask].groupby("pos").snaps_total.sum())
    prior_spl = (P[reg_mask].groupby("pos").spl_pts_season.sum() / P[reg_mask].groupby("pos").snaps_total.sum())

    def shrunk(pts, snp, prior, k):
        return (pts + k * prior) / (snp + k)

    P["prior_tkl"] = P.pos.map(prior_tkl)
    P["prior_spl"] = P.pos.map(prior_spl)
    tkl_season = shrunk(P.tkl_pts_season, P.snaps_total, P.prior_tkl, SHRINK_SNAPS_TACKLE)
    tkl_recent = shrunk(P.tkl_pts_recent, P.snaps_recent, P.prior_tkl, SHRINK_SNAPS_TACKLE)
    spl_season = shrunk(P.spl_pts_season, P.snaps_total, P.prior_spl, SHRINK_SNAPS_SPLASH)
    spl_recent = shrunk(P.spl_pts_recent, P.snaps_recent, P.prior_spl, SHRINK_SNAPS_SPLASH)
    P["tkl_rate"] = RECENT_VS_SEASON * tkl_recent + (1 - RECENT_VS_SEASON) * tkl_season
    P["spl_rate"] = RECENT_VS_SEASON * spl_recent + (1 - RECENT_VS_SEASON) * spl_season
    P["tackles_per_snap"] = (P.solo + P.ast) / P.snaps_total.replace(0, np.nan)
    P["splash_per_snap"] = (P.sacks + P.tfl + P.ints + P.pd + P.ff) / P.snaps_total.replace(0, np.nan)
    P["proj_snap_pct"] = (0.65 * P.recent_snap_pct.fillna(P.season_snap_pct)
                          + 0.35 * P.season_snap_pct).fillna(0)
    P["snap_trend"] = P.recent_snap_pct - P.season_snap_pct

    # ---------------- current team / status ----------------
    rw = rosters[rosters.week == rosters.week.max()].drop_duplicates("gsis_id").set_index("gsis_id")
    P["team"] = P.gsis_id.map(rw.team).fillna(P.stat_team)
    P["roster_status"] = P.gsis_id.map(rw.status)
    P["yahoo_id"] = P.gsis_id.map(rw.yahoo_id)
    P = P[P.roster_status.isna() | (P.roster_status == "ACT")]  # drop IR/cut/practice squad
    if len(inj):
        iw = inj[inj.week == week].drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
        P["inj_report"] = P.gsis_id.map(iw.report_status)
        P["inj_practice"] = P.gsis_id.map(iw.practice_status)
        P["injury"] = P.gsis_id.map(iw.practice_primary_injury).fillna(P.gsis_id.map(iw.report_primary_injury))
    else:
        P["inj_report"] = P["inj_practice"] = P["injury"] = np.nan

    # ---------------- schedule / opponent ----------------
    wk = sched[(sched.week == week) & (sched.game_type == "REG")]
    gm = pd.concat([
        pd.DataFrame({"team": wk.home_team, "opp": wk.away_team, "home": 1,
                      "spread_for": wk.spread_line, "total": wk.total_line, "gameday": wk.gameday}),
        pd.DataFrame({"team": wk.away_team, "opp": wk.home_team, "home": 0,
                      "spread_for": -wk.spread_line, "total": wk.total_line, "gameday": wk.gameday}),
    ])  # nflverse spread_line > 0 means home favored -> spread_for > 0 means this defense's team favored
    all_teams = set(sched.home_team) | set(sched.away_team)
    bye_teams = sorted(all_teams - set(gm.team))
    P = P.merge(gm, on="team", how="left")
    P["on_bye"] = P.opp.isna()

    # team games already played -> how many of his team's most recent games did the player miss?
    played = sched[(sched.game_type == "REG") & (sched.week <= hist_max) & sched.result.notna()]
    team_weeks = pd.concat([played[["home_team", "week"]].rename(columns={"home_team": "team"}),
                            played[["away_team", "week"]].rename(columns={"away_team": "team"})])
    tw = team_weeks.groupby("team").week.apply(lambda w: sorted(w, reverse=True)).to_dict()
    P["missed_recent"] = [sum(1 for w in tw.get(t, []) if w > lw) for t, lw in zip(P.team, P.last_game_week)]
    if len(inj):
        last_inj = inj[inj.week == hist_max].drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
        P["last_week_status"] = P.gsis_id.map(last_inj.report_status)
    else:
        P["last_week_status"] = np.nan

    # ---------------- opponent offense profile (from pbp + defender stats) ----------------
    plays = pbp[pbp.play_type.isin(["pass", "run"]) & (pbp.two_point_attempt != 1)]
    off = plays.groupby("posteam").agg(
        games=("game_id", "nunique"), plays=("play_id", "size"),
        pass_att=("pass_attempt", "sum"), rush_att=("rush_attempt", "sum"),
        sacks=("sack", "sum"), tfl=("tackled_for_loss", "sum"),
        ints=("interception", "sum"), fum_lost=("fumble_lost", "sum"), fum=("fumble", "sum"),
        dropbacks=("qb_dropback", "sum"),
    )
    for c in ["plays", "pass_att", "rush_att", "sacks", "tfl", "ints", "fum_lost", "fum"]:
        off[c + "_pg"] = off[c] / off.games
    off["sack_rate"] = off.sacks / off.dropbacks
    off["giveaway_pg"] = off.ints_pg + off.fum_pg  # all fumbles = FF/FR chances
    off_snaps_pg = team_off_snaps.groupby("team").team_off_snaps.mean()
    off["off_snaps_pg"] = off_snaps_pg

    # fantasy points allowed to each defensive position group (by opponent offense)
    fpa = dfn.groupby(["opponent_team", "position_group", "week"])[["pts_tackle", "pts_splash"]].sum().reset_index()
    fpa = fpa.groupby(["opponent_team", "position_group"])[["pts_tackle", "pts_splash"]].mean()
    lg_fpa = fpa.groupby("position_group").mean()
    fpa_idx = (fpa / lg_fpa.reindex(fpa.index.get_level_values(1)).values)

    lg = off.mean(numeric_only=True)
    adj = lambda raw: np.clip(1 + MATCHUP_SHRINK * (raw - 1), *MATCHUP_CLIP)

    own_def_snaps_pg = team_def_snaps.groupby("team").team_def_snaps.mean()

    def matchup(r):
        if r.on_bye:
            return pd.Series(dtype=float)
        o = off.loc[r.opp]
        pos = r.pos
        # volume: expected defensive snaps vs this opponent
        exp_snaps = 0.5 * own_def_snaps_pg.get(r.team, lg.off_snaps_pg) + 0.5 * o.off_snaps_pg
        vol = exp_snaps / own_def_snaps_pg.mean()
        total = r.total if pd.notna(r.total) else LEAGUE_AVG_TOTAL
        spread = r.spread_for if pd.notna(r.spread_for) else 0.0
        vol *= 1 + 0.003 * (total - LEAGUE_AVG_TOTAL)
        # tackle matchup: position-specific tackle points allowed + rush share for LB/DL
        tk_fpa = fpa_idx.loc[(r.opp, pos), "pts_tackle"] if (r.opp, pos) in fpa_idx.index else 1.0
        rush_idx = o.rush_att_pg / lg.rush_att_pg
        tk_raw = 0.7 * tk_fpa + 0.3 * (rush_idx if pos in ("DL", "LB") else o.pass_att_pg / lg.pass_att_pg)
        tk = adj(tk_raw) * (1 + SCRIPT_TACKLE_PER_PT[pos] * spread)
        # splash matchup: sacks/TFL/turnovers allowed by opponent + splash FPA + pass volume
        sp_fpa = fpa_idx.loc[(r.opp, pos), "pts_splash"] if (r.opp, pos) in fpa_idx.index else 1.0
        sack_idx = o.sack_rate / lg.sack_rate
        tfl_idx = o.tfl_pg / lg.tfl_pg
        give_idx = o.giveaway_pg / lg.giveaway_pg
        pass_idx = o.pass_att_pg / lg.pass_att_pg
        if pos == "DL":
            sp_raw = 0.35 * sack_idx + 0.25 * tfl_idx + 0.15 * give_idx + 0.25 * sp_fpa
        elif pos == "LB":
            sp_raw = 0.25 * tfl_idx + 0.20 * sack_idx + 0.20 * give_idx + 0.15 * pass_idx + 0.20 * sp_fpa
        else:
            sp_raw = 0.30 * give_idx + 0.25 * pass_idx + 0.10 * tfl_idx + 0.35 * sp_fpa
        sp = adj(sp_raw) * (1 + SCRIPT_SPLASH_PER_PT[pos] * spread)
        return pd.Series({
            "exp_team_def_snaps": exp_snaps, "vol_factor": vol, "tackle_factor": tk, "splash_factor": sp,
            "opp_plays_pg": o.plays_pg, "opp_pass_att_pg": o.pass_att_pg, "opp_rush_att_pg": o.rush_att_pg,
            "opp_sacks_allowed_pg": o.sacks_pg, "opp_tfl_allowed_pg": o.tfl_pg,
            "opp_giveaways_pg": o.giveaway_pg, "opp_fpa_idx_tkl": tk_fpa, "opp_fpa_idx_splash": sp_fpa,
        })

    M = P.apply(matchup, axis=1)
    P = pd.concat([P, M], axis=1)

    # ---------------- projection ----------------
    act = P[~P.on_bye].copy()
    act["proj_snaps"] = act.proj_snap_pct * act.exp_team_def_snaps * (act.vol_factor / (act.exp_team_def_snaps / own_def_snaps_pg.mean()))
    act["proj_tackle_pts"] = act.proj_snaps * act.tkl_rate * act.tackle_factor
    act["proj_splash_pts"] = act.proj_snaps * act.spl_rate * act.splash_factor
    model = act.proj_tackle_pts + act.proj_splash_pts
    # blend with raw weighted recent ppg (matchup-adjusted) to keep it honest to box scores
    form = act.recent_ppg * (act.tackle_factor * 0.5 + act.splash_factor * 0.5) * act.vol_factor
    act["proj_pts"] = (0.75 * model + 0.25 * form).round(2)
    # discount questionable / out players
    inj_mult = act.inj_report.map({"Out": 0.0, "Doubtful": 0.25, "Questionable": 0.85}).fillna(1.0)
    dnp = act.inj_practice.fillna("").str.startswith("Did Not")
    inj_mult = np.where(act.inj_report.isna() & dnp, 0.85, inj_mult)
    # missed his team's latest game(s) and no fresh report clearing him -> discount
    inj_mult = np.where((act.missed_recent > 0) & act.inj_report.isna(), inj_mult * MISSED_GAME_MULT, inj_mult)
    act["proj_pts"] = (act.proj_pts * inj_mult).round(2)
    act = act[act.proj_snap_pct >= MIN_SNAP_SHARE_RATED]

    # ratings 0-100: scaled to the 99th percentile projection in each group (and overall)
    def rate(s):
        top = s.max()
        return (100 * (s / top).clip(0, 1)).round(0)
    act["rating_pos"] = act.groupby("pos").proj_pts.transform(rate)
    act["rating_overall"] = rate(act.proj_pts)
    act["rank_pos"] = act.groupby("pos").proj_pts.rank(ascending=False, method="first").astype(int)
    act["rank_overall"] = act.proj_pts.rank(ascending=False, method="first").astype(int)

    # flags + one-line reason
    def flags(r):
        f = []
        if r.proj_snap_pct < LOW_SNAP_FLAG:
            f.append(f"LOW_SNAP({r.proj_snap_pct:.0%})")
        if r.snap_trend <= -0.10:
            f.append("SNAPS_DOWN")
        if r.snap_trend >= 0.10:
            f.append("SNAPS_UP")
        if r.missed_recent > 0:
            st = f",W{hist_max}:{r.last_week_status}" if pd.notna(r.last_week_status) else ""
            f.append(f"MISSED_LAST_{r.missed_recent}_GAMES(last played W{r.last_game_week}{st})")
        if pd.notna(r.inj_report) or pd.notna(r.inj_practice):
            f.append(f"INJ:{r.inj_report if pd.notna(r.inj_report) else r.inj_practice}")
        if r.games < 3:
            f.append("SMALL_SAMPLE")
        return ";".join(f)
    act["flags"] = act.apply(flags, axis=1)

    def reason(r):
        bits = [f"{r.recent_ppg:.1f} wtd-L4 ppg ({r.season_ppg:.1f} season), {r.proj_snap_pct:.0%} snaps"]
        if r.tackles_per_snap >= act[act.pos == r.pos].tackles_per_snap.quantile(0.8):
            bits.append(f"high tackle rate {r.tackles_per_snap:.3f}/snap")
        if r.spl_rate >= act[act.pos == r.pos].spl_rate.quantile(0.8):
            bits.append(f"splash: {r.sacks:g} sk/{r.tfl:g} TFL/{r.ints:g} INT/{r.pd:g} PD/{r.ff:g} FF")
        m = []
        if r.tackle_factor >= 1.05: m.append("tackle-friendly opp")
        if r.tackle_factor <= 0.95: m.append("tough tackle matchup")
        if r.splash_factor >= 1.05: m.append("opp gives up sacks/TFL/TOs")
        if r.splash_factor <= 0.95: m.append("opp limits splash plays")
        if pd.notna(r.spread_for) and abs(r.spread_for) >= 6:
            m.append("big favorite (pass script)" if r.spread_for > 0 else "big underdog (run script)")
        if m:
            bits.append(", ".join(m) + f" vs {r.opp}")
        return "; ".join(bits)
    return act
    act["reason"] = act.apply(reason, axis=1)
    act["matchup"] = np.where(act.home == 1, "vs " + act.opp, "@ " + act.opp)

    cols = ["rank_overall", "rank_pos", "pos", "position", "player", "team", "matchup", "gameday",
            "proj_pts", "rating_pos", "rating_overall", "proj_tackle_pts", "proj_splash_pts",
            "season_ppg", "recent_ppg", "games", "season_snap_pct", "recent_snap_pct", "proj_snap_pct",
            "snap_trend", "tackles_per_snap", "splash_per_snap", "solo", "ast", "tfl", "sacks", "qb_hits",
            "ints", "pd", "ff", "fr", "tds", "spread_for", "total", "tackle_factor", "splash_factor",
            "vol_factor", "opp_plays_pg", "opp_pass_att_pg", "opp_rush_att_pg", "opp_sacks_allowed_pg",
            "opp_tfl_allowed_pg", "opp_giveaways_pg", "opp_fpa_idx_tkl", "opp_fpa_idx_splash",
            "missed_recent", "last_week_status", "inj_report", "inj_practice", "injury", "flags", "reason", "gsis_id", "yahoo_id"]
    out = act.sort_values("proj_pts", ascending=False)[cols]
    num = out.select_dtypes("float").columns
    out[num] = out[num].round(3)
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"ratings_week{week}.csv")
    out.to_csv(path, index=False)

    print(f"Season {season}, target week {week}. Generated {dt.datetime.now():%Y-%m-%d %H:%M}")
    print("Data freshness:", freshness)
    print("Bye teams:", ", ".join(bye_teams) or "none")
    print(f"Wrote {len(out)} players -> {path}")
    pd.set_option("display.width", 250)
    for p in POS_GROUPS:
        print(f"\n=== Top 10 {p} ===")
        print(out[out.pos == p].head(10)[["rank_pos", "player", "team", "matchup", "proj_pts", "rating_pos",
                                            "flags", "reason"]].to_string(index=False))



