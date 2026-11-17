# IDP streaming ratings (v2.1 + boom model)

Weekly DL / LB / DB projections and 0-100 ratings for Irene's Bush League (Yahoo 54162), built on 2026 nflverse data (`nflreadpy`).
v2 adds opponent offensive-line ratings, team-volume matchups by role, and a walk-forward backtest.

## Run
    ./run.sh                          # auto-detects season + first week with unplayed games
    ./run.sh --week 9                 # force a week
    ./run.sh --backtest 4-7           # walk-forward backtest (base vs v1 vs v2), writes backtest_weeks4-7.csv
    .venv/bin/python streamers.py --week 8   # (run.sh does this too) join to yahoo_league_week8.md
    .venv/bin/python calib_boom.py 4 5 6 7   # boom-model calibration backtest
    .venv/bin/python robust_compare.py 8     # v2.1 vs v2 projection changes -> robust_changes_week8.csv
Outputs: `ratings_week<N>.csv` (all players, incl. boom + consistency columns), `boom_week<N>.csv`, `ol_matchups_week<N>.csv`,
`streamers_week<N>.csv` (safe/boom lists), `streamers_boom_week<N>.csv`.
nflverse posts stats/snaps/pbp the night after games, so run Tue/Wed. Injury reports come in Wed-Fri; rerun Friday or Saturday.
For a new week, refresh the Yahoo available list into `yahoo_league_week<N>.md` in the same format, and update `STARTERS` in `streamers.py`.

## Scoring (`SCORING` at the top of `idp_ratings.py`)
Solo 0.75, assist 0.25, TFL 1.5, sack 3, INT 5, FF 5, FR 2, def TD 6, safety 3, PD 1, blocked kick 2.

## Model (v2)
1. **Roles**: EDGE, IDL, LB, CB, S. DL is IDL when ESPN depth lists DT/NT, otherwise EDGE. An LB counts as EDGE when the depth chart lists DE/OLB, or when he has a pass-rush profile (QB hits/snap >= 0.030 with tackles/snap < 0.11, or >= 0.015 with < 0.09). That rule catches Bailey, Watt, Van Ginkel, Turner, Tuipulotu and others; they get flagged `EDGE_LB`.
2. **Per-snap component rates** (tackle pts, TFL, sack, INT, PD, FF, other) use an exponential recency weight (0.8 per week) and are shrunk toward the role prior with pseudo-snaps (tackle 120, TFL/sack 300, PD 400, INT/FF 900, other 1500).
   **Sacks use expected sacks**: 40% realized sacks + 60% QB hits x league sacks-per-hit. QB hits are the more stable, leading indicator.
3. **Opponent offense profile** comes from 2026 play-by-play, recency weighted.
   - Sack rate per dropback, QB-hit rate, and run stuff rate (<= 0 yards) are **opponent-adjusted** with alternating ridge fits (rate = mu + offense + defense), so a line that faced strong rushes isn't penalized.
   - Pass-pro index `pr_idx` = 0.5 adj sack rate/mu + 0.5 adj hit rate/mu. Above 1 is easier for pass rushers.
   - OL personnel: each team's top 5 OL by snaps over its last 4 games. A starter counts as missing at 1.0 (IR/RES/Out/Doubtful), 0.8 (DNP last game with no report), 0.5 (cut), or 0.4 (Q / under 70% snaps / DNP practice). Each missing starter adds +5% to the pass-rush index (cap 3).
     OL snap rows have no pfr id in rosters, so they are joined by name + team.
   - Also tracked: plays/g, dropbacks/g, runs/g, WR/TE targets/g, QB INT rate (shrunk with 200 attempts), aDOT, fumbles/play, and tackle points allowed by role.
