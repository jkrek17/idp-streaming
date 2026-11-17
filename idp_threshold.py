#!/usr/bin/env python3
"""
IDP threshold model (v3): P(>= 6 pts) and P(>= 12 pts) for every DL / LB / DB, every week.

Why a separate model: v2 is a mean-projection model fit on one season. A streamer is judged on whether he clears
6 (a safe start) or 12 (a week-winner), and 12+ games are rare (about 4%), so they need many seasons of history to
learn from. This model trains on 2018-present nflverse data and predicts the thresholds directly.

Pipeline (all features use only games before the target game, so backtests are leak-free):
  1. Player-game log (REG season): league fantasy points, components, snaps, PFR pressures / hurries / blitzes /
     targets / missed tackles, share of team tackles.
  2. Player history features: exponentially weighted (EW) per-game and per-snap rates over the player's past games
     (half-lives 3 and 10 games, crossing seasons), this-season and career counts, snap trend, past 6+/12+ rates.
  3. Team context: opponent offense (plays, dropbacks, runs, sack/hit/INT/fumble rates, IDP points and tackles it
     gives up by position group), own defense plays faced, Vegas spread and total, home/away, and the home stat
     crew's tackle-credit tendency (tackles and assists credited per play in games at that stadium).
  4. Gradient-boosted tree classifiers (scikit-learn) for P(6+ | plays) and P(12+ | plays) and a regressor for expected points, trained on
     seasons before the target season plus earlier weeks of the target season.
  5. Play probability from the injury report, estimated from 2018-2025 history (status -> share who played).

    python idp_threshold.py --week 11            # predictions for 2026 week 11 -> threshold_week11.csv
    python idp_threshold.py --backtest           # season / week walk-forward backtest -> threshold_backtest.txt
    python idp_threshold.py --refresh            # re-download the nflverse cache first
"""
from __future__ import annotations

import argparse
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
FIRST_SEASON = 2018

SCORING = {
    "solo_tackle": 0.75, "assisted_tackle": 0.25, "tackle_for_loss": 1.5, "sack": 3.0,
    "interception": 5.0, "forced_fumble": 5.0, "fumble_recovery": 2.0, "defensive_td": 6.0,
    "safety": 3.0, "pass_defended": 1.0, "blocked_kick": 2.0,
}
POS_GROUPS = ["DL", "LB", "DB"]
POS_MAP = {"DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "OLB": "LB", "ILB": "LB", "MLB": "LB", "LB": "LB",
           "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB", "SAF": "DB"}
THRESH = (6, 12)


# ============================================================================ data
def refresh_cache(last_season: int, full: bool = False) -> None:
    """Download nflverse data into cache/. Past seasons are stable, so by default only `last_season` is
    re-downloaded and swapped into each cached file (about 10 s); `full=True` (or a missing file) pulls everything."""
    import nflreadpy as nfl
    os.makedirs(CACHE, exist_ok=True)
    pbp_cols = ["season", "week", "season_type", "game_id", "posteam", "defteam", "home_team", "play_type", "pass",
                "rush", "qb_dropback", "sack", "qb_hit", "interception", "fumble_lost", "yards_gained"]
    jobs = {
        "ps": lambda S: nfl.load_player_stats(S, summary_level="week"),
        "snaps": lambda S: nfl.load_snap_counts(S),
        "sched": lambda S: nfl.load_schedules(S),
        "rosters": lambda S: nfl.load_rosters_weekly(S),
        "inj": lambda S: nfl.load_injuries(S),
        "pfr_def": lambda S: nfl.load_pfr_advstats(S, stat_type="def", summary_level="week"),
        "pbp": lambda S: nfl.load_pbp(S).select(pbp_cols),
    }
    for name, f in jobs.items():
        path = os.path.join(CACHE, f"{name}.parquet")
        try:
            if full or not os.path.exists(path):
                f(list(range(FIRST_SEASON, last_season + 1))).to_pandas().to_parquet(path)
            else:
                old = pd.read_parquet(path)
                new = f([last_season]).to_pandas()
                old = old[old.season != last_season]
                pd.concat([old, new.astype({c: old[c].dtype for c in new.columns if c in old}, errors="ignore")],
                          ignore_index=True).to_parquet(path)
        except Exception as e:  # e.g. injuries lag at season start; keep the old file
            print(f"refresh {name} failed: {e!r}")


def load(name: str) -> pd.DataFrame:
    path = os.path.join(CACHE, f"{name}.parquet")
    if not os.path.exists(path):
        import datetime as dt
        today = dt.date.today()
        refresh_cache(today.year if today.month >= 8 else today.year - 1, full=True)
    return pd.read_parquet(path)


def norm_name(x) -> str:
    import re
    s = re.sub(r"[^a-z ]", "", str(x).lower().replace("-", " "))
    return " ".join(w for w in s.split() if w not in {"jr", "sr", "ii", "iii", "iv", "v"})


