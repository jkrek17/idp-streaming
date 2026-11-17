"""Boom/ceiling model: Monte Carlo weekly fantasy-point distributions on top of the v2 projections.

Each simulated game draws:
  * play/no-play (injury multiplier treated as the probability he plays; missed-latest-game x0.6 likewise)
  * snap share ~ Beta(mean = projected snap %, sd = player's own game-to-game snap % sd, shrunk to 0.08)
  * team defensive-snap volume ~ Gamma(mean 1, CV 0.12)
  * tackles ~ NegBin(mean = projected tackles x snap mult, size R_TKL); solo ~ Binomial(tackles, solo share)
  * QB hits ~ NegBin(size R_HIT) with mean set so sacks = Binomial(hits, sack-per-hit) match projected xSacks;
    each sack is a half sack with prob HALF_SACK; 93% of sacks also count as a TFL (2026 nflverse rate)
  * other TFL ~ Poisson(projected TFL - sack TFLs); INT ~ Poisson; PD = INT + Poisson(rest); FF ~ Poisson
  * FR, blocks ~ Poisson; defensive TD ~ Binomial(INT + FR, p) so return TDs ride on turnovers
All component means come from idp_ratings.project(), so the simulated mean equals the projection.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from idp_ratings import SCORING, P, score

SIM = dict(
    n=10000, seed=7,
    R_TKL=12.0,         # NegBin size for tackles given snaps (overdispersion); tuned in calibrate()
    R_HIT=1.5,          # NegBin size for QB hits (pass-rush games are streaky); grid-tuned wks 4-7 (insensitive)
    SNAP_SD_PRIOR=0.08, SNAP_SD_K=3,   # shrink game-to-game snap% sd toward 0.08 with 3 pseudo-games
    TEAM_SNAP_CV=0.12,  # team defensive snaps vary ~14% game to game (2026); part of that is already in snap sd
    HALF_SACK=0.22,     # share of sack credits that are half sacks (2026: 130 half-sack games / 476 sack games)
    SACK_TFL=0.93,      # share of sacks also credited as a TFL (2026 nflverse)
    OTHER_SPLIT=dict(fr=0.78, td=0.13, block=0.09),  # share of 'other' points by type, 2026 league-wide
    SPLASH_CV=0.6,      # Nov 3: per player-game Gamma(mean 1) shock shared by all big-play events (hot pass-rush /
                        # turnover-prone opponent game). Mean-preserving; fattens the 12+ tail. Tuned in boom_tune.py
)


def snap_sd(D: dict, week: int) -> pd.Series:
    s = D["snaps"]
    s = s[(s.week < week) & (s.defense_snaps > 0)].dropna(subset=["gsis_id"]).sort_values("week")
    s = s.groupby("gsis_id").tail(6)
    g = s.groupby("gsis_id").defense_pct.agg(["std", "count"])
    g["std"] = g["std"].fillna(SIM["SNAP_SD_PRIOR"])
    k, p0 = SIM["SNAP_SD_K"], SIM["SNAP_SD_PRIOR"]
    return np.sqrt((g["count"] * g["std"] ** 2 + k * p0 ** 2) / (g["count"] + k))


def _nb(rng, mean, size, shape):
    """NegBin via gamma-Poisson; mean array broadcast over sims (rows=players)."""
    lam = rng.gamma(size, 1.0 / size, shape) * mean
    return rng.poisson(lam)


def simulate(T: pd.DataFrame, D: dict, week: int, sims: dict | None = None, return_draws=False) -> pd.DataFrame:
    S = {**SIM, **(sims or {})}
    rng = np.random.default_rng(S["seed"])
    n, m = S["n"], len(T)
    sc = SCORING
    ps = score(D["ps"][D["ps"].week < week])
    sack_per_hit = ps.sacks.sum() / max(ps.qb_hits.sum(), 1)
    sack_val = 1 - 0.5 * S["HALF_SACK"]
    # solo share, shrunk to role average
    tot = (T.solo + T.ast)
    role_share = (T.groupby("role").solo.transform("sum") / T.groupby("role").apply(
        lambda g: (g.solo + g.ast).sum(), include_groups=False).reindex(T.role).values)
    solo_sh = ((T.solo + 20 * role_share) / (tot + 20)).clip(0.2, 0.95).to_numpy()

    # play probability = injury multiplier already applied to proj_pts
    p_play = (T.proj_pts / T.proj_raw.replace(0, np.nan)).fillna(1.0).clip(0, 1).to_numpy()
    mean_share = T.proj_snap_pct.clip(0.02, 0.995).to_numpy()
    sd = T.gsis_id.map(snap_sd(D, week)).fillna(S["SNAP_SD_PRIOR"]).to_numpy()
    sd = np.minimum(sd, np.sqrt(mean_share * (1 - mean_share)) * 0.95)
    conc = mean_share * (1 - mean_share) / sd ** 2 - 1
    a, b = mean_share * conc, (1 - mean_share) * conc
    shape = (m, n)
    share = rng.beta(a[:, None], b[:, None], shape)
    team_mult = rng.gamma(1 / S["TEAM_SNAP_CV"] ** 2, S["TEAM_SNAP_CV"] ** 2, (m, n))  # per player-game (no team pairing needed)
    snap_mult = share / mean_share[:, None] * team_mult
    plays = rng.random(shape) < p_play[:, None]
    snap_mult = snap_mult * plays

    col = lambda c: T[c].to_numpy()[:, None]
    cv = S["SPLASH_CV"]
    bp_mult = snap_mult * (rng.gamma(1 / cv ** 2, cv ** 2, shape) if cv > 0 else 1.0)   # big-play exposure
    # tackles
    tkl_pts_per = sc["solo_tackle"] * solo_sh + sc["assisted_tackle"] * (1 - solo_sh)
    lam_tkl = col("proj_tackle") / tkl_pts_per[:, None]
    tkl = _nb(rng, lam_tkl * snap_mult, S["R_TKL"], shape)
    solo = rng.binomial(tkl, solo_sh[:, None])
    ast = tkl - solo
    # sacks from QB hits
    e_sack_events = col("proj_sack") / sc["sack"] / sack_val
    hits = _nb(rng, e_sack_events / sack_per_hit * bp_mult, S["R_HIT"], shape)
    sack_ev = rng.binomial(hits, sack_per_hit)
    half = rng.binomial(sack_ev, S["HALF_SACK"])
    sacks = sack_ev - 0.5 * half
    sack_tfl = rng.binomial(sack_ev, S["SACK_TFL"])
    lam_tfl_other = np.maximum(col("proj_tfl") / sc["tackle_for_loss"] - S["SACK_TFL"] * e_sack_events, 0)
    tfl = sack_tfl + rng.poisson(lam_tfl_other * bp_mult)
    lam_int = col("proj_int") / sc["interception"]
    ints = rng.poisson(lam_int * bp_mult)
    pd_ = ints + rng.poisson(np.maximum(col("proj_pd") / sc["pass_defended"] - lam_int, 0) * bp_mult)
    ff = rng.poisson(col("proj_ff") / sc["forced_fumble"] * bp_mult)
    o = S["OTHER_SPLIT"]
    lam_fr = o["fr"] * col("proj_other") / sc["fumble_recovery"]
    fr = rng.poisson(lam_fr * bp_mult)
    blk = rng.poisson(o["block"] * col("proj_other") / sc["blocked_kick"] * snap_mult)
    p_td = np.clip(o["td"] * col("proj_other") / sc["defensive_td"] / np.maximum(lam_int + lam_fr, 1e-6), 0, 0.5)
    td = rng.binomial(ints + fr, np.broadcast_to(p_td, shape))
    pts = (solo * sc["solo_tackle"] + ast * sc["assisted_tackle"] + tfl * sc["tackle_for_loss"] + sacks * sc["sack"]
           + ints * sc["interception"] + pd_ * sc["pass_defended"] + ff * sc["forced_fumble"]
           + fr * sc["fumble_recovery"] + td * sc["defensive_td"] + blk * sc["blocked_kick"])
    out = pd.DataFrame({
        "gsis_id": T.gsis_id.values,
        "sim_mean": pts.mean(1), "sim_median": np.median(pts, 1),
        "floor_p10": np.percentile(pts, 10, axis=1), "p90": np.percentile(pts, 90, axis=1),
        "p_ge10": (pts >= 10).mean(1), "p_ge12": (pts >= 12).mean(1),
        "p_sack": (sacks > 0).mean(1), "p_takeaway": ((ints + ff) > 0).mean(1),
        "p_play": p_play,
    })
    return (out, pts) if return_draws else out


def calibrate(D: dict, weeks: list[int], sims: dict | None = None, verbose=True, n=4000):
    """Walk-forward: project + simulate week W from weeks < W; compare to actual league points."""
    import idp_ratings as M
    ps_all = score(D["ps"])
    rows = []
    for wk in weeks:
        T = M.project(D, wk)
        T = T[T.proj_snap_pct >= 0.5].copy()
        B = simulate(T, D, wk, {**(sims or {}), "n": n})
        g = T[["gsis_id", "pos", "proj_pts"]].merge(B, on="gsis_id")
        act = ps_all[ps_all.week == wk].set_index("player_id").fpts
        g["actual"] = g.gsis_id.map(act).fillna(0.0)
        g["week"] = wk
        rows.append(g)
    G = pd.concat(rows, ignore_index=True)
    eps = 1e-4
    res = {}
    for thr, col in [(10, "p_ge10"), (12, "p_ge12")]:
        y = (G.actual >= thr).astype(float)
        p = G[col].clip(eps, 1 - eps)
        base = G.groupby(["week", "pos"]).pos.transform("size") * 0 + y.groupby(G.pos).transform("mean")  # in-sample pos base rate
        res[f"brier_{thr}"] = ((p - y) ** 2).mean()
        res[f"brier_{thr}_posrate"] = ((base - y) ** 2).mean()
        res[f"logloss_{thr}"] = -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
        res[f"pred_rate_{thr}"] = p.mean()
        res[f"obs_rate_{thr}"] = y.mean()
    res["below_p10"] = (G.actual < G.floor_p10).mean()
    res["above_p90"] = (G.actual > G.p90).mean()
    res["n"] = len(G)
    if verbose:
        print("Calibration summary:", {k: round(v, 4) if isinstance(v, float) else v for k, v in res.items()})
        G["bin10"] = pd.cut(G.p_ge10, [0, .03, .06, .10, .15, .20, .30, 1.0], include_lowest=True)
        print("\nReliability P(>=10): predicted vs observed")
        print(G.groupby("bin10", observed=True).apply(lambda x: pd.Series(
            {"n": len(x), "pred": x.p_ge10.mean(), "obs": (x.actual >= 10).mean()}), include_groups=False).round(3))
        G["bin12"] = pd.cut(G.p_ge12, [0, .02, .04, .07, .10, .15, 1.0], include_lowest=True)
        print("\nReliability P(>=12): predicted vs observed")
        print(G.groupby("bin12", observed=True).apply(lambda x: pd.Series(
            {"n": len(x), "pred": x.p_ge12.mean(), "obs": (x.actual >= 12).mean()}), include_groups=False).round(3))
        print("\nBy position (pred vs obs rate of 10+):")
        print(G.groupby("pos").apply(lambda x: pd.Series({"pred10": x.p_ge10.mean(), "obs10": (x.actual >= 10).mean(),
              "pred12": x.p_ge12.mean(), "obs12": (x.actual >= 12).mean()}), include_groups=False).round(3))
        # ranking: does sorting by P90 / P(>=12) pick more boom games than sorting by mean?
        rk = []
        for (wk, pos), x in G.groupby(["week", "pos"]):
            for key in ["proj_pts", "p90", "p_ge12", "p_ge10"]:
                for k in (12, 24):
                    top = x.nlargest(k, key)
                    rk.append({"week": wk, "pos": pos, "rank_by": key, "top_k": k,
                               "games_10plus": (top.actual >= 10).sum(), "games_12plus": (top.actual >= 12).sum(),
                               "avg_pts": top.actual.mean()})
        for (wk,), x in G.groupby(["week"]):   # all positions together = D slot
            for key in ["proj_pts", "p90", "p_ge12", "p_ge10"]:
                top = x.nlargest(24, key)
                rk.append({"week": wk, "pos": "ALL", "rank_by": key, "top_k": 24,
                           "games_10plus": (top.actual >= 10).sum(), "games_12plus": (top.actual >= 12).sum(),
                           "avg_pts": top.actual.mean()})
        RK = pd.DataFrame(rk)
        print("\nBoom-pick test (sum over weeks of 10+/12+ games among top-k; avg actual pts):")
        print(RK.groupby(["pos", "top_k", "rank_by"])[["games_10plus", "games_12plus"]].sum().join(
            RK.groupby(["pos", "top_k", "rank_by"]).avg_pts.mean().round(2)).to_string())
        res["ranking"] = RK
    res["G"] = G
    return res