4. **Expected volume**: opponent dropbacks and runs are adjusted by the spread (pass script for the favorite's defense) and the total.
5. **Role factors** (alpha 0.8 of the raw deviation, clipped to 0.70-1.35):
   - EDGE/IDL: sack and TFL from OL pass-pro/run-block indexes x expected dropbacks.
   - LB: run volume, plays/g, and LB tackles allowed.
   - DB: pass attempts, WR/TE targets, QB INT rate, and aDOT.
6. **Snap share** = 50% last 3 games + 50% season. Projection = expected snaps x rate x factor, summed over components.
   Injury multipliers: Out 0, Doubtful 0.25, Q 0.85, DNP practice 0.85. A player who missed his team's latest game with no fresh report gets x0.6.
7. **Rating** = 100 x projection / best projection, within position and overall.
8. **One-big-game robustness (v2.1, `P["robust"]`)**: tackle opportunity (snaps x tackles/snap) is never capped. Rare big plays are:
   - capped per game before entering the rates: 2 sacks, 1 INT, 1 FF, and a return TD counts like a fumble recovery (2 pts);
   - for INT/FF/other, the player's single best game gets half weight (needs >= 3 games);
   - INT/FF/other shrinkage doubled (`splash_k_mult` 2.0).
   The league-level loss from the caps is added back per role, so averages don't move; only one-off outliers drop.
   Consistency columns: `median_ppg`, `games_ge6` (games >= 6 pts / games played), `cv_pts`, `ppg_ex_best`, `best_game_pts`, `best_game_share`.

## Backtest (walk-forward; week W uses only weeks < W; actual = league points, 0 if DNP)
Pool: players with projected snap share >= 50%. `base` = season ppg to date (about what Yahoo's default ranking shows).

| metric (mean of wks 4-7) | base | v1 | v2 |
|---|---|---|---|
| Spearman, all | 0.219 | 0.255 | **0.262** |
| top-24 hit rate | 0.326 | 0.323 | **0.351** |
| top-24 avg actual pts | 4.81 | 4.92 | **5.04** |
| MAE | 2.87 | 2.69 | **2.64** |

By position (Spearman / top-24 hit): DB 0.241/0.219 base, 0.272/0.250 v1, **0.283/0.292** v2. LB 0.253/0.344, 0.281/0.312, **0.322/0.344**. DL 0.161/0.417, **0.212**/0.406, 0.180/**0.417**.
DL is v2's weak spot: it beats base but not v1 on Spearman. Full rows are in `backtest_weeks4-7.csv`.

Tuning (`tune.py`, `tune2.py`, results in `tune_results*.csv`) changed one parameter at a time and kept only changes that were consistent across positions:
- opp_alpha 0.6 -> 0.8. Turning matchups off (alpha 0) gives Spearman 0.246; the matchup layer helps every position.
- snap_recent_w 0.65 -> 0.5.
Everything else stayed at the priors. Differences under ~0.01 are noise with only 4 weeks.

### v2.1 robustness backtest (`tune_robust.py`, `tune_results_robust*.csv`)
| wks 4-7 | Spearman | top-24 hit | top-24 avg pts | top-24 share >= 6 | MAE | DL Spearman |
|---|---|---|---|---|---|---|
| v2 | 0.2617 | 0.351 | 5.04 | 0.340 | 2.642 | 0.180 |
| caps only | 0.2621 | 0.354 | 5.06 | 0.340 | 2.641 | 0.180 |
| **v2.1** (caps + best-game 0.5 on INT/FF/other + k x2) | **0.2626** | **0.361** | **5.11** | **0.347** | **2.639** | 0.178 |
| best-game 0.5 on all splash incl. sacks | 0.259 | 0.365 | 5.12 | 0.351 | 2.640 | 0.163 |
Small but consistent gains. Downweighting best *sack* games hurt DL (pass rushers' big games carry signal), so sacks are only capped; they are already stabilized by QB hits.
Using historical median or games >= 6 inside the ranking score did **not** help (top-24 avg pts 5.11 by mean vs 5.05 with 30% median weight, 5.02 with a games >= 6 bonus). So the safe list keeps the mean and uses consistency as the tiebreak.

## Boom model (`boom.py`, columns in ratings_week<N>.csv and `boom_week<N>.csv`)
A Monte Carlo (10,000 games per player) on the same component projections, so the simulated mean equals `proj_pts` (mean abs diff 0.02).
- Play probability = injury multiplier.
- Snap share ~ Beta around the projected snap %, with the player's own game-to-game sd shrunk to 0.08. Team snap volume ~ Gamma, CV 0.12.
- Tackles ~ NegBin (size 12), split into solo/assist by the shrunk solo share.
- QB hits ~ NegBin (size 1.5). Sacks ~ Binomial(hits, league sacks/hit), 22% of them half sacks, 93% also a TFL. Extra TFLs ~ Poisson.
- INT ~ Poisson; PD = INT + Poisson; FF, FR, and blocks ~ Poisson; return TD ~ Binomial(INT + FR).
- Outputs: `sim_mean`, `sim_median`, `floor_p10`, `p90`, `p_ge10`, `p_ge12`, `p_sack`, `p_takeaway`.
Dispersion was grid-tuned on wks 4-7 (`calib_grid.py`); results are insensitive to it.

Calibration, walk-forward wks 4-7 (`calib_boom.py`, `backtest_boom_weeks4-7.txt`), 1,284 player-games:
- Rates: predicted P(>=10) 7.5% vs observed 7.1%; P(>=12) 3.8% vs 4.0%. Actuals fell below P10 8.5% of the time and above P90 9.0%.
- Reliability: about right from 3% to 30%, overconfident at the tails. Under 3% predicted, 4% observed; 10-15% predicted, 9% observed.
- P(>=10) has some skill: AUC 0.64 (mean projection 0.63). Leave-one-week-out log loss 0.2516 beats a position base rate at 0.2568.
- P(>=12) is too rare to beat a position base rate out of sample (log loss 0.172 vs 0.167; only 51 12+ games).
- Boom-pick test, top-24 overall per week, summed over wks 4-7:

  | Ranked by | 10+ games | 12+ games |
  |---|---|---|
  | P(>=10) | 22 | 9 |
  | P90 | 21 | 10 |
  | mean | 18 | 8 |

  DL top-24: 7 by P(>=10) vs 5 by mean. LB top-12: mean does as well or better.
- Bottom line: boom ranking finds a few more 10+ games, mostly by promoting edges and volatile players, at a small cost in average points.

## Streamers (`streamers.py`)
- Joins ratings to Yahoo's available list by normalized name + team (LAR->LA, Jr/II stripped, initial fallback). Yahoo positions are used as given.
- LB slot = Yahoo positions containing LB. D slot = anyone.
- Shows W (waivers until Oct 31) vs FA.
- When the model has no injury report yet, it applies Yahoo's tag: Q x0.85, D x0.25, IR/SUSP 0. Bailey (Q) is compared at his tagged projection.
- Bye-week players (HOU, NO, NYG, SF) are unmatched by design.
- Re-runs the Monte Carlo for the listed players with Yahoo tags applied, so a Q player's floor and boom odds include the DNP risk.
- Two lists per slot, 15 each, plus a `starter` row: `list_type` = safe / boom / starter.
  - **safe**: mean rounded to 0.25, then floor (P10), then median weekly pts.
  - **boom**: P(>=10), then P90, then P(>=12).
  LB-eligible edges (LB,DE) are in both slots; DL/DE are in the D slot.
- Outputs: `streamers_week<N>.csv` (all columns) and `streamers_boom_week<N>.csv` (boom summary).
- `run.sh` runs ratings + boom, then streamers when `yahoo_league_week<N>.md` exists.

## Limitations
- Only 7 weeks of 2026 data. OL and defense ratings are noisy, which is why they are shrunk.
- No pressures or pass-rush win rate in nflverse; QB hits are the best proxy.
- Week 8 injury reports cover only CAR/GB so far, so the OL "missing" values mostly come from week-7 snaps and roster status. Rerun Friday.
- Yahoo's available list is its top 50 per position, so deeper options aren't evaluated.
- TDs, safeties, and blocks are not projectable; they enter only through shrunk history.
- The boom model treats a player's events as independent given snaps; it does not model a defense-wide blowout or garbage-time spike. Its tails are slightly overconfident (see calibration).

## Offense model (offense.py) - added week 8
- QB/RB/WR/TE/K. Team volume (plays, pass rate) x shrunk, recency-weighted player shares (targets, carries, RZ, inside-10), efficiency priors (aDOT-adjusted yards/target, ypc, catch rate), defense factors (opponent allowed vs league), Vegas implied totals (fallback: avg of offense ppg and defense ppg allowed). Monte Carlo gives floor (P10), median, P90, P(boom): QB 25+, RB/WR 20+, TE 15+, K 12+.
- Matchup grade = projection / neutral-opponent projection: F <0.90, D <0.95, C- <0.985, C <1.015, B <1.05, A <1.10, A+ above. IDP grade uses opp_fpa_idx with the same bins.
- Scoring = real league scoring from yahoo_offense_available_week8.md (Pass 20 yd/pt +5@375, TD 4, INT -1; Rush/Rec 10 yd/pt, TD 6, 0.5 PPR, +5@180 rush/+5@200 rec; FL -2; K PAT +1/-1, 0.1 pt per made-FG yard, missed FG 0-29 -1).
- Backtest: `offense.py --backtest 4-7` -> backtest_offense_weeks4-7.csv/txt and backtest_offense_latest.txt. Weeks 4-7 Spearman: model .537 vs season-avg .358 (injury-adjusted avg .490). K model is weak (.157 vs .201).

## Weekly lineup, waivers, dashboard (fantasy.py)
- Inputs: roster.json (your roster, slots, FAAB, forced IDP starters), yahoo_offense_available_weekN.md, yahoo_league_weekN.md.
- Outputs: offense_weekN.csv, lineup_weekN.csv (safe = max mean, boom = max P90), waivers_weekN.csv (ROS ppg weeks N-17 with byes/schedule, week value, gain over your weakest starter, FAAB % range of budget), dashboard_data_weekN.json.
- FAAB tiers by ROS ppg gain: >=3 20-30%, >=1.5 10-20%, >=0.5 4-10%, >0 1-4%, else $0-1; x1.25 if >=60% rostered. FA players are free adds.
- Page: "Fantasy Week 8 Rankings" (canvas 1ef81067-034a-4b9a-b69e-b27a311688f3). run.sh builds page/page_weekN.tsx (page/head.tsx + make_page_data.py output + page/body.tsx); ask Grok Bot to rewrite the Page from that file each week.
- Weekly: refresh the two Yahoo md files and roster.json, then `./run.sh --week N`.

## Oct 28 usage audit (Washington vs Shakir)
Changes in offense.py (backup: offense_pre_audit.py):
- Vacated targets: target and red-zone target shares now discount games where core teammates (season target share >= 5% and active in the team's latest game) were absent. tgt_adj = tgt * (1 - absent_share), with absent_share capped at 0.5.
- WR/TE rush TDs are now carries * position rush-TD-per-carry rate (P["wr_rush_td"]="rate") instead of an inside-10 share.
- Yards-per-target prior: aDOT weight is now P["adot_w"]=0.15, and the prior is scaled by the team's shrunk pass yds/att ratio ^ P["qb_w"]=1.0, so QB efficiency counts.
Changes in fantasy.py: a 0-0.5 ppg ROS gain is labeled "toss-up (within model error)" with FAAB "$0-1 (depth only)".
Backtest wks 4-7, all positions (before -> after): Spearman .537 -> .539, MAE 4.665 -> 4.646, hit .576 -> .563; WR Spearman .627 -> .632, WR MAE 4.368 -> 4.270.
Audit scripts: audit_wr.py, audit2.py, audit3.py, audit4.py, audit_bt.py, audit_bt2.py. Pre-audit outputs are saved as *_pre_audit.*

## Trade finder (`trade_finder.py`)
`python trade_finder.py --week N [--team 4] [--all-pairs 1] [--selftest]` (run.sh calls it automatically when `league_rosters_weekN.json` exists).
Scores trades by change in each team's rest-of-season optimal starting lineup (weeks N-17, playoff weeks 15-17 weighted by playoff odds), with FA streaming, a small depth term, roster drop/add, and Yahoo injury tags.

Streaming value: a free agent fills a slot at `CFG['stream']` (0.85) of his projection, except tight ends at `CFG['stream_pos']['TE']` (0.60, override with env `TF_STREAM_TE`). Calibrated on 2026 weeks 2-7: top-projected FA TEs scored 45-63% of projection vs 84-90% for QB/RB/WR, so the old flat 0.85 understated elite-TE scarcity.
Keeps trades where both sides gain, smaller gain >= 40% of larger and >= 3 weighted points. Writes `trades_weekN.csv` and `page_trades_weekN.txt` (spliced into the Page).
Acceptance flag uses FantasyCalc redraft values + FantasyPros ROS ECR (offense and IDP), cached in `consensus/`.

### WR2 preset (`wr2_finder.py`, Oct 28)
`TF_DEV=1 .venv/bin/python wr2_finder.py --week 8 [--lock "Brock Bowers,CeeDee Lamb"] [--soft "Hunter Henry"] [--min-wr 9.5]`
uses the same engine, balance rule (smaller gain >= 40% of the larger and >= 3) and market check as `trade_finder.py`, but only for team 4. The rules:
- Locked players never go out.
- A trade that sends a soft-locked player out is flagged (`henry_flag`).
- You must receive a WR with a non-bye ROS average of at least max(9.5, your WR2 + 1).
- The WR slots must be your largest positive lineup change and at least 50% of the positive change.

Outputs:
- `trades_week8_wr2.csv`: all rows, with `shortlist` = one row per package received, as shown on the Page.
- Rows tagged `preset=wr2_no_bowers`, merged into `trades_week8.csv`. Rerun this script after `trade_finder.py`, because that script rewrites the CSV.

`wr_usage_check.py` writes `wr_usage_week8.csv` with snap %, targets per game, target share, air yards and ppg for the season and the last 3 games. It covers the trade-target WRs and the top 14 free-agent WRs.

## Lesson: big-play audit (Nov 3, 2026)
Complaint: "not valuing sacks/turnovers, just pushing tackle volume."
- Level bias was NOT the problem (wks 4-8, snap>=50%: big-play proj vs actual DB 1.61/1.56, DL 2.24/2.14, LB 2.04/2.01).
- The problem was the single total-points CAL: it shrank DL/EDGE big-play spread (calibrated slope 1.17; raw model was already ~0.99). Top-quintile DL projected 3.15 vs 3.47 actual (~25% under on the spread).
- LB/DB big plays are mostly noise (slopes 0.47/0.54; INT corr ~0). Shrink them; don't chase them.
- Matchup factors: sack factor works (top quartile 1.26x actual vs 0.81x bottom); INT factor no signal; FF weak. All kept.
- Shrinkage/cap tweaks (k_sack, k_tfl, sack cap, k_int) moved MAE by ~0.01. They don't matter.
- Fix: `CAL_MODE="split"`, `CAL_SPLIT` in idp_ratings.py (separate tackle/big (a,b) per DL/LB/DB; "total" reverts). boom.py `SIM["SPLASH_CV"]=0.6` Gamma shock on per-game big plays.
- Backtest wks 4-8 total->split: MAE 2.592->2.580; big slope DB/DL/LB 0.54/1.17/0.47 -> 0.76/0.99/0.74; Spearman flat. P(12+) overall 3.3%->3.85% pred vs 4.05% obs; boom list 9.3% pred/13.3% obs -> 10.0%/10.0%; log loss 0.1686->0.1667. LB 12+ is still a bit under (5.8% vs 7.3%). The CAL was fit in-sample, and list hit differences are within noise.
- Scripts: comp_audit.py, ca2.py, comp_exp*.py, comp_bt.py, boom_tune.py. Pre-change backups: *_pre_bigplay.*

## Lesson: matchup + full IDP audit (Nov 3, 2026) - `idp_audit.py`, output `idp_audit_weeks4-8.txt`
Complaint: the matchup score leaned on volume, and re-percentiling handed the top team an automatic 100 (CHI 100 vs TB, raw 84.4 vs 83.6).
- Walk-forward weeks 4-8 (1,511 player-games). Residual = actual minus the player's shrunk prior average. Matchup factors are weak: the best single factors have r 0.05-0.08 (DL QB-hit rate, DB giveaways, LB rushes). Free multi-factor fits lose to "no matchup" out of sample. The old score's r was 0.03-0.07.
- New matchup (`matchup_view.py`, backup `matchup_view_pre_audit.py`):
  - A fixed big-play-first index (weights `IDX` in `audit_final.pkl`) on shrunk offense rates: 150 dropbacks for rates, 300 for INT rate, 3 games for per-game and allowed stats.
  - One scale per group, fit walk-forward. The output is expected pts vs average, about +-0.3. Grades: A >= +0.15, B >= +0.05, C within 0.05, D <= -0.05, F <= -0.15.
  - Only the DB scale shows an out-of-sample gain.
- A past 12+ rate does not predict the next 12+ game (AUC 0.48). QB hits x snaps does (AUC 0.60 overall, 0.69 for DL). Use P(12+) from the boom model for ceiling, not 12+ counts.
- Tackle opportunity is stable: snap blends tie at r ~.53. Recency 0.8 is best (0.6 is worse). Caps plus shrinkage help DL big plays. LB/DB turnovers are unpredictable.
- EDGE-flagged LBs have the highest 12+ rate (9.2%). LB-eligible edges are the ceiling pool for the LB slot.
- Lesson: never re-percentile a weak signal to 0-100. Report it in points, so the spread shows how little it matters.
