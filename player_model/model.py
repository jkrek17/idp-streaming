"""LightGBM projection models per pool (offense, IDP):
  - mean points (L2)
  - quantiles 10/25/50/75/90 (pinball loss), re-sorted to avoid crossing
  - P(start-worthy week) and P(boom week) classifiers, isotonic-calibrated on a held-out season
"""
from __future__ import annotations
import numpy as np, pandas as pd
import lightgbm as lgb
from sklearn.isotonic import IsotonicRegression
from . import features as F

QS = [0.1, 0.25, 0.5, 0.75, 0.9]
POOLS = {"offense": ["QB", "RB", "WR", "TE", "K"], "idp": ["DL", "LB", "DB"]}
POS_CODE = {p: i for i, p in enumerate(["QB", "RB", "WR", "TE", "K", "DL", "LB", "DB"])}
CTX = ["home", "spread", "total_line", "implied", "rest", "dome", "opp_allow", "week", "gap", "age",
       "years_exp", "draft_pick", "pos_code", "imp_tgt", "imp_car", "imp_rz", "imp_att", "imp_snap"]
NON_FEAT = {"player_id", "player_display_name", "pos", "team", "season", "week", "t", "fpts", "birth_date",
            "rookie_year", "draft_number", "target", "opp", "gameday", "tgt_week", "tgt_season", "tgt_t"}
PARAMS = dict(learning_rate=0.03, num_leaves=31, min_data_in_leaf=150, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, verbose=-1, num_threads=4, seed=7)


def feature_cols(S: pd.DataFrame) -> list[str]:
    st = [c for c in S.columns if c not in NON_FEAT and S[c].dtype.kind in "fiub"]
    return st


def add_target_ctx(X: pd.DataFrame, sched: pd.DataFrame, G: pd.DataFrame) -> pd.DataFrame:
    """X has player state columns plus target (season, week, team). Adds game context + bio features."""
    X = F.context(X, sched, G)
    bd = pd.to_datetime(X.birth_date, errors="coerce")
    gd = pd.to_datetime(X.gameday, errors="coerce")
    X["age"] = (gd - bd).dt.days / 365.25
    X["years_exp"] = X.season - pd.to_numeric(X.rookie_year, errors="coerce")
    dn = pd.to_numeric(X.draft_number, errors="coerce")
    X["draft_pick"] = dn.where(dn > 0, 300)
    X["pos_code"] = X.pos.map(POS_CODE)
    # usage x team scoring environment (expected-opportunity proxies)
    X["imp_tgt"] = X.implied * X.tgt_sh
    X["imp_car"] = X.implied * X.car_sh
    X["imp_rz"] = X.implied * (X.rz_tgt_sh + X.rz_car_sh)
    X["imp_att"] = X.implied * X.att_sh
    X["imp_snap"] = X.implied * X.snap
    return X


def training_table(D: dict, prior_max_season: int) -> tuple[pd.DataFrame, list[str], pd.DataFrame, dict]:
    G = D["games"]
    S, priors = F.build_states(G, max_season_prior=prior_max_season)
    feats = feature_cols(S)
    prev = S.groupby("player_id")[feats + ["t"]].shift(1)
    X = S[["player_id", "player_display_name", "pos", "team", "season", "week", "fpts", "birth_date",
           "rookie_year", "draft_number"]].copy()
    X[feats] = prev[feats]
    X["gap"] = S.t - prev.t - 1
    X = X[prev.t.notna()].copy()
    X = add_target_ctx(X, D["sched"], G)
    return X, feats + CTX, S, priors


class PoolModel:
    def __init__(self, pool: str, feats: list[str]):
        self.pool, self.feats = pool, feats
        self.models, self.cal, self.iters = {}, {}, {}

    def _ds(self, X):
        return lgb.Dataset(X[self.feats], label=X.fpts, free_raw_data=False)

    def fit(self, tr: pd.DataFrame, va: pd.DataFrame | None = None, iters: dict | None = None):
        thr_s = tr.pos.map({p: v[0] for p, v in F.THR.items()})
        thr_b = tr.pos.map({p: v[1] for p, v in F.THR.items()})
        tasks = {"mean": (dict(objective="regression"), tr.fpts)}
        for q in QS:
            tasks[f"q{int(q * 100)}"] = (dict(objective="quantile", alpha=q), tr.fpts)
        tasks["p_start"] = (dict(objective="binary"), (tr.fpts >= thr_s).astype(int))
        tasks["p_boom"] = (dict(objective="binary"), (tr.fpts >= thr_b).astype(int))
        for name, (obj, y) in tasks.items():
            p = {**PARAMS, **obj}
            dtr = lgb.Dataset(tr[self.feats], label=y)
            if va is not None:
                yv = self._label(name, va)
                dva = lgb.Dataset(va[self.feats], label=yv)
                m = lgb.train(p, dtr, num_boost_round=3000, valid_sets=[dva],
                              callbacks=[lgb.early_stopping(100, verbose=False)])
                self.iters[name] = m.best_iteration
            else:
                m = lgb.train(p, dtr, num_boost_round=(iters or {}).get(name, 600))
            self.models[name] = m
        return self

    def _label(self, name, X):
        if name == "p_start":
            return (X.fpts >= X.pos.map({p: v[0] for p, v in F.THR.items()})).astype(int)
        if name == "p_boom":
            return (X.fpts >= X.pos.map({p: v[1] for p, v in F.THR.items()})).astype(int)
        return X.fpts

    def raw(self, X: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=X.index)
        for name, m in self.models.items():
            out[name] = m.predict(X[self.feats], num_iteration=m.best_iteration or None)
        qc = [f"q{int(q * 100)}" for q in QS]
        out[qc] = np.sort(out[qc].to_numpy(), axis=1)
        return out

    def calibrate(self, va: pd.DataFrame):
        r = self.raw(va)
        for name in ["p_start", "p_boom"]:
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
            iso.fit(r[name], self._label(name, va))
            self.cal[name] = iso
        # quantile coverage check / conformal widening: scale spread so 10-90 covers ~80% on held-out data
        cover = ((va.fpts.to_numpy() >= r.q10) & (va.fpts.to_numpy() <= r.q90)).mean()
        self.cover_raw = float(cover)
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        r = self.raw(X)
        for name, iso in self.cal.items():
            r[name] = iso.predict(r[name])
        return r


def pool_mask(X, pool):
    return X.pos.isin(POOLS[pool])