def score(df: pd.DataFrame) -> pd.DataFrame:
    s, df = SCORING, df.copy()
    f = lambda c: df[c].fillna(0) if c in df else 0
    df["solo"] = f("def_tackles_solo")
    df["ast"] = f("def_tackles_with_assist") + f("def_tackle_assists")   # same definition as idp_ratings.score
    df["tfl"], df["sacks"], df["qb_hits"] = f("def_tackles_for_loss"), f("def_sacks"), f("def_qb_hits")
    df["ints"], df["pd"], df["ff"] = f("def_interceptions"), f("def_pass_defended"), f("def_fumbles_forced")
    df["fr"], df["tds"], df["safeties"] = f("fumble_recovery_opp"), f("def_tds"), f("def_safeties")
    df["blocks"] = f("def_punt_blocks") + f("def_fg_blocks") + f("def_pat_blocks")
    df["p_tackle"] = df.solo * s["solo_tackle"] + df.ast * s["assisted_tackle"]
    df["p_big"] = (df.tfl * s["tackle_for_loss"] + df.sacks * s["sack"] + df.ints * s["interception"]
                   + df.pd * s["pass_defended"] + df.ff * s["forced_fumble"] + df.fr * s["fumble_recovery"]
                   + df.tds * s["defensive_td"] + df.safeties * s["safety"] + df.blocks * s["blocked_kick"])
    df["fpts"] = df.p_tackle + df.p_big
    return df


# ============================================================================ player-game log
def player_games() -> pd.DataFrame:
    ps = load("ps")
    ps = score(ps[ps.season_type == "REG"])
    ros = load("rosters")
    ros = ros[ros.game_type.fillna("REG") == "REG"]
    sn = load("snaps")
    sn = sn[sn.game_type == "REG"]
    # snaps -> gsis: pfr id via rosters, else normalized name + team + season
    idmap = ros[["gsis_id", "pfr_id"]].dropna().drop_duplicates("pfr_id").set_index("pfr_id").gsis_id
    sn["gsis_id"] = sn.pfr_player_id.map(idmap)
    r = ros.dropna(subset=["gsis_id"]).copy()
    r["k"] = r.full_name.map(norm_name) + "|" + r.team + "|" + r.season.astype(str)
    nmap = r.drop_duplicates("k", keep="last").set_index("k").gsis_id
    miss = sn.gsis_id.isna()
    sn.loc[miss, "gsis_id"] = (sn.loc[miss, "player"].map(norm_name) + "|" + sn.loc[miss, "team"] + "|"
                               + sn.loc[miss, "season"].astype(str)).map(nmap)
    sn = sn.dropna(subset=["gsis_id"]).drop_duplicates(["gsis_id", "season", "week"])
    sn = sn[["gsis_id", "season", "week", "team", "opponent", "position", "defense_snaps", "defense_pct",
             "pfr_player_id", "game_id"]].rename(columns={"position": "snap_pos", "team": "snap_team",
                                                          "opponent": "snap_opp", "game_id": "snap_game"})
    keep = ["player_id", "player_display_name", "position", "position_group", "season", "week", "team",
            "opponent_team", "solo", "ast", "tfl", "sacks", "qb_hits", "ints", "pd", "ff", "fr", "tds",
            "safeties", "blocks", "p_tackle", "p_big", "fpts"]
    ps = ps[keep].rename(columns={"player_id": "gsis_id"})
    g = sn.merge(ps, on=["gsis_id", "season", "week"], how="outer")
    g["team"] = g.team.fillna(g.snap_team)
    g["opp"] = g.opponent_team.fillna(g.snap_opp)
    # position: latest roster entry up to that week
    rp = ros.dropna(subset=["gsis_id"]).sort_values(["season", "week"]).drop_duplicates(
        ["gsis_id", "season", "week"], keep="last")[["gsis_id", "season", "week", "position", "depth_chart_position",
                                                     "full_name", "pfr_id"]]
    rp = rp.rename(columns={"position": "ros_pos", "full_name": "ros_name"})
    g = g.merge(rp, on=["gsis_id", "season", "week"], how="left")
    g["pos_detail"] = g.ros_pos.fillna(g.snap_pos).fillna(g.position)
    g["pos"] = g.position_group.where(g.position_group.isin(POS_GROUPS), g.pos_detail.map(POS_MAP))
    g = g[g.pos.isin(POS_GROUPS)].copy()
    g["player"] = g.player_display_name.fillna(g.ros_name)
    num = ["solo", "ast", "tfl", "sacks", "qb_hits", "ints", "pd", "ff", "fr", "tds", "safeties", "blocks",
           "p_tackle", "p_big", "fpts"]
    g[num] = g[num].fillna(0.0)
    # PFR advanced defense (pressures etc.)
    pf = load("pfr_def")
    pf = pf[pf.game_type == "REG"][["pfr_player_id", "season", "week", "def_times_blitzed", "def_times_hurried",
                                     "def_times_hitqb", "def_pressures", "def_targets", "def_missed_tackles",
                                     "def_completions_allowed", "def_yards_allowed"]].drop_duplicates(
        ["pfr_player_id", "season", "week"])
    g["pfr_player_id"] = g.pfr_player_id.fillna(g.pfr_id)
    g = g.merge(pf, on=["pfr_player_id", "season", "week"], how="left")
    g["played"] = (g.defense_snaps.fillna(0) > 0) | (g.solo + g.ast + g.pd + g.qb_hits > 0)
    g = g[g.played & g.team.notna()].copy()
    g["t"] = g.season * 100 + g.week
    # share of team tackles (solo + ast) in that game
    tk = g.assign(tk=g.solo + g.ast).groupby(["team", "season", "week"]).tk.transform("sum")
    g["tkl_share"] = (g.solo + g.ast) / tk.replace(0, np.nan)
    g["y6"] = (g.fpts >= 6).astype(float)
    g["y12"] = (g.fpts >= 12).astype(float)
    return g.drop_duplicates(["gsis_id", "season", "week"]).reset_index(drop=True)


