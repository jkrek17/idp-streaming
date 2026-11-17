"""Feature engineering: usage rates with empirical-Bayes shrinkage, recency-decayed production,
consistency (floor/ceiling/boom/bust) and game context.

Every feature for a game is computed only from that player's earlier games, so a row can be
used both to train (target = that game's points) and, for the latest state, to forecast.

Time axis: t = season * 30 + week, so the offseason is a 12-week gap. Decayed sums use
exp(-ln2 * dt / halflife); with halflife 8 weeks last season's games count about 1/3 as much.
"""
from __future__ import annotations
import numpy as np, pandas as pd

HL_SHORT, HL_LONG = 3.0, 8.0
CONS_N = 16                      # games in the consistency window
IDP_POS = ["DL", "LB", "DB"]
# weekly thresholds by position (league scoring): "start" ~ a weekly top-N starter, "boom" ~ weekly top-5ish
THR = {"QB": (17, 25), "RB": (10, 20), "WR": (10, 20), "TE": (7, 15), "K": (8, 13),
       "DL": (5, 10), "LB": (7, 12), "DB": (6, 11)}

# (name, numerator, denominator, kind) -> shrunk share features. kind: "binom" (share of team volume)
# or "pois" (rate per exposure).
OFF_SHARES = [
    ("snap", "offense_snaps", "team_snaps_off", "binom"),
    ("tgt_sh", "targets", "team_dropbacks", "binom"),
    ("car_sh", "carries", "team_rushes", "binom"),
    ("rz_tgt_sh", "rz_tgt", "team_rz_tgt", "binom"),
    ("rz_car_sh", "rz_car", "team_rz_car", "binom"),
    ("ay_sh", "receiving_air_yards_pos", "team_air_yards", "pois"),
    ("att_sh", "attempts", "team_dropbacks", "binom"),
    ("catch", "receptions", "targets", "binom"),
    ("ypt", "receiving_yards", "targets", "pois"),
    ("ypc", "rushing_yards", "carries", "pois"),
    ("ypa", "passing_yards", "attempts", "pois"),
    ("ptd_rate", "passing_tds", "attempts", "pois"),
    ("int_rate", "passing_interceptions", "attempts", "pois"),
    ("rtd_rate", "rec_rush_tds", "opps", "pois"),
    ("pts_per_opp", "fpts", "opps", "pois"),
]
IDP_SHARES = [
    ("snap", "defense_snaps", "team_snaps_def", "binom"),
    ("tkl_sh", "tackles", "opp_plays", "pois"),
    ("solo_sh", "def_tackles_solo", "opp_plays", "pois"),
    ("tkl_per_snap", "tackles", "defense_snaps", "pois"),
    ("tfl_rate", "def_tackles_for_loss", "defense_snaps", "pois"),
    ("sack_rate", "def_sacks", "defense_snaps", "pois"),
    ("hit_rate", "def_qb_hits", "defense_snaps", "pois"),
    ("pd_rate", "def_pass_defended", "defense_snaps", "pois"),
    ("int_rate", "def_interceptions", "defense_snaps", "pois"),
    ("ff_rate", "def_fumbles_forced", "defense_snaps", "pois"),
    ("pts_per_snap", "fpts", "defense_snaps", "pois"),
]
K_SHARES = [("fga_g", "fg_att", "one", "pois"), ("pat_g", "pat_att", "one", "pois"),
            ("fgyd_g", "fg_made_distance", "one", "pois"), ("fg_pct", "fg_made", "fg_att", "binom")]


def tcode(season, week):
    return np.asarray(season) * 30 + np.asarray(week)


