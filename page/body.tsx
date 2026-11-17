
type P = {
  player: string; team: string; pos: string; opp: string; mean: number; floor: number; median: number; p90: number;
  p_boom: number; grade: string; snap: number | null; useful: string; cv: number | null; ros: number | null;
  inj: string; implied: number | null; status: string; pct: number | null; lb: boolean;
};

const num = (v: Val): number | null => (typeof v === "number" ? v : null);
const str = (v: Val): string => (typeof v === "string" ? v : "");
const PLAYERS: P[] = DATA.players.map((r) => ({
  player: str(r[0]), team: str(r[1]), pos: str(r[2]), opp: str(r[3]),
  mean: num(r[4]) ?? 0, floor: num(r[5]) ?? 0, median: num(r[6]) ?? 0, p90: num(r[7]) ?? 0, p_boom: num(r[8]) ?? 0,
  grade: str(r[9]), snap: num(r[10]), useful: str(r[11]), cv: num(r[12]), ros: num(r[13]), inj: str(r[14]),
  implied: num(r[15]), status: str(r[16]), pct: num(r[17]), lb: r[18] === true,
}));

const OFF = ["QB", "RB", "WR", "TE", "K"];
const IDP = ["DL", "LB", "DB"];
const VIEWS = [...OFF, ...IDP, "LB slot", "D slot", "My roster"];
const GRADE_RANK: Record<string, number> = { "A+": 7, A: 6, B: 5, C: 4, "C-": 3, D: 2, F: 1 };

const f1 = (x: number | null): string => (x === null ? "–" : x.toFixed(1));
const pc = (x: number | null): string => (x === null ? "–" : `${Math.round(x * 100)}%`);
const gradeCell = (g: string): Cell => {
  if (g === "A+" || g === "A") return { text: g, tone: "success" };
  if (g === "D") return { text: g, tone: "warning" };
  if (g === "F") return { text: g, tone: "danger" };
  return g || "–";
};
const statusText = (p: P): string => {
  const s = p.status === "mine" ? "Mine" : p.status === "W" ? "Waivers" : p.status === "FA" ? "FA" : "Rostered";
  const pct = p.pct === null ? "" : ` ${p.pct}%`;
  const inj = p.inj ? ` · ${p.inj}` : "";
  return s + pct + inj;
};

type SortKey = "auto" | "mean" | "floor" | "median" | "p90" | "p_boom" | "grade" | "snap" | "useful" | "cv" | "ros" | "opp";
const SORTS: { value: SortKey; label: string }[] = [
  { value: "auto", label: "Mode default" }, { value: "mean", label: "Mean" }, { value: "floor", label: "Floor (P10)" },
  { value: "median", label: "Median" }, { value: "p90", label: "P90" }, { value: "p_boom", label: "P(boom)" },
  { value: "grade", label: "Matchup grade" }, { value: "snap", label: "Snap share" }, { value: "useful", label: "Useful games" },
  { value: "cv", label: "Consistency (low CV)" }, { value: "ros", label: "ROS ppg" }, { value: "opp", label: "Opponent" },
];
const usefulFrac = (u: string): number => {
  const [a, b] = u.split("/").map(Number);
  return b ? a / b : -1;
};
const sortVal = (p: P, k: SortKey): number | string => {
  switch (k) {
    case "grade": return GRADE_RANK[p.grade] ?? 0;
    case "snap": return p.snap ?? -1;
    case "useful": return usefulFrac(p.useful);
    case "cv": return p.cv === null ? -99 : -p.cv;
    case "ros": return p.ros ?? -1;
    case "opp": return p.opp.replace(/^(vs|@) /, "");
    case "auto": return p.mean;
    default: return p[k];
  }
};

const slotTable = (rows: Slot[]) => (
  <Table
    columns={["Slot", "Player", "Matchup", "Grade", "Mean", "Floor", "P90", "P(boom)"]}
    rows={rows.map((s) => [s.slot, `${s.player} · ${s.team} ${s.pos}`, s.matchup, gradeCell(s.grade), f1(s.mean), f1(s.floor), f1(s.p90), pc(s.p_boom)])}
  />
);