# ============================================================================ team context
def team_games(G: pd.DataFrame) -> pd.DataFrame:
    """One row per team per scheduled REG game (played or not), with that game's offense/defense stats."""
    sc = load("sched")
    sc = sc[sc.game_type == "REG"]
    a = sc[["game_id", "season", "week", "gameday", "home_team", "away_team", "spread_line", "total_line", "result"]]
    home = a.rename(columns={"home_team": "team", "away_team": "opp"}).assign(home=1)
    away = a.rename(columns={"away_team": "team", "home_team": "opp"}).assign(home=0)
    away["spread_line"] = -away.spread_line        # spread_line = points the home team is favored by
    T = pd.concat([home, away], ignore_index=True)
    T = T.rename(columns={"spread_line": "spread_for"})
    T["host"] = np.where(T.home == 1, T.team, T.opp)
    pb = load("pbp")
    pb = pb[(pb.season_type == "REG") & pb.play_type.isin(["pass", "run"])]
    o = pb.groupby(["game_id", "posteam"]).agg(
        plays=("play_type", "size"), dropbacks=("qb_dropback", "sum"), runs=("rush", "sum"), sacks=("sack", "sum"),
        hits=("qb_hit", "sum"), ints=("interception", "sum"), fum=("fumble_lost", "sum")).reset_index()
    o = o.rename(columns={"posteam": "team"})
    T = T.merge(o.add_prefix("off_").rename(columns={"off_game_id": "game_id", "off_team": "team"}),
                on=["game_id", "team"], how="left")
    T = T.merge(o.add_prefix("def_").rename(columns={"def_game_id": "game_id", "def_team": "opp"}),
                on=["game_id", "opp"], how="left")   # def_* = what this team's defense faced
    # IDP production allowed by this team's OFFENSE (credited to the opposing defense), by position group
    pg = G.groupby(["season", "week", "opp", "pos"]).agg(f=("fpts", "sum"), tk=("p_tackle", "sum"),
                                                         big=("p_big", "sum")).unstack("pos")
    pg.columns = [f"allow_{a}_{b}" for a, b in pg.columns]
    pg = pg.reset_index().rename(columns={"opp": "team"})
    T = T.merge(pg, on=["season", "week", "team"], how="left")
    # stat crew: tackles + assists credited per play (both teams) and assist share, in the game
    gg = G.groupby(["season", "week", "team"]).agg(solo=("solo", "sum"), ast=("ast", "sum")).reset_index()
    T = T.merge(gg, on=["season", "week", "team"], how="left")
    T["t"] = T.season * 100 + T.week
    T["played"] = T.result.notna() & T.off_plays.notna()
    return T.sort_values(["team", "t"]).reset_index(drop=True)


def ew(df: pd.DataFrame, key: str, cols: list[str], hl: float, mask: pd.Series | None = None) -> pd.DataFrame:
    """EW mean of each col over a group's PREVIOUS rows (shifted), ignoring NaN. Rows sorted by key, time."""
    x = df[cols].astype(float)
    if mask is not None:
        x = x.where(mask)
    sh = x.groupby(df[key]).shift()
    return sh.groupby(df[key]).transform(lambda s: s.ewm(halflife=hl, ignore_na=True).mean()).add_suffix(f"_e{hl:g}")


def team_features(T: pd.DataFrame) -> pd.DataFrame:
    T = T.copy()
    T["off_sack_rate"] = T.off_sacks / T.off_dropbacks
    T["off_hit_rate"] = T.off_hits / T.off_dropbacks
    T["off_int_rate"] = T.off_ints / T.off_dropbacks
    T["off_fum_rate"] = T.off_fum / T.off_plays
    T["off_pass_rate"] = T.off_dropbacks / T.off_plays
    allow = [c for c in T.columns if c.startswith("allow_")]
    T[allow] = T[allow].where(T.played)
    off_cols = ["off_plays", "off_dropbacks", "off_runs", "off_sack_rate", "off_hit_rate", "off_int_rate",
                "off_fum_rate", "off_pass_rate"] + allow
    m = T.played
    F = pd.concat([ew(T, "team", off_cols, 8, m), ew(T, "team", ["def_plays", "def_dropbacks", "def_runs"], 8, m)],
                  axis=1)
    T = pd.concat([T, F], axis=1)
    # stat crew (host team): credited tackles per defensive play and assist share, over prior games it hosted
    T["crew_tk_per_play"] = (T.solo + T.ast) / T.def_plays
    T["crew_ast_share"] = T.ast / (T.solo + T.ast)
    H = T[T.home == 1][["host", "t", "crew_tk_per_play", "crew_ast_share", "played"]].copy()
    # both teams' defenses in a hosted game share the crew: average the two sides first
    both = T[T.played].groupby(["host", "t"])[["crew_tk_per_play", "crew_ast_share"]].mean()
    H = H.drop(columns=["crew_tk_per_play", "crew_ast_share"]).merge(both, on=["host", "t"], how="left")
    H = H.sort_values(["host", "t"])
    Hf = ew(H, "host", ["crew_tk_per_play", "crew_ast_share"], 12, H.played)
    lg = H.sort_values("t").set_index("t")[["crew_tk_per_play", "crew_ast_share"]].expanding().mean().shift()
    lg = lg[~lg.index.duplicated(keep="first")]
    H = pd.concat([H[["host", "t"]], Hf], axis=1)
    H["crew_tk_idx"] = H.crew_tk_per_play_e12 / H.t.map(lg.crew_tk_per_play)
    H["crew_ast_idx"] = H.crew_ast_share_e12 / H.t.map(lg.crew_ast_share)
    T = T.merge(H[["host", "t", "crew_tk_idx", "crew_ast_idx"]], on=["host", "t"], how="left")
    return T


