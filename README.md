# IDP streaming ratings (v3 threshold model + v2.1 + boom model)

## v3: P(6+) and P(12+) threshold model (`idp_threshold.py`), added Nov 17
The streamer lists now rank by the chance a player clears **6 points** (safe list) or **12 points** (boom list),
from a model trained on **2018-2026** nflverse data instead of one season.

    .venv/bin/python idp_threshold.py --refresh --week 11   # refresh this season's data, write threshold_week11.csv
    .venv/bin/python idp_threshold.py --backtest            # walk-forward backtest -> threshold_backtest.txt
`run.sh` runs it after `idp_ratings.py`; `streamers.py` reads `threshold_week<N>.csv` (falls back to v2 ordering without it).
Data is cached in `cache/` (gitignored, ~95 MB); the first run downloads everything (~40 s), later `--refresh` runs
only re-pull the current season.

**Model.** One row per defender-game (REG season, about 93,000 since 2018). Every feature uses only earlier games:
- Player history, exponentially weighted over his past games across seasons (half-lives 3 and 10 games): points,
  tackle points, big-play points, solo/assist tackles, TFL, sacks, QB hits, PFR pressures / hurries / blitzes /
  targets / missed tackles, share of team tackles, snap %, past 6+ and 12+ rates; per-snap rates (half-life 6);
  last game snap %, snap trend, prior-season ppg / snap % / pressures, games this season and career, missed games.
- Game context: opponent offense (plays, dropbacks, runs, sack / hit / INT / fumble rates, IDP points and tackles it
  allows to this position group), own defense plays faced, Vegas spread and total, opponent implied total, home/away.
- Home stat crew: tackles and assists credited per play in games at that stadium vs league (crews range from about 4% below to 7% above average).
- Pre-game injury report: own questionable / practice status, and snap share vacated by Out/Doubtful teammates.
- Gradient-boosted trees (scikit-learn), shallow and heavily regularized, for P(6+ | plays), P(12+ | plays) and
  expected points. Then x play probability from history: Out 0, Doubtful 0.8%, Questionable 63%, DNP practice with no
  status 77%, on report otherwise 91%, not on report 97.7%, missed last game with no report 58%; IR / cut / practice
  squad / off his team's latest roster 0. Yahoo tags stand in when there is no NFL report yet (`streamers.TAG_PLAY`).
- Leak check: rebuilding features with all later games deleted gives identical values for the cutoff week.

**Backtest** (`threshold_backtest.txt`; each season trained only on earlier seasons, 2026 refit every week; pool =
starters with recent snap share >= 50%; "ppg" = EW points per game, roughly what a manager sorts by):

| season | 6+ base | 6+ AUC within pos (v3 / ppg) | 6+ top-10 hit (v3 / ppg) | 12+ base | 12+ AUC (v3 / ppg) | 12+ top-10 hit (v3 / ppg) |
|---|---|---|---|---|---|---|
| 2023 | 25.6% | 0.639 / 0.620 | 52.8% / 46.7% | 4.6% | 0.664 / 0.649 | 15.0% / 11.7% |
| 2024 | 24.4% | 0.645 / 0.620 | 47.8% / 36.1% | 4.3% | 0.651 / 0.626 | 17.8% / 8.9% |
| 2025 | 23.3% | 0.641 / 0.614 | 48.9% / 46.1% | 3.9% | 0.681 / 0.675 | 10.6% / 10.6% |
| 2026 wk 2-10 | 24.4% | 0.636 / 0.623 | 46.7% / 42.2% | 4.2% | 0.656 / 0.666 | 12.2% / 7.8% |

- Calibrated: by decile, predicted vs observed P(6+) is within 1 point everywhere (0.448 -> 0.457 in the top
  decile), and P(12+) within 0.6 points (0.112 -> 0.113). Calibration holds by position too.
- Waiver tier (outside each week's top 24 LB / 24 DL / 36 DB by ppg): the top 5 picks per week hit 6+ 47% of the
  time (base 21%, ppg 39%) and 12+ 9.8% (base 3.3%, ppg 6.3%).
- vs v2 on 2026 weeks 4-10 (2,057 player-games): AUC within position 0.640 vs 0.613 for 6+ and 0.665 vs 0.580 for
  12+; 12+ log loss 0.1730 vs 0.1785. v2's top 10 hit 6+ more often (52.9% vs 47.1%, 4 picks over 7 weeks, inside
  noise); from the top 20 down v3 is ahead. The v2 mean stays in the lists as a tiebreak and reference column.
- What did not help (2023-2025 holdouts): bigger trees (AUC -0.005), LightGBM (same as scikit-learn), monotone
  constraints, a slower learning rate, per-position logistic regression (-0.003), the injury features (neutral, kept
  because they matter for snaps live), and blending in the v2 mean (helped 6+ by 0.003 in 2026, hurt 12+).
- Ceiling: weekly IDP points are noisy. Within-position AUC of ~0.64 (6+) and ~0.66 (12+) is about what box-score and
  snap data support; the remaining gains are in snap-share news (injuries, depth changes) that arrives late in the week,
  so **rerun Friday or Saturday** after injury reports.

---

# v2.1 model and boom model (still used for the mean projection, matchup notes and the dashboard)

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
- **Since v3:** safe = P(6+) from `threshold_week<N>.csv` (tiebreak v2 mean), boom = P(12+) (tiebreak v2 P(10+)).
  Columns `v3_p_ge6`, `v3_p_ge12`, `v3_x_pts`, `v3_p_play`, plus the starter's v3 odds. The bullets below describe the v2 fallback.
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

