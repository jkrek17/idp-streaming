import { Page, Section, Table, Segmented, Select, Toggle, Callout, Metrics, Properties, BulletList, Text, Grid, useState } from "grok/canvas";

type Val = string | number | boolean | null;
type Tone = "success" | "warning" | "danger";
type Cell = string | { text: string; tone: Tone };
type Slot = { slot: string; player: string; team: string; pos: string; matchup: string; mean: number; floor: number; p90: number; p_boom: number; grade: string; note: string };
type Waiver = { pos: string; player: string; team: string; status: string; pct: number | null; ros: number; wk: number; gain: number; verdict: string; faab: string; opp: string };
type Data = {
  week: number; season: number; generated: string; league: string; faab: number; waivers_clear: string;
  players: Val[][];
  lineup: { safe: Slot[]; boom: Slot[] }; bench: Slot[]; moves: string[]; waivers: Waiver[];
  boom_thr: Record<string, number>; scoring: string; backtest: string;
};
type TradeRow = { mine: boolean; a: string; aid: number; b: string; bid: number; kind: string; get: string; give: string; ga: number; gb: number; bal: number; minG: number; accept: string; note: string; ratio: number; moves: string; reason: string; preset?: string };
type TradeTest = { test: string; trade: string; gain_me: number; gain_them: number; passed: boolean };
type TradeData = { week: number; weeks: string; me: string; sources: string[]; minRatio: number; minGain: number; nWinWin: number; nKept: number; odds: { team: string; p: number }[]; tests: TradeTest[]; rows: TradeRow[] };
