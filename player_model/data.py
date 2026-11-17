"""Multi-season nflverse loader with a local parquet cache (data_cache/, gitignored).

One tidy player-game table per season with league fantasy points, snaps, red-zone usage and
team volume, plus schedules (with Vegas lines) and injury reports.
"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
import nflreadpy as nfl
import idp_ratings as M          # IDP scoring + name normalizer
import offense as O              # offense/K scoring
from .league import POS_MAP

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
FIRST_SEASON = 2018              # 2018 only feeds priors; training targets start in 2019


def _cached(name: str, fn, refresh: bool):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name + ".parquet")
    if os.path.exists(path) and not refresh:
        return pd.read_parquet(path)
    df = fn()
    df.to_parquet(path, index=False)
    return df


def _pbp_usage(season: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["season", "week", "season_type", "posteam", "defteam", "play_type", "qb_dropback", "rush_attempt",
            "pass_attempt", "yardline_100", "receiver_player_id", "rusher_player_id", "two_point_attempt"]
    p = nfl.load_pbp([season]).select(cols).to_pandas()
    p = p[(p.season_type == "REG") & p.play_type.isin(["pass", "run"]) & (p.two_point_attempt != 1)]
    team = p.groupby(["season", "week", "posteam"]).agg(
        team_plays=("play_type", "size"), team_dropbacks=("qb_dropback", "sum"),
        team_rushes=("rush_attempt", "sum"), team_rz_plays=("yardline_100", lambda s: (s <= 20).sum()),
    ).reset_index().rename(columns={"posteam": "team"})
    rz = p.yardline_100 <= 20
    rec = p[(p.pass_attempt == 1) & p.receiver_player_id.notna()]
    rush = p[(p.rush_attempt == 1) & p.rusher_player_id.notna()]
    a = rec[rec.yardline_100 <= 20].groupby(["season", "week", "receiver_player_id"]).size().rename("rz_tgt")
    b = rec[rec.yardline_100 <= 10].groupby(["season", "week", "receiver_player_id"]).size().rename("i10_tgt")
    c = rush[rush.yardline_100 <= 20].groupby(["season", "week", "rusher_player_id"]).size().rename("rz_car")
    d = rush[rush.yardline_100 <= 5].groupby(["season", "week", "rusher_player_id"]).size().rename("i5_car")
    a.index.names = b.index.names = c.index.names = d.index.names = ["season", "week", "player_id"]
    pl = pd.concat([a, b, c, d], axis=1).fillna(0).reset_index()
    team_rz = p[rz].groupby(["season", "week", "posteam"]).agg(
        team_rz_tgt=("pass_attempt", "sum"), team_rz_car=("rush_attempt", "sum")).reset_index()
    team = team.merge(team_rz.rename(columns={"posteam": "team"}), on=["season", "week", "team"], how="left")
    return team.fillna(0), pl


def _season(season: int) -> pd.DataFrame:
    ps = nfl.load_player_stats([season], summary_level="week").to_pandas()
    ps = ps[ps.season_type == "REG"].copy()
    ps["pos"] = ps.position.map(POS_MAP)
    ps = ps[ps.pos.notna()].copy()
    ps["fpts_off"] = O.score_actual(ps)
    ps["fpts_idp"] = M.score(ps)["fpts"].values
    ps["fpts"] = np.where(ps.pos.isin(["DL", "LB", "DB"]), ps.fpts_idp, ps.fpts_off)

    # snaps -> gsis id (pfr id first, then name+team, as idp_ratings does)
    sn = nfl.load_snap_counts([season]).to_pandas()
    sn = sn[sn.game_type == "REG"]
    ro = nfl.load_rosters_weekly([season]).to_pandas()
    idmap = ro[["gsis_id", "pfr_id"]].dropna().drop_duplicates("pfr_id")
    sn = sn.merge(idmap, left_on="pfr_player_id", right_on="pfr_id", how="left")
    r = ro.dropna(subset=["gsis_id"]).copy()
    r["k"] = r.full_name.map(M.norm_name) + "|" + r.team
    nmap = r.drop_duplicates("k", keep="last").set_index("k").gsis_id
    miss = sn.gsis_id.isna()
    sn.loc[miss, "gsis_id"] = (sn.loc[miss, "player"].map(M.norm_name) + "|" + sn.loc[miss, "team"]).map(nmap).values
    sn = (sn.dropna(subset=["gsis_id"]).groupby(["season", "week", "gsis_id"])
          .agg(offense_snaps=("offense_snaps", "max"), offense_pct=("offense_pct", "max"),
               defense_snaps=("defense_snaps", "max"), defense_pct=("defense_pct", "max"),
               st_snaps=("st_snaps", "max"), sn_team=("team", "first"), sn_opp=("opponent", "first"),
               sn_pos=("position", "first"), sn_name=("player", "first"), sn_game=("game_id", "first"))
          .reset_index().rename(columns={"gsis_id": "player_id"}))
    snap_cols = ["offense_snaps", "offense_pct", "defense_snaps", "defense_pct", "st_snaps"]
    ps = ps.merge(sn[["season", "week", "player_id"] + snap_cols], on=["season", "week", "player_id"], how="left")
    # games a player was on the field but recorded no stat (0 points): nflverse player_stats omits them
    have = set(zip(ps.week, ps.player_id))
    extra = sn[[(w, i) not in have for w, i in zip(sn.week, sn.player_id)]].copy()
    extra["pos"] = extra.sn_pos.map(POS_MAP)
    idp = extra.pos.isin(["DL", "LB", "DB"])
    extra = extra[extra.pos.notna() & ((idp & (extra.defense_snaps > 0)) | (~idp & (extra.offense_snaps > 0)))]
    extra = extra.rename(columns={"sn_team": "team", "sn_opp": "opponent_team", "sn_name": "player_display_name"})
    extra["position"], extra["season_type"], extra["fpts"] = extra.sn_pos, "REG", 0.0
    extra["player_name"] = extra.player_display_name
    extra = extra.drop(columns=["sn_pos", "sn_game"])
    ps = pd.concat([ps, extra], ignore_index=True)
    num = ps.select_dtypes("number").columns.difference(snap_cols + ["season", "week"])
    ps[num] = ps[num].fillna(0)
    ps["zero_stat_game"] = ps.index >= len(ps) - len(extra)

    team, pl = _pbp_usage(season)
    ps = ps.merge(pl, on=["season", "week", "player_id"], how="left")
    ps = ps.merge(team, on=["season", "week", "team"], how="left")
    opp = team[["season", "week", "team", "team_plays", "team_dropbacks", "team_rushes"]].rename(
        columns={"team": "opponent_team", "team_plays": "opp_plays", "team_dropbacks": "opp_dropbacks",
                 "team_rushes": "opp_rushes"})
    ps = ps.merge(opp, on=["season", "week", "opponent_team"], how="left")

    bio = ro.sort_values("week").drop_duplicates("gsis_id", keep="last")[["gsis_id", "birth_date", "rookie_year",
                                                                          "draft_number", "depth_chart_position"]]
    ps = ps.merge(bio.rename(columns={"gsis_id": "player_id"}), on="player_id", how="left")
    for c in ["rz_tgt", "i10_tgt", "rz_car", "i5_car"]:
        ps[c] = ps[c].fillna(0)
    return ps


KEEP = None  # all columns kept; parquet keeps it compact


def load(seasons: list[int], refresh_current: bool = True) -> dict:
    cur = nfl.get_current_season()
    games = []
    for s in seasons:
        games.append(_cached(f"games_{s}", lambda s=s: _season(s), refresh=(s == cur and refresh_current)))
    G = pd.concat(games, ignore_index=True)
    sched = _cached("sched", lambda: nfl.load_schedules(list(range(FIRST_SEASON, cur + 1))).to_pandas(),
                    refresh=refresh_current)
    sched = sched[sched.game_type == "REG"]
    try:
        inj = _cached(f"inj_{cur}", lambda: nfl.load_injuries([cur]).to_pandas(), refresh=refresh_current)
    except Exception:
        inj = pd.DataFrame(columns=["season", "week", "gsis_id", "report_status", "practice_status"])
    try:
        ros = _cached(f"rosters_{cur}", lambda: nfl.load_rosters_weekly([cur]).to_pandas(), refresh=refresh_current)
    except Exception:
        ros = pd.DataFrame(columns=["gsis_id", "team", "status", "week"])
    players = _cached("players", lambda: nfl.load_players().to_pandas(), refresh=refresh_current)
    return {"games": G, "sched": sched, "inj": inj, "players": players, "rosters": ros, "season": cur}