# ============================================================================ player features
PSTATS = ["fpts", "p_tackle", "p_big", "solo", "ast", "tfl", "sacks", "qb_hits", "ints", "pd", "ff",
          "def_pressures", "def_times_hurried", "def_times_blitzed", "def_targets", "def_missed_tackles",
          "tkl_share", "defense_pct", "defense_snaps", "y6", "y12"]


def player_features(G: pd.DataFrame, target: pd.DataFrame | None = None) -> pd.DataFrame:
    """History features for every played game in G (from earlier games only), plus optional target rows
    (gsis_id, season, week, team, opp, pos, pos_detail) for an unplayed week."""
    G = G.copy()
    G["is_target"] = False
    if target is not None and len(target):
        tt = target.copy()
        tt["is_target"] = True
        tt["t"] = tt.season * 100 + tt.week
        G = pd.concat([G, tt], ignore_index=True)
    G = G.sort_values(["gsis_id", "t"]).reset_index(drop=True)
    real = ~G.is_target
    # per-snap stats: EW of stat / EW of snaps (ratio of EW sums)
    snaps = G.defense_snaps.where(real)
    for c in ["solo", "ast", "tfl", "sacks", "qb_hits", "ints", "pd", "ff", "def_pressures", "def_times_hurried",
              "def_times_blitzed", "def_targets", "p_tackle", "p_big", "fpts"]:
        G[f"{c}_ps"] = G[c].where(real & snaps.notna()) / snaps.where(snaps > 0)
    feats = []
    for hl in (3, 10):
        feats.append(ew(G, "gsis_id", PSTATS, hl, real))
    feats.append(ew(G, "gsis_id", [c for c in G.columns if c.endswith("_ps")], 6, real))
    F = pd.concat(feats, axis=1)
    G = pd.concat([G, F], axis=1)
    grp = G.groupby("gsis_id")
    G["n_games"] = grp.cumcount()                               # career games before this one (in data)
    G["n_season"] = G.groupby(["gsis_id", "season"]).cumcount()
    G["last_pct"] = grp.defense_pct.shift()
    G["last_fpts"] = grp.fpts.shift()
    G["last3_pct"] = grp.defense_pct.transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
    G["max_fpts_10"] = grp.fpts.transform(lambda s: s.shift().rolling(10, min_periods=1).max())
    G["prev_t"] = grp.t.shift()
    G["prev_team"] = grp.team.shift()
    G["new_team"] = (G.prev_team.notna() & (G.prev_team != G.team)).astype(float)
    G["snap_trend"] = G.defense_pct_e3 - G.defense_pct_e10
    # prior season per-game (true multi-season prior)
    ss = G[real].groupby(["gsis_id", "season"]).agg(ps_fpts=("fpts", "mean"), ps_games=("fpts", "size"),
                                                    ps_pct=("defense_pct", "mean"),
                                                    ps_press=("def_pressures", "mean")).reset_index()
    ss["season"] += 1
    G = G.merge(ss, on=["gsis_id", "season"], how="left")
    return G


