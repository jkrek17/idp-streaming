#!/usr/bin/env bash
# Rerun weekly: ./run.sh            (auto week)   ./run.sh --week 9
# Before running: save yahoo_league_week<N>.md (IDP available) and yahoo_offense_available_week<N>.md
# (offense available + FAAB), update roster.json if your roster changed, and league_rosters_week<N>.json for trades.
set -e; cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q nflreadpy polars pandas pyarrow scikit-learn; }
.venv/bin/python -c "import sklearn" 2>/dev/null || .venv/bin/pip install -q scikit-learn
.venv/bin/python idp_ratings.py "$@"
WEEK=$(ls -t ratings_week*.csv | head -1 | sed -E 's/ratings_week([0-9]+).csv/\1/')
PREV=$((WEEK-1)); LO=$(( PREV-3 > 1 ? PREV-3 : 2 ))
# v3 threshold model: P(>=6) and P(>=12) from 2018-present history -> threshold_week<N>.csv (refreshes this season's data)
.venv/bin/python idp_threshold.py --refresh --week "$WEEK"
# IDP streamers (needs yahoo_league_week<N>.md)
[ -f "yahoo_league_week${WEEK}.md" ] && .venv/bin/python streamers.py --week "$WEEK" || echo "no yahoo_league_week${WEEK}.md; skipped streamers"
# offense backtest on the last 4 completed weeks (feeds the dashboard's model-check panel)
.venv/bin/python offense.py --backtest "${LO}-${PREV}" > /dev/null
cp "backtest_offense_weeks${LO}-${PREV}.txt" backtest_offense_latest.txt
# offense projections, start/sit, lineup, waivers, dashboard JSON (needs both Yahoo files + roster.json)
if [ -f "yahoo_offense_available_week${WEEK}.md" ] && [ -f "yahoo_league_week${WEEK}.md" ]; then
  .venv/bin/python fantasy.py --week "$WEEK"
  .venv/bin/python make_page_data.py "$WEEK"
  # trade finder (needs league_rosters_week<N>.json: every team's roster, scraped read-only)
  if [ -f "league_rosters_week${WEEK}.json" ]; then
    .venv/bin/python trade_finder.py --week "$WEEK"
  else
    echo "no league_rosters_week${WEEK}.json; trade finder skipped"
    echo 'const TRADES: TradeData = {"week":'"$WEEK"',"weeks":"","me":"","sources":[],"minRatio":0.4,"minGain":3,"nWinWin":0,"nKept":0,"odds":[],"tests":[],"rows":[]};' > "page_trades_week${WEEK}.txt"
  fi
  cat page/head.tsx "page_data_week${WEEK}.txt" "page_trades_week${WEEK}.txt" page/body.tsx > "page/page_week${WEEK}.tsx"
  echo "dashboard: page/page_week${WEEK}.tsx built -> ask Grok Bot to refresh the 'Fantasy Week ${WEEK} Rankings' Page (canvas 1ef81067-034a-4b9a-b69e-b27a311688f3)"
else
  .venv/bin/python offense.py --week "$WEEK"
  echo "missing Yahoo files for week ${WEEK}; wrote offense_week${WEEK}.csv only"
fi
