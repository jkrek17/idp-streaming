"""Walk-forward calibration of the boom model (weeks given on argv, default 4-7)."""
import sys, warnings; warnings.filterwarnings("ignore")
import numpy as np, idp_ratings as M, boom
weeks = [int(x) for x in sys.argv[1:]] or [4, 5, 6, 7]
D = M.load_data(2026)
r = boom.calibrate(D, weeks, n=10000)
G = r["G"]
for thr, c in [(10, "p_ge10"), (12, "p_ge12")]:
    y = (G.actual >= thr).astype(float); p = G[c].clip(1e-4, 1 - 1e-4)
    for name, q in [("sim", p), ("pos base rate (in-sample)", y.groupby(G.pos).transform("mean"))]:
        print(thr, name, "brier", round(((q - y) ** 2).mean(), 4), "logloss", round(-(y * np.log(q) + (1 - y) * np.log(1 - q)).mean(), 4))
    pos, neg = p[y == 1].values, p[y == 0].values
    auc = (pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()
    a, b = G.proj_pts[y == 1].values, G.proj_pts[y == 0].values
    auc_m = (a[:, None] > b[None, :]).mean() + 0.5 * (a[:, None] == b[None, :]).mean()
    print(thr, "AUC sim prob", round(auc, 3), "AUC by mean proj", round(auc_m, 3))
tag = f"weeks{weeks[0]}-{weeks[-1]}"
r["ranking"].to_csv(f"backtest_boom_ranking_{tag}.csv", index=False)
G.to_csv(f"backtest_boom_{tag}.csv", index=False)