def assemble(G: pd.DataFrame, T: pd.DataFrame, target: pd.DataFrame | None = None) -> pd.DataFrame:
    X = player_features(G, target)
    tf = T[["team", "season", "week", "opp", "home", "spread_for", "total_line", "crew_tk_idx", "crew_ast_idx",
            "def_plays_e8", "def_dropbacks_e8", "def_runs_e8", "game_id", "t"]].rename(columns={"opp": "opp_s"})
    X = X.drop(columns=["opp"], errors="ignore").merge(tf.drop(columns="t"), on=["team", "season", "week"], how="left")
    X = X.rename(columns={"opp_s": "opp"})
    oc = [c for c in T.columns if c.startswith("off_") and c.endswith("_e8")] + \
         [c for c in T.columns if c.startswith("allow_") and c.endswith("_e8")]
    of = T[["team", "season", "week"] + oc].rename(columns={"team": "opp"})
    X = X.merge(of, on=["opp", "season", "week"], how="left")
    # opponent production allowed to THIS player's position group
    for k in ["f", "tk", "big"]:
        X[f"opp_allow_{k}"] = np.select([X.pos == p for p in POS_GROUPS],
                                        [X[f"allow_{k}_{p}_e8"] for p in POS_GROUPS], np.nan)
    X["opp_implied"] = X.total_line / 2 - X.spread_for / 2
    # weeks since he last played vs team games since then (missed games)
    tg = T[["team", "t"]].drop_duplicates().sort_values(["team", "t"])
    tg["team_game_no"] = tg.groupby("team").cumcount()
    X = X.merge(tg, on=["team", "t"], how="left")
    prev = tg.rename(columns={"t": "prev_t", "team_game_no": "prev_game_no", "team": "prev_team"})
    X = X.merge(prev, on=["prev_team", "prev_t"], how="left")
    same = X.prev_team == X.team
    X["missed_games"] = np.where(same & (X.prev_t // 100 == X.season), X.team_game_no - X.prev_game_no - 1, np.nan)
    X["exp_snaps"] = X.defense_pct_e3 * 0.5 * X.def_plays_e8 + X.defense_pct_e10 * 0.5 * X.def_plays_e8
    X["exp_tkl_pts"] = X.p_tackle_ps_e6 * X.exp_snaps * X.crew_tk_idx.fillna(1.0)
    X["exp_press"] = X.def_pressures_ps_e6 * X.exp_snaps * (X.off_sack_rate_e8 / 0.065)
    X["role"] = X.pos_detail.fillna(X.pos)
    X = X.merge(injury_features(G), on=["gsis_id", "season", "week"], how="left")
    vac = vacated_snaps(G)
    X = X.merge(vac, on=["team", "season", "week", "pos"], how="left")
    X["vac_pos"] = X.vac_pos.fillna(0.0)
    X[["inj_q", "inj_prac"]] = X[["inj_q", "inj_prac"]].fillna(0.0)
    return X


def _final_injury_rows() -> pd.DataFrame:
    inj = load("inj")
    inj = inj[inj.game_type == "REG"].dropna(subset=["gsis_id", "week"])
    inj["season"], inj["week"] = inj.season.astype(int), inj.week.astype(int)
    return inj.sort_values("date_modified").drop_duplicates(["gsis_id", "season", "week"], keep="last")


def injury_features(G: pd.DataFrame) -> pd.DataFrame:
    """The player's own final pre-game report: questionable flag and practice participation (0 full/none, 1 limited,
    2 did not practice). Known before kickoff, so usable in training and live."""
    inj = _final_injury_rows()
    pr = inj.practice_status.fillna("")
    inj["inj_prac"] = np.where(pr.str.startswith("Did Not"), 2.0, np.where(pr.str.startswith("Limited"), 1.0, 0.0))
    inj["inj_q"] = (inj.report_status == "Questionable").astype(float)
    return inj[["gsis_id", "season", "week", "inj_q", "inj_prac"]]


def vacated_snaps(G: pd.DataFrame) -> pd.DataFrame:
    """Snap share that teammates at the same position group leave open this week: sum of each Out/Doubtful
    teammate's snap % in his last game this season (from the pre-game report, so no look-ahead)."""
    inj = _final_injury_rows()
    inj = inj[inj.report_status.isin(["Out", "Doubtful"])][["gsis_id", "season", "week", "team"]].copy()
    inj["t"] = (inj.season * 100 + inj.week).astype("int64")
    h = G[["gsis_id", "t", "season", "defense_pct", "pos"]].copy()
    h["t"] = h.t.astype("int64")
    h = h.sort_values("t")
    inj = inj.sort_values("t")
    j = pd.merge_asof(inj, h.rename(columns={"season": "h_season"}), on="t", by="gsis_id",
                      allow_exact_matches=False)
    j = j[(j.h_season == j.season) & j.pos.notna()]
    return j.groupby(["team", "season", "week", "pos"]).defense_pct.sum().rename("vac_pos").reset_index()


CAT = ["pos", "role"]
FEATURES = None   # set in feature_list()


def feature_list(X: pd.DataFrame) -> list[str]:
    drop = {"gsis_id", "season", "week", "team", "opp", "game_id", "t", "prev_t", "prev_team", "is_target",
            "team_game_no", "prev_game_no", "player", "y6", "y12", "fpts", "played"}
    base = [c for c in X.columns if (c.endswith(("_e3", "_e10", "_e6", "_e8")) or c in {
        "n_games", "n_season", "last_pct", "last_fpts", "last3_pct", "max_fpts_10", "new_team", "snap_trend",
        "ps_fpts", "ps_games", "ps_pct", "ps_press", "home", "spread_for", "total_line", "crew_tk_idx",
        "crew_ast_idx", "opp_allow_f", "opp_allow_tk", "opp_allow_big", "opp_implied", "missed_games",
        "exp_snaps", "exp_tkl_pts", "exp_press", "week", "inj_q", "inj_prac", "vac_pos"})]
    base = [c for c in base if c not in drop or c == "week"]
    base = [c for c in base if not c.startswith("allow_")]   # keep only the position-matched opp_allow_*
    return base + CAT


# ============================================================================ model
# Shallow, heavily regularized gradient-boosted trees (scikit-learn, no extra dependency). Weekly IDP outcomes are
# noisy and the signal is low-dimensional (snap share, tackle volume, pass-rush volume): bigger trees lost AUC and
# log loss on the 2023-2025 holdouts, and LightGBM with the same settings scored the same (see README).
GBM = dict(learning_rate=0.02, max_leaf_nodes=7, min_samples_leaf=1000, l2_regularization=10.0,
           categorical_features="from_dtype", early_stopping=False, random_state=7)
ROUNDS = {"y6": 400, "y12": 300, "fpts": 400}


def pool(X: pd.DataFrame) -> pd.Series:
    """Training / ranking pool: a real defender with history and a meaningful recent snap share."""
    return (X.n_games >= 1) & (X.defense_pct_e3.fillna(0) >= 0.25)


def _prep(X: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    Z = X[feats].copy()
    for c in CAT:
        Z[c] = Z[c].astype("category")
    return Z


def fit(X: pd.DataFrame, feats: list[str]):
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    Z = _prep(X, feats)
    models = {"_cats": {c: Z[c].cat.categories for c in CAT}, "_feats": feats}
    for y in ["y6", "y12"]:
        models[y] = HistGradientBoostingClassifier(max_iter=ROUNDS[y], **GBM).fit(Z, X[y])
    models["fpts"] = HistGradientBoostingRegressor(max_iter=ROUNDS["fpts"], **GBM).fit(Z, X.fpts)
    return models


def predict(models, X: pd.DataFrame) -> pd.DataFrame:
    Z = _prep(X, models["_feats"])
    for c, cats in models["_cats"].items():
        Z[c] = pd.Categorical(Z[c].astype(str), categories=cats)
    return pd.DataFrame({"p6_play": models["y6"].predict_proba(Z)[:, 1], "p12_play": models["y12"].predict_proba(Z)[:, 1],
                         "xpts_play": models["fpts"].predict(Z)}, index=X.index)


# ============================================================================ play probability
def play_prob_table(G: pd.DataFrame) -> dict:
    """Historical share of players who played, by final injury-report status (2018-2025)."""
    inj = load("inj")
    inj = inj[inj.game_type == "REG"].dropna(subset=["gsis_id"])
    inj = inj.sort_values("date_modified").drop_duplicates(["gsis_id", "season", "week"], keep="last")
    played = G[["gsis_id", "season", "week"]].assign(pl=1)
    j = inj.merge(played, on=["gsis_id", "season", "week"], how="left")
    j["pl"] = j.pl.fillna(0)
    j = j[j.position.map(POS_MAP).isin(POS_GROUPS) & (j.season < 2026)]
    rs = j.report_status.fillna("None")
    dnp = j.practice_status.fillna("").str.startswith("Did Not")
    out = {"Out": j.pl[rs == "Out"].mean(), "Doubtful": j.pl[rs == "Doubtful"].mean(),
           "Questionable": j.pl[rs == "Questionable"].mean(),
           "None_dnp": j.pl[(rs == "None") & dnp].mean(), "None": j.pl[(rs == "None") & ~dnp].mean()}
    return {k: round(float(v), 3) for k, v in out.items()}


# ============================================================================ backtest
def metrics(y, p) -> dict:
    from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss
    y, p = np.asarray(y), np.clip(np.asarray(p), 1e-4, 1 - 1e-4)
    if y.sum() == 0 or y.sum() == len(y):
        return {"n": len(y)}
    return {"n": len(y), "pos": int(y.sum()), "auc": roc_auc_score(y, p), "logloss": log_loss(y, p),
            "brier": brier_score_loss(y, p), "pred": p.mean(), "obs": y.mean()}


def build_all():
    G = player_games()
    T = team_features(team_games(G))
    X = assemble(G, T)
    feats = feature_list(X)
    return G, T, X, feats


def backtest(test_seasons=(2023, 2024, 2025, 2026), weekly_2026=True, out="threshold_backtest"):
    G, T, X, feats = build_all()
    X = X[pool(X) & (X.season >= FIRST_SEASON + 1)].copy()   # 2018 is history only
    preds = []
    for s in test_seasons:
        if s == 2026 and weekly_2026:
            for wk in sorted(X[(X.season == 2026)].week.unique()):
                if wk < 2:
                    continue
                tr = X[(X.season < 2026) | ((X.season == 2026) & (X.week < wk))]
                te = X[(X.season == 2026) & (X.week == wk)]
                m = fit(tr, feats)
                preds.append(pd.concat([te, predict(m, te)], axis=1))
        else:
            tr, te = X[X.season < s], X[X.season == s]
            m = fit(tr, feats)
            preds.append(pd.concat([te, predict(m, te)], axis=1))
        print("done", s, flush=True)
    R = pd.concat(preds, ignore_index=True)
    R.to_parquet(os.path.join(CACHE, f"{out}.parquet"))
    txt = report(R)
    open(os.path.join(HERE, f"{out}.txt"), "w").write(txt)
    print(txt)
    return R, feats


def report(R: pd.DataFrame, v2_path: str | None = None) -> str:
    """Backtest summary on starters (recent snap share >= 50%), the pool the v2 backtest used."""
    from sklearn.metrics import roc_auc_score, log_loss
    R = R[R.defense_pct_e3 >= 0.5].copy()
    R["ppg"] = R.fpts_e10.fillna(0)
    L = []
    w = L.append

    def wauc(d, y, p):
        return np.mean([roc_auc_score(g[y], g[p]) for _, g in d.groupby("pos") if 0 < g[y].sum() < len(g)])

    def topk(d, y, p, k):
        return d.groupby(["season", "week"]).apply(lambda x: x.nlargest(k, p)[y].mean()).mean()

    w("IDP threshold model v3: walk-forward backtest (each season trained only on earlier seasons; 2026 refit weekly)")
    w("Pool: defenders with recent snap share >= 50% who played. Baseline 'ppg' = EW (half-life 10 games) points/game.")
    w("AUC within pos = mean of DL/LB/DB AUCs (0.5 = coin flip). topK = share of each week's top K that hit, averaged.\n")
    w(f"{'season':>6} {'thr':>4} {'n':>5} {'base':>6} | {'AUCpos v3':>9} {'ppg':>6} | {'logloss v3':>10} {'pos-rate':>8} |"
      f" {'top10 v3':>8} {'ppg':>6} | {'top24 v3':>8} {'ppg':>6}")
    for s, g in R.groupby("season"):
        for thr, y, p in [(6, "y6", "p6_play"), (12, "y12", "p12_play")]:
            base = g.groupby("pos")[y].transform("mean")
            w(f"{s:>6} {thr:>3}+ {len(g):>5} {g[y].mean():>6.3f} | {wauc(g, y, p):>9.3f} {wauc(g, y, 'ppg'):>6.3f} |"
              f" {log_loss(g[y], g[p].clip(1e-4, 1 - 1e-4)):>10.4f} {log_loss(g[y], base):>8.4f} |"
              f" {topk(g, y, p, 10):>8.3f} {topk(g, y, 'ppg', 10):>6.3f} | {topk(g, y, p, 24):>8.3f} {topk(g, y, 'ppg', 24):>6.3f}")
    w("\n(pos-rate log loss uses the in-sample position base rate, so it is a generous baseline.)")
    for thr, y, p in [(6, "y6", "p6_play"), (12, "y12", "p12_play")]:
        R["b"] = pd.qcut(R[p], 10, duplicates="drop")
        c = R.groupby("b", observed=True).agg(n=(y, "size"), pred=(p, "mean"), obs=(y, "mean"))
        w(f"\nReliability P({thr}+), deciles, all seasons:  pred -> obs")
        w("  " + "  ".join(f"{a:.3f}->{b:.3f}" for a, b in zip(c.pred, c.obs)))
    # waiver tier: drop each week's top 24 LB / 24 DL / 36 DB by ppg (roughly rostered in a 12-team IDP league)
    R["r"] = R.groupby(["season", "week", "pos"]).ppg.rank(ascending=False)
    W = R[((R.pos == "DB") & (R.r > 36)) | ((R.pos != "DB") & (R.r > 24))]
    w(f"\nWaiver tier (outside top 24 LB / 24 DL / 36 DB by ppg each week), {len(W)} player-games:")
    for thr, y, p in [(6, "y6", "p6_play"), (12, "y12", "p12_play")]:
        w(f"  {thr}+: base {W[y].mean():.3f} | top-5 per week hit rate v3 {topk(W, y, p, 5):.3f} vs ppg {topk(W, y, 'ppg', 5):.3f}")
    v2_path = v2_path or os.path.join(CACHE, "v2_bt_2026.parquet")
    if os.path.exists(v2_path):
        V = pd.read_parquet(v2_path)
        J = R[R.season == 2026].merge(V, on=["gsis_id", "week"], suffixes=("", "_v2"))
        J = J[J.proj_snap_pct >= 0.5]
        w(f"\nHead to head with v2 on 2026 weeks {J.week.min()}-{J.week.max()} ({len(J)} player-games, v2 proj snap >= 50%):")
        for thr, y, p, q in [(6, "y6", "p6_play", "proj_pts"), (12, "y12", "p12_play", "p_ge12")]:
            line = f"  {thr}+: AUC within pos v3 {wauc(J, y, p):.3f} vs v2 {wauc(J, y, q):.3f}"
            line += f" | top10 v3 {topk(J, y, p, 10):.3f} vs v2 {topk(J, y, q, 10):.3f}"
            if thr == 12:
                line += f" | logloss v3 {log_loss(J[y], J[p].clip(1e-4, 1-1e-4)):.4f} vs v2 {log_loss(J[y], J[q].clip(1e-4, 1-1e-4)):.4f}"
            w(line)
    return "\n".join(L)


# ============================================================================ weekly predictions
def target_rows(G: pd.DataFrame, T: pd.DataFrame, season: int, week: int) -> pd.DataFrame:
    """Every defender who played in the last 4 team games of this season, on his latest team, for `week`."""
    t0 = season * 100 + week
    hs = season if (G.season == season).any() and week > 1 else season - 1   # week 1: last season's players
    H = G[(G.t < t0) & (G.season == hs)].sort_values("t")
    last = H.groupby("gsis_id").tail(1)
    recent_t = T[(T.t < t0) & (T.season == hs) & T.played].groupby("team").t.apply(lambda s: s.nlargest(4).min())
    last = last[last.t >= last.team.map(recent_t)]
    ros = load("rosters")
    ros_all = ros[(ros.season == season) & (ros.week <= week)]
    ros = ros_all.sort_values("week").drop_duplicates("gsis_id", keep="last")
    cur_team = ros.set_index("gsis_id").team
    status = ros.set_index("gsis_id").status
    tt = last[["gsis_id", "pos", "pos_detail", "player", "team"]].copy()
    tt["team"] = tt.gsis_id.map(cur_team).fillna(tt.team)
    tt["roster_status"] = tt.gsis_id.map(status)
    # missing from his team's latest weekly roster (teams on bye have no rows that week) = released or retired
    team_last = ros_all.groupby("team").week.max()
    tt["off_roster"] = tt.gsis_id.map(ros.set_index("gsis_id").week) < tt.team.map(team_last)
    tt["season"], tt["week"] = season, week
    games = T[(T.season == season) & (T.week == week)][["team", "opp"]]
    tt = tt.merge(games, on="team", how="inner")     # drops bye teams
    return tt


def injury_mult(tt: pd.DataFrame, season: int, week: int, ptab: dict) -> pd.Series:
    inj = load("inj")
    inj = inj[(inj.season == season) & (inj.week == week)].sort_values("date_modified").drop_duplicates(
        "gsis_id", keep="last").set_index("gsis_id")
    on_report = tt.gsis_id.isin(inj.index)
    rs = tt.gsis_id.map(inj.report_status)
    pr = tt.gsis_id.map(inj.practice_status).fillna("")
    p = rs.map({"Out": 0.0, "Doubtful": ptab["Doubtful"], "Questionable": ptab["Questionable"]}).astype(float)
    # on the practice report with no game status: did-not-practice vs limited/full
    listed = on_report & p.isna()
    p = p.where(~listed, np.where(pr.str.startswith("Did Not"), ptab["None_dnp"], ptab["None"]))
    p = pd.Series(p, index=tt.index).astype(float)   # NaN = not on the report at all (handled by caller)
    # roster status (IR/reserve, cut, practice squad, exempt, retired) or gone from rosters beats everything.
    # INA is last week's game-day inactive list, not this week's: those players fall to MISS_PLAY_PROB instead.
    p = p.where(~(tt.roster_status.isin(["RES", "CUT", "DEV", "EXE", "RET"]) | tt.off_roster.fillna(False)), 0.0)
    return p, rs


def weekly(season: int, week: int, write=True) -> pd.DataFrame:
    G = player_games()
    T = team_features(team_games(G))
    tt = target_rows(G, T, season, week)
    X = assemble(G, T, tt)
    feats = feature_list(X)
    tr = X[~X.is_target & pool(X) & (X.season >= FIRST_SEASON + 1)]
    te = X[X.is_target].copy()
    m = fit(tr, feats)
    te = pd.concat([te, predict(m, te)], axis=1)
    ptab = play_prob_table(G)
    p_inj, rs = injury_mult(te, season, week, ptab)
    # missed his team's latest game with no fresh report: historical share who played next week
    p_miss = MISS_PLAY_PROB
    p_play = p_inj.where(p_inj.notna(), np.where(te.missed_games.fillna(0) > 0, p_miss, HEALTHY_PLAY_PROB))
    te["p_play"] = p_play.clip(0, 1)
    te["inj_report"] = rs
    te["p_ge6"] = te.p6_play * te.p_play
    te["p_ge12"] = te.p12_play * te.p_play
    te["x_pts"] = te.xpts_play * te.p_play
    cols = ["player", "pos", "role", "team", "opp", "home", "spread_for", "total_line", "p_ge6", "p_ge12", "x_pts",
            "p_play", "inj_report", "p6_play", "p12_play", "xpts_play", "defense_pct_e3", "last_pct",
            "fpts_e3", "fpts_e10", "y6_e10", "y12_e10", "def_pressures_e10", "p_tackle_e10", "exp_snaps",
            "exp_tkl_pts", "crew_tk_idx", "opp_allow_f", "missed_games", "n_season", "gsis_id"]
    te = te[cols].sort_values("p_ge6", ascending=False)
    te = te.rename(columns={"defense_pct_e3": "snap_pct_recent", "fpts_e3": "ppg_recent", "fpts_e10": "ppg_ew10",
                            "y6_e10": "rate6_ew10", "y12_e10": "rate12_ew10", "def_pressures_e10": "pressures_pg",
                            "p_tackle_e10": "tackle_pts_pg", "n_season": "games_this_season"})
    te["rank_6"] = te.p_ge6.rank(ascending=False, method="first").astype(int)
    te["rank_12"] = te.p_ge12.rank(ascending=False, method="first").astype(int)
    if write:
        te.round(4).to_csv(os.path.join(HERE, f"threshold_week{week}.csv"), index=False)
    return te


# 2018-2025 history for 50%+ snap defenders:
MISS_PLAY_PROB = 0.58      # missed his team's last game, not on this week's report: played the next game 58% of the time
HEALTHY_PLAY_PROB = 0.977  # played last game, not on this week's report: played 97.7% (cuts, trades, late scratches)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=None, help="default: latest season in the schedule")
    ap.add_argument("--week", type=int)
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    if a.season is None:
        import datetime as dt
        today = dt.date.today()
        a.season = today.year if today.month >= 8 else today.year - 1
    if a.refresh:
        refresh_cache(a.season)
    if a.backtest:
        backtest()
        return
    if a.week is None:
        sc = load("sched")
        pend = sc[(sc.season == a.season) & (sc.game_type == "REG") & sc.result.isna()]
        a.week = int(pend.week.min())
    te = weekly(a.season, a.week)
    show = ["rank_6", "player", "pos", "team", "opp", "p_ge6", "p_ge12", "x_pts", "p_play", "inj_report",
            "snap_pct_recent", "ppg_ew10"]
    pd.set_option("display.width", 200)
    print(f"Week {a.week}: {len(te)} defenders -> threshold_week{a.week}.csv. Top 25 by P(6+):")
    print(te[show].head(25).round(3).to_string(index=False))
    print("\nTop 15 by P(12+):")
    print(te.sort_values("p_ge12", ascending=False)[show].head(15).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
