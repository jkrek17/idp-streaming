"""Week-N projection with v2.1 robustness on vs off; lists the biggest demotions (one-big-game players)."""
import sys, warnings; warnings.filterwarnings("ignore")
import pandas as pd, idp_ratings as M
week = int(sys.argv[1]) if len(sys.argv) > 1 else 8
D = M.load_data(2026)
new = M.project(D, week)
M.P["robust"] = False
old = M.project(D, week).set_index("gsis_id")
M.P["robust"] = True
C = new[["gsis_id", "player", "team", "pos", "role", "proj_pts", "season_ppg", "median_ppg", "games_ge6", "cv_pts",
         "ppg_ex_best", "best_game_pts", "best_game_share", "proj_snap_pct"]].copy()
C["proj_old_v2"] = C.gsis_id.map(old.proj_pts)
C["delta"] = (C.proj_pts - C.proj_old_v2).round(2)
C["rank_old"] = C.proj_old_v2.rank(ascending=False, method="first").astype(int)
C["rank_new"] = C.proj_pts.rank(ascending=False, method="first").astype(int)
C = C.sort_values("delta")
C.to_csv(f"robust_changes_week{week}.csv", index=False)
pd.set_option("display.width", 250)
print(C[C.proj_snap_pct >= 0.4].head(15).round(2).to_string(index=False))
print(C[C.player.str.contains("Josiah Trotter")].round(2).to_string(index=False))