const BT_RE = /^\s*(QB|RB|WR|TE|K)?\s*(base_inj|base|model)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)/;
const btRows = (): Cell[][] => {
  const out: Cell[][] = [];
  let pos = "";
  let inAll = false;
  for (const line of DATA.backtest.split("\n")) {
    if (line.startsWith("All positions")) { inAll = true; pos = "All"; continue; }
    if (line.startsWith("Calibration")) break;
    const m = BT_RE.exec(line);
    if (!m) continue;
    if (m[1]) pos = m[1];
    if (inAll && !m[1]) pos = "All";
    const label = m[2] === "model" ? "Model" : m[2] === "base_inj" ? "Season avg, injury-adj." : "Season avg";
    out.push([pos, m[2] === "model" ? { text: label, tone: "success" } : label, m[3], m[4], m[5], m[6]]);
  }
  return out;
};
const calLines = (): string[] => {
  const i = DATA.backtest.indexOf("Calibration");
  if (i < 0) return [];
  return DATA.backtest.slice(i).split("\n").map((l) => l.trim()).filter((l) => l.length > 0).slice(0, 4);
};

type TSort = "minG" | "ga" | "gb" | "bal" | "accept" | "kind";
const ACCEPT_ORDER: Record<string, number> = { "Easy yes": 0, "Fair on paper": 1, "Hard sell": 2, "Unlikely": 3 };
const acceptCell = (a: string): Cell =>
  a === "Unlikely" ? { text: a, tone: "danger" } : a === "Hard sell" ? { text: a, tone: "warning" } : { text: a, tone: "success" };
const plus = (v: number): string => `${v >= 0 ? "+" : ""}${v.toFixed(1)}`;
const tradeSortVal = (r: TradeRow, k: TSort): number | string =>
  k === "accept" ? ACCEPT_ORDER[r.accept] ?? 9 : k === "kind" ? r.kind : r[k];