## Player ranking and value model (`player_model/`) - added Nov 17, 2026
Ranks and values every offensive and IDP player for this league, with a consistency-to-ceiling switch.
Offense (QB/RB/WR/TE/K) and IDP (DL/LB/DB) are separate pools. Each has position ranks plus a whole-pool ranking
(W/R/T flex for offense, D slot for IDP, plus an LB-slot view). Horizons: this week, rest of season (weeks W-17), and playoffs (15-17).

    .venv/bin/python -m player_model.run [--week N]     # ~2 min; writes player_values_week<N>.csv/.json and player_values.html
    .venv/bin/python -m player_model.backtest           # season-held-out backtest -> player_model_backtest.txt/.csv
`run.sh` calls it last. Data is cached in `data_cache/` (gitignored); the current season refreshes each run.

**Data.** nflverse 2018-2026 player stats, snap counts, play-by-play (red-zone usage, team plays/dropbacks/rushes), schedules
(Vegas lines), injuries and weekly rosters. Zero-stat games (on the field, no stat) are added from snap counts so floors are honest.
**Features** (`features.py`), each built only from earlier games:
- Usage: snap share, target share, carry share, red-zone target/carry shares, air-yards share, pass-attempt share; IDP snap share,
  tackles per opponent play, solo share, and sack / QB-hit / TFL / PD / INT / FF rates per snap; K attempts and FG yards per game.
- Every rate is a recency-decayed sum (8-week and 3-week half-lives on a season*30+week clock, so last season counts about 1/3)
  shrunk toward the position mean by empirical Bayes. The prior strength k is fit by method of moments from player-season
  spreads (beta-binomial for shares, gamma-Poisson for per-snap rates), so noisy stats (INT, sacks) shrink hard and snap share barely.
- Consistency over the last 16 games: sd, CV, 20th/80th percentile games, max, and shrunk start / boom / bust rates.
- Context: implied team total, spread, total, home, rest, dome, opponent points allowed to the position (decayed), age,
  experience, draft slot, weeks since last game, and usage x implied-total interactions.
**Models** (`model.py`): LightGBM per pool. Mean (L2), quantiles 10/25/50/75/90 (pinball loss, sorted to avoid crossing), and
P(start-worthy) / P(boom) classifiers with isotonic calibration on a held-out season. Thresholds (start / boom):
QB 17/25, RB 10/20, WR 10/20, TE 7/15, K 8/13, DL / LB / DB 6/12 (the league's IDP lines, same as idp_threshold.py).
Production fit: model A trains 2019 to last-2 seasons and early-stops/calibrates on last season; model B refits through the last
completed week with A's iterations x1.15 and A's calibrators.
**Availability**: injury report, Yahoo tag, NFL roster status (IR = out 4 weeks then 50%), and missed-last-game (0.6). It mixes a
chance of 0 into the mean and quantiles; short-term injuries heal at 50% per week in the ROS sums.
**One IDP model for the coming week** (Nov 17): when `threshold_week<N>.csv` exists, week-N IDP numbers on the board
(P(6+), P(12+), expected points, play probability) come from the threshold model, and this model's quantiles are shifted to
its mean, so the board and the streamer lists always agree. Head-to-head at 6+/12+ on 2023-2026 (each season out of sample),
AUC within position: threshold model 0.643 / 0.666, this model 0.641 / 0.660 (threshold model ahead in 2023-2025, behind
in 2026); a stacked blend of the two added only ~0.003. Rest-of-season and playoff sums still come from this model.
If `offense_week<N>.csv` exists, this week's offense projections are blended 50/50 with offense.py (backtest weeks 4-8:
Spearman 0.399/0.396 alone -> 0.421 blended, MAE 4.88 -> 4.80).
**Value** (`value.py`, live in the page): mode score = mean pulled toward the 25th pct (consistency) or 90th pct (ceiling),
`lam` in [-1, 1]; ROS = sum of weekly scores. Value = score minus the average of the 3 best unrostered players at the position
(from `league_rosters_week<N>.json`; falls back to the 13th-15th best if no roster file). Tiers break on large score gaps.

**Backtest** (train 2019-2024, calibrate 2025, test 2026 weeks 3-10, never trained on; players with a real role; mean over weeks):

| Spearman | model | decayed ppg | season ppg |
|---|---|---|---|
| QB | **0.50** | 0.46 | 0.36 |
| RB | **0.50** | 0.48 | 0.36 |
| WR | **0.54** | 0.51 | 0.44 |
| TE | **0.57** | 0.53 | 0.49 |
| K | 0.04 | **0.15** | 0.13 |
| DL | **0.28** | 0.19 | 0.19 |
| LB | **0.42** | 0.31 | 0.27 |
| DB | **0.38** | 0.29 | 0.24 |

Head-to-head with offense.py on the same 1,117 player-weeks (weeks 4-8): about even overall (Spearman 0.396 vs 0.399, MAE 4.87 vs 4.88);
better on WR and TE, worse on RB and QB, so the blend helps. Kickers are close to noise for every model.
The 10-90 band covers 76-81% of outcomes (target 80%), and P(start) beats the position base rate on log loss at every position.
Full output: `player_model_backtest.txt`. Route participation is not in free nflverse data, so routes are not used yet.

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