def _prep(G: pd.DataFrame) -> pd.DataFrame:
    G = G.copy()
    G["t"] = tcode(G.season, G.week)
    G["one"] = 1.0
    G["tackles"] = G.def_tackles_solo + G.def_tackle_assists + G.get("def_tackles_with_assist", 0)
    G["rec_rush_tds"] = G.receiving_tds + G.rushing_tds
    G["opps"] = G.targets + G.carries
    G.loc[G.pos == "QB", "opps"] = G.attempts + G.carries
    G["receiving_air_yards_pos"] = G.receiving_air_yards.clip(lower=0)
    # team snaps per game = max snaps by any player on that side (nflverse snap pct = snaps / team snaps)
    tm = G.groupby(["season", "week", "team"]).agg(off_max=("offense_snaps", "max"),
                                                   def_max=("defense_snaps", "max"),
                                                   team_air_yards=("receiving_air_yards_pos", "sum")).reset_index()
    G = G.merge(tm, on=["season", "week", "team"], how="left")
    G["team_snaps_off"] = np.where(G.offense_pct > 0, G.offense_snaps / G.offense_pct.clip(lower=0.01), G.off_max)
    G["team_snaps_def"] = np.where(G.defense_pct > 0, G.defense_snaps / G.defense_pct.clip(lower=0.01), G.def_max)
    for c in ["offense_snaps", "defense_snaps", "team_snaps_off", "team_snaps_def"]:
        G[c] = G[c].fillna(0)
    return G.sort_values(["player_id", "t"]).reset_index(drop=True)


def _decayed(G: pd.DataFrame, cols: list[str], hl: float) -> pd.DataFrame:
    """Decayed sums of `cols` through each game, per player (inclusive of that game)."""
    lam = np.log(2) / hl
    t0 = G.groupby("player_id").t.transform("min")
    rel = (G.t - t0).to_numpy(float)
    up = np.exp(lam * rel)
    out = {}
    g = G.player_id.to_numpy()
    for c in cols + ["one"]:
        x = G[c].to_numpy(float) * up
        cs = pd.Series(x).groupby(g).cumsum().to_numpy()
        out[c] = cs / up
    return pd.DataFrame(out, index=G.index)


def estimate_k(G: pd.DataFrame, num: str, den: str, kind: str, pos_col="pos", max_season=None) -> dict:
    """Method-of-moments empirical-Bayes prior per position from player-season totals.
    Returns {pos: (prior_mean, k)} where k is pseudo-exposure added to the denominator."""
    H = G if max_season is None else G[G.season <= max_season]
    a = H.groupby([pos_col, "season", "player_id"])[[num, den]].sum().reset_index()
    a = a[a[den] > 0]
    res = {}
    for pos, d in a.groupby(pos_col):
        if len(d) < 30:
            continue
        w = d[den].to_numpy(float)
        p = d[num].to_numpy(float) / w
        mu = np.average(p, weights=w)
        var_obs = np.average((p - mu) ** 2, weights=w)
        if kind == "binom":
            samp = np.average(np.clip(mu * (1 - mu), 1e-9, None) / w, weights=w)
            vt = max(var_obs - samp, 1e-4 * max(mu * (1 - mu), 1e-9))
            k = max(mu * (1 - mu) / vt - 1, 0.5)
        else:
            samp = np.average(np.clip(mu, 1e-9, None) / w, weights=w)
            vt = max(var_obs - samp, 1e-4 * max(mu ** 2, 1e-9))
            k = max(mu / vt, 0.5) if mu > 0 else 1.0
        res[pos] = (float(mu), float(min(k, 5000)))
    return res