function TradeFinder() {
  const [scope, setScope] = useState<"mine" | "all" | "wr2">("mine");
  const [partner, setPartner] = useState<string>("All");
  const [tsort, setTsort] = useState<TSort>("minG");
  const [tdir, setTdir] = useState<"desc" | "asc">("desc");
  const [hideUnlikely, setHideUnlikely] = useState<boolean>(false);

  const base = TRADES.rows.filter((r) => (scope === "wr2" ? r.preset === "wr2" : !r.preset && (scope === "mine" ? r.mine : true)));
  const teams = Array.from(new Set(scope !== "all" ? base.map((r) => r.b) : base.flatMap((r) => [r.a, r.b]))).sort();
  let rows = base.filter((r) => partner === "All" || r.b === partner || (scope === "all" && r.a === partner));
  if (hideUnlikely) rows = rows.filter((r) => r.accept !== "Unlikely");
  const dir = tdir === "desc" ? -1 : 1;
  rows = [...rows].sort((x, y) => {
    const vx = tradeSortVal(x, tsort);
    const vy = tradeSortVal(y, tsort);
    if (vx < vy) return -dir;
    if (vx > vy) return dir;
    return y.minG - x.minG;
  });
  const why = (r: TradeRow): string => `${r.reason}${r.moves ? ` Moves: ${r.moves}.` : ""} Paper value: ${r.note}.`;
  const mineRows: Cell[][] = rows.map((r) => [r.b, r.get, r.give, plus(r.ga), plus(r.gb), r.bal.toFixed(2), acceptCell(r.accept), why(r)]);
  const allRows: Cell[][] = rows.map((r) => [r.a, r.get, r.give, r.b, plus(r.ga), plus(r.gb), r.bal.toFixed(2), acceptCell(r.accept), why(r)]);
  const mineAll = TRADES.rows.filter((r) => r.mine && !r.preset);
  const wr2All = TRADES.rows.filter((r) => r.preset === "wr2");
  const best = mineAll.length ? mineAll[0] : null;
  const sorts: { value: TSort; label: string }[] = [
    { value: "minG", label: "Smaller gain (default)" }, { value: "ga", label: scope !== "all" ? "Your gain" : "Team A gain" },
    { value: "gb", label: scope !== "all" ? "Their gain" : "Team B gain" }, { value: "bal", label: "Balance" },
    { value: "accept", label: "Acceptance" }, { value: "kind", label: "Trade size" },
  ];

  return (
    <Section heading="Trade Finder" id="trades" caption={`Gains are rest-of-season starting-lineup points (weeks ${TRADES.weeks}, playoff weeks weighted by each team's playoff odds), not player value. Only trades where both teams gain and the smaller gain is at least ${Math.round(TRADES.minRatio * 100)}% of the larger (and at least ${TRADES.minGain} points) are listed. Ranked by the smaller gain.`}>
      <Metrics metrics={[
        { value: String(mineAll.length), label: `Mutual trades for ${TRADES.me}` },
        { value: best ? plus(best.minG) : "–", label: "Best smaller-side gain", detail: best ? `${best.get} for ${best.give}` : "" },
        { value: String(TRADES.nKept), label: "Mutual trades league-wide", detail: `out of ${TRADES.nWinWin} where both sides gain at all` },
      ]} />
      <Segmented value={scope} onChange={(v: string) => { setScope(v === "all" ? "all" : v === "wr2" ? "wr2" : "mine"); setPartner("All"); }} options={[{ value: "mine", label: "My trades", count: mineAll.length }, { value: "wr2", label: "WR2 without Bowers", count: wr2All.length }, { value: "all", label: "All league", count: TRADES.rows.filter((r) => !r.preset).length }]} />
      {scope === "wr2" ? <Callout tone="info" lead="WR2 without Bowers:">{`Bowers and Lamb never leave. Every trade here brings back a WR projecting 9.5+ pts/wk rest of season (Shakir projects 7.4), and the WR slots are the biggest part of your gain. Same 40% balance rule and market check as above. Trades that include Hunter Henry are flagged in the Why column (he is Bowers' bye-week cover). One row per package received; the full list is in trades_week8_wr2.csv. Waivers: no free-agent WR clears the bar. The best by projection is Malik Washington at 7.6/wk; Flournoy and Douglas have had 11-13 ppg over the last 3 games on 5.7 targets a game, which is touchdown-driven.`}</Callout> : null}
      <Grid columns={4}>
        <Select label={scope !== "all" ? "Partner" : "Team"} value={partner} onChange={(v: string) => setPartner(v)} options={["All", ...teams].map((t) => ({ value: t, label: t }))} />
        <Select label="Sort by" value={tsort} onChange={(v: string) => setTsort(v as TSort)} options={sorts} />
        <Segmented value={tdir} onChange={(v: string) => setTdir(v === "asc" ? "asc" : "desc")} options={[{ value: "desc", label: "High → low" }, { value: "asc", label: "Low → high" }]} />
        <Toggle label="Hide unlikely" value={hideUnlikely} onChange={(v: boolean) => setHideUnlikely(v)} />
      </Grid>
      {scope !== "all"
        ? <Table columns={["Partner", "You get", "You give", "Your gain", "Their gain", "Balance", "Acceptance", "Why"]} rows={mineRows} />
        : <Table columns={["Team A", "A gets", "A gives", "Team B", "A gain", "B gain", "Balance", "Acceptance", "Why"]} rows={allRows} />}
      <Section heading="How the trade finder works" collapsible defaultOpen={false}>
        <BulletList items={[
          "Each team's value = sum over remaining weeks of its best legal lineup (QB, 2 RB, 2 WR, TE, W/R/T, K, D, LB). Empty or weak slots are filled by streaming the best free agent at 85% of his projection, 60% for tight ends (in 2026 weeks 2-7 the top-projected free-agent TEs scored only 45-63% of projection; QB, RB and WR streamers scored 84-90%).",
          "Depth counts a little: each starter has a 6% weekly chance of an unexpected miss, so a backup is worth 6% of his edge over the streamer.",
          "Injuries by Yahoo tag: Q 85% this week, then 95%, then full. D 25% then 85%. O out this week, 70% next. IR/IR-R/NA out 4 weeks, then 60% (IR) or 90% (IR-R).",
          "Week weights: this week 0.5 (trade processing lag), weeks 9-14 1.0, weeks 15-17 0.5 + playoff odds. Playoff odds come from a simulation of the rest of the regular season using each team's current lineup strength and record (6 teams assumed to make it; real schedule not exported).",
          "A team receiving 2-for-1 drops its least valuable player; a team left short adds the best free agent. Both are shown under Moves.",
          `Balance = smaller gain ÷ larger gain. Cut-off ${TRADES.minRatio}: below that one side is mostly a donor. About half of all win-win trades are under 0.4.`,
          "Acceptance compares consensus trade values from the partner's side (best player + 70% of the second). Unlikely = they give up 30%+ more paper value. Hard sell = 12-30% more. Easy yes = they get 25%+ more on paper.",
          ...TRADES.sources.map((s) => `Source: ${s}`),
          ...TRADES.tests.map((t) => `Sanity test ${t.passed ? "passed" : "FAILED"}: ${t.test} (${t.trade}: ${plus(t.gain_me)} / ${plus(t.gain_them)})`),
          `Playoff odds used: ${TRADES.odds.map((o) => `${o.team} ${Math.round(o.p * 100)}%`).join(", ")}.`,
        ]} />
      </Section>
    </Section>
  );
}

export default function FantasyRankings() {
  const [mode, setMode] = useState<"safe" | "boom">("safe");
  const [view, setView] = useState<string>("RB");
  const [avail, setAvail] = useState<boolean>(false);
  const [sortKey, setSortKey] = useState<SortKey>("auto");
  const [desc, setDesc] = useState<"desc" | "asc">("desc");
  const [group, setGroup] = useState<"proj" | "profile">("proj");
  const [wpos, setWpos] = useState<string>("All");
  const [limit, setLimit] = useState<string>("40");

  const lineup = DATA.lineup[mode];
  const total = lineup.reduce((a, s) => a + s.mean, 0);
  const totalP90 = lineup.reduce((a, s) => a + s.p90, 0);

  let rows = PLAYERS.filter((p) => {
    if (view === "LB slot") return p.lb;
    if (view === "D slot") return IDP.includes(p.pos);
    if (view === "My roster") return p.status === "mine";
    return p.pos === view;
  });
  if (avail) rows = rows.filter((p) => p.status === "FA" || p.status === "W" || p.status === "mine");
  const key: SortKey = sortKey === "auto" ? (mode === "safe" ? "mean" : "p90") : sortKey;
  const dir = desc === "desc" ? -1 : 1;
  rows = [...rows].sort((a, b) => {
    const va = sortVal(a, key);
    const vb = sortVal(b, key);
    if (va < vb) return -dir;
    if (va > vb) return dir;
    return mode === "safe" ? b.floor - a.floor : b.p_boom - a.p_boom;
  });
  const shown = limit === "all" ? rows : rows.slice(0, Number(limit));

  const name = (p: P): string => `${p.player}${p.status === "mine" ? " ★" : ""}`;
  const projRows: Cell[][] = shown.map((p) => [name(p), `${p.team} ${p.pos}`, p.opp, gradeCell(p.grade), f1(p.mean), f1(p.floor), f1(p.median), f1(p.p90), pc(p.p_boom)]);
  const profRows: Cell[][] = shown.map((p) => [name(p), `${p.team} ${p.pos}`, statusText(p), pc(p.snap), p.useful || "–", p.cv === null ? "–" : p.cv.toFixed(2), f1(p.ros), f1(p.implied)]);

  const waivers = DATA.waivers.filter((w) => wpos === "All" || w.pos === wpos);
  const wRows: Cell[][] = waivers.map((w) => [
    w.player, `${w.team} ${w.pos} · ${w.opp}`, `${w.status}${w.pct === null ? "" : ` ${w.pct}%`}`, f1(w.ros), f1(w.wk),
    w.gain >= 0.5 ? { text: `+${w.gain.toFixed(1)}`, tone: "success" } : w.gain > 0 ? `+${w.gain.toFixed(1)}` : w.gain.toFixed(1),
    w.verdict === "clear ROS upgrade" ? { text: "Upgrade", tone: "success" } : w.verdict, w.faab,
  ]);
  const notes = [...lineup, ...DATA.bench].filter((s) => s.note).map((s) => `${s.player}: ${s.note}`);

  return (
    <Page title={`Fantasy Week ${DATA.week} Rankings`} width="full">
      <Text>{`${DATA.league} · ${DATA.season} week ${DATA.week} · data generated ${DATA.generated} · FAAB $${DATA.faab}, waivers clear ${DATA.waivers_clear}`}</Text>

      <Section heading="Recommended lineup" id="lineup" caption="Brute-force best lineup from your roster. Safe maximizes mean (floor breaks ties); Boom maximizes P90 (P(boom) breaks ties). Sherwood at LB and Hamilton at D are fixed.">
        <Segmented value={mode} onChange={(v: string) => setMode(v === "boom" ? "boom" : "safe")} options={[{ value: "safe", label: "Safe" }, { value: "boom", label: "Boom" }]} />
        <Metrics metrics={[
          { value: f1(total), label: "Projected lineup points (mean)" },
          { value: f1(totalP90), label: "Sum of P90s" },
          { value: `$${DATA.faab}`, label: "FAAB left", detail: `Waivers clear ${DATA.waivers_clear}` },
        ]} />
        {slotTable(lineup)}
        <Text>Bench and IR</Text>
        {slotTable(DATA.bench)}
        <BulletList items={notes} />
      </Section>

      <Section heading="Roster moves" id="moves">
        <Callout tone="warning" lead="Suggested this week">{DATA.moves.join(" ")}</Callout>
      </Section>

      <Section heading="Rankings" id="rankings" caption={`Mode ${mode === "safe" ? "Safe (sorted by mean)" : "Boom (sorted by P90)"} unless you pick a sort. Boom = QB ${DATA.boom_thr.QB}+, RB/WR ${DATA.boom_thr.RB}+, TE ${DATA.boom_thr.TE}+, K ${DATA.boom_thr.K}+, IDP 10+. Grade = projection vs a neutral opponent. ★ = your player.`}>
        <Segmented value={view} onChange={(v: string) => setView(v)} options={VIEWS.map((v) => ({ value: v, label: v }))} />
        <Grid columns={4}>
          <Select label="Sort by" value={sortKey} onChange={(v: string) => setSortKey(v as SortKey)} options={SORTS} />
          <Segmented value={desc} onChange={(v: string) => setDesc(v === "asc" ? "asc" : "desc")} options={[{ value: "desc", label: "High → low" }, { value: "asc", label: "Low → high" }]} />
          <Segmented value={group} onChange={(v: string) => setGroup(v === "profile" ? "profile" : "proj")} options={[{ value: "proj", label: "Projection" }, { value: "profile", label: "Usage & status" }]} />
          <Select label="Show" value={limit} onChange={(v: string) => setLimit(v)} options={[{ value: "25", label: "Top 25" }, { value: "40", label: "Top 40" }, { value: "all", label: "All" }]} />
        </Grid>
        <Toggle label="Available only (FA/waivers, plus your players)" value={avail} onChange={(v: boolean) => setAvail(v)} />
        {group === "proj"
          ? <Table columns={["Player", "Team", "Opp", "Grade", "Mean", "Floor", "Median", "P90", "P(boom)"]} rows={projRows} />
          : <Table columns={["Player", "Team", "Status", "Snap share", "Useful games", "CV (lower = steadier)", "ROS ppg", "Team implied"]} rows={profRows} />}
      </Section>

      <Section heading="Waiver suggestions" id="waivers" caption={`ROS = projected points per game, weeks ${DATA.week}-17, with byes and schedule. Gain = ROS ppg over your weakest starter at that position (or flex). FAAB as % of $${DATA.faab}.`}>
        <Select label="Position" value={wpos} onChange={(v: string) => setWpos(v)} options={["All", ...OFF, ...IDP].map((v) => ({ value: v, label: v }))} />
        <Callout tone="info" lead="Usage audit (Oct 28):">Malik Washington is not a real upgrade over Khalil Shakir. Washington's target share was inflated by 3 games without Caleb Douglas (wks 3-5) and he got 3 targets when Douglas returned in wk 7. The model now discounts targets earned while current teammates were out, scores WR carries at the league WR rate, and ties receiver yards per target to the team's passing efficiency (Willis/MIA vs Allen/BUF). Gains under +0.5/g are toss-ups within model error.</Callout>
        <Table columns={["Player", "Team · matchup", "Status", "ROS ppg", `Wk ${DATA.week}`, "Gain", "Verdict", "FAAB"]} rows={wRows} />
      </Section>

      <TradeFinder />

      <Section heading="Scoring and model check" id="model">
        <Properties items={[{ label: "League scoring", value: DATA.scoring }]} />
        <Text>{`Backtest, weeks 4-${DATA.week - 1}: each week projected using only earlier games, compared with season-average points. Spearman = rank correlation with actual points; hit = overlap between the projected top group and the actual top group.`}</Text>
        <Table columns={["Pos", "Method", "Spearman", "Hit", "Top avg", "MAE"]} rows={btRows()} />
        <BulletList items={calLines()} />
      </Section>
    </Page>
  );
}