def build_states(G: pd.DataFrame, max_season_prior: int | None = None) -> tuple[pd.DataFrame, dict]:
    """State of each player after each game (features to forecast his NEXT game)."""
    G = _prep(G)
    specs = OFF_SHARES + IDP_SHARES + K_SHARES
    raw_cols = sorted({c for _, n, d, _ in specs for c in (n, d)} | {"fpts"})
    priors = {}
    S = G[["player_id", "player_display_name", "pos", "team", "season", "week", "t", "fpts",
           "birth_date", "rookie_year", "draft_number"]].copy()
    for hl, tag in [(HL_LONG, ""), (HL_SHORT, "_s")]:
        D = _decayed(G, raw_cols, hl)
        S["n_eff" + tag] = D["one"]
        S["ppg" + tag] = D["fpts"] / D["one"]
        for name, num, den, kind in specs:
            spec = (name, num, den, kind)
            if spec in IDP_SHARES:
                pool, pname = G.pos.isin(IDP_POS), "idp"
            elif spec in K_SHARES:
                pool, pname = G.pos == "K", "k"
            else:
                pool, pname = G.pos.isin(["QB", "RB", "WR", "TE"]), "off"
            key = (pname, name)
            if key not in priors:
                priors[key] = estimate_k(G[pool], num, den, kind, max_season=max_season_prior)
            col = name + tag
            if col not in S:
                S[col] = np.nan
                if tag == "":
                    S[name + "_den_g"] = np.nan
            for pos, (mu, k) in priors[key].items():
                m = ((G.pos == pos) & pool).to_numpy()
                S.loc[m, col] = ((D.loc[m, num] + k * mu) / (D.loc[m, den] + k)).to_numpy()
                if tag == "":
                    S.loc[m, name + "_den_g"] = (D.loc[m, den] / D.loc[m, "one"]).to_numpy()
    # rate x volume summaries that the trees otherwise need to discover
    S["exp_tgt"] = S.tgt_sh * _team_avg(G, "team_dropbacks")
    S["exp_car"] = S.car_sh * _team_avg(G, "team_rushes")
    S["exp_tkl"] = S.tkl_sh * _team_avg(G, "opp_plays")
    S["career_games"] = G.groupby("player_id").cumcount() + 1
    S["games_season"] = G.groupby(["player_id", "season"]).cumcount() + 1
    S["last_snap_pct"] = np.where(G.pos.isin(IDP_POS), G.defense_pct, G.offense_pct)
    S = S.join(_consistency(G))
    return S, priors


def _team_avg(G, col):
    # team-level decayed average volume, aligned to rows (simple: player's team season mean so far)
    tm = G.drop_duplicates(["season", "week", "team"])[["season", "week", "team", col]].sort_values(["team", "season", "week"])
    tm["avg"] = tm.groupby("team")[col].transform(lambda s: s.ewm(halflife=8, min_periods=1).mean())
    return G.merge(tm[["season", "week", "team", "avg"]], on=["season", "week", "team"], how="left")["avg"].to_numpy()


def _consistency(G: pd.DataFrame) -> pd.DataFrame:
    """Rolling floor / ceiling / boom / bust over the last CONS_N games, shrunk toward position."""
    thr_s = G.pos.map({p: v[0] for p, v in THR.items()})
    thr_b = G.pos.map({p: v[1] for p, v in THR.items()})
    G = G.assign(_start=(G.fpts >= thr_s).astype(float), _boom=(G.fpts >= thr_b).astype(float),
                 _bust=(G.fpts < 0.5 * thr_s).astype(float))
    g = G.groupby("player_id")
    roll = lambda s, f: g[s].transform(lambda x: getattr(x.rolling(CONS_N, min_periods=1), f)())
    out = pd.DataFrame(index=G.index)
    n = g.fpts.transform(lambda x: x.rolling(CONS_N, min_periods=1).count())
    out["cons_n"] = n
    out["roll_mean"] = roll("fpts", "mean")
    out["roll_sd"] = g.fpts.transform(lambda x: x.rolling(CONS_N, min_periods=2).std()).fillna(0)
    out["roll_q20"] = g.fpts.transform(lambda x: x.rolling(CONS_N, min_periods=1).quantile(0.2))
    out["roll_q80"] = g.fpts.transform(lambda x: x.rolling(CONS_N, min_periods=1).quantile(0.8))
    out["roll_max"] = g.fpts.transform(lambda x: x.rolling(CONS_N, min_periods=1).max())
    for c, k in [("_start", 6.0), ("_boom", 8.0), ("_bust", 6.0)]:
        prior = G.groupby("pos")[c].transform("mean")
        out["rate" + c] = (g[c].transform(lambda x: x.rolling(CONS_N, min_periods=1).sum()) + k * prior) / (n + k)
    out["cv"] = out.roll_sd / out.roll_mean.clip(lower=1.0)
    return out


def context(rows: pd.DataFrame, sched: pd.DataFrame, G: pd.DataFrame) -> pd.DataFrame:
    """Game context for (season, week, team) target rows: Vegas, home, opponent points allowed to position."""
    s = sched[["season", "week", "home_team", "away_team", "spread_line", "total_line", "gameday",
               "home_rest", "away_rest", "roof"]].copy()
    home = s.rename(columns={"home_team": "team", "away_team": "opp", "home_rest": "rest"}).assign(home=1)
    away = s.rename(columns={"away_team": "team", "home_team": "opp", "away_rest": "rest"}).assign(home=0)
    home["spread"] = home.spread_line            # nflverse spread_line > 0 means home favored
    away["spread"] = -away.spread_line
    tg = pd.concat([home, away])[["season", "week", "team", "opp", "home", "spread", "total_line", "rest", "roof",
                                  "gameday"]]
    tg["implied"] = tg.total_line / 2 + tg.spread / 2
    tg["dome"] = tg.roof.isin(["dome", "closed"]).astype(int)
    rows = rows.merge(tg.drop(columns="roof"), on=["season", "week", "team"], how="left")
    rows = rows.merge(opp_allowed(G), left_on=["opp", "pos", "season", "week"],
                      right_on=["opp", "pos", "season", "week"], how="left")
    return rows


def opp_allowed(G: pd.DataFrame, hl: float = 6.0) -> pd.DataFrame:
    """Decayed points allowed by each defense to each position (top-2 at the position per game,
    relative to league average), known BEFORE each week. Keyed by (opp, pos, season, week)."""
    G = G.sort_values("fpts", ascending=False)
    rk = G.groupby(["season", "week", "opponent_team", "pos"]).cumcount()
    top = G[rk < np.where(G.pos.isin(["QB", "TE", "K"]), 1, 2)]
    a = top.groupby(["season", "week", "opponent_team", "pos"]).fpts.sum().reset_index()
    lg = a.groupby(["season", "week", "pos"]).fpts.transform("mean")
    a["rel"] = a.fpts - lg
    a["t"] = tcode(a.season, a.week).astype("int64")
    a = a.sort_values("t")
    out = []
    for (opp, pos), d in a.groupby(["opponent_team", "pos"]):
        ts = pd.to_datetime(d.t.to_numpy() * 7, unit="D")
        e = d.rel.ewm(halflife=pd.Timedelta(days=7 * hl), times=ts).mean()
        out.append(pd.DataFrame({"opp": opp, "pos": pos, "t": d.t.to_numpy(), "opp_allow": e.to_numpy()}))
    o = pd.concat(out)
    # shift: value known before week w is the one after the previous game -> asof merge on t
    allw = []
    weeks = pd.DataFrame({"season": np.repeat(np.arange(2018, 2027), 19), "week": np.tile(np.arange(1, 20), 9)})
    weeks["t"] = tcode(weeks.season, weeks.week).astype("int64")
    for (opp, pos), d in o.groupby(["opp", "pos"]):
        m = pd.merge_asof(weeks.assign(tq=weeks.t - 1).sort_values("tq"), d.sort_values("t"),
                          left_on="tq", right_on="t", direction="backward", suffixes=("", "_o"))
        m["opp"], m["pos"] = opp, pos
        allw.append(m[["opp", "pos", "season", "week", "opp_allow"]])
    return pd.concat(allw).fillna({"opp_allow": 0.0})
