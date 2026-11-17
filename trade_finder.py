"""Mutual-benefit trade finder (analysis only; never touches Yahoo).

A trade is judged by how much it changes each team's rest-of-season STARTING LINEUP points, not raw player value:
  team value = sum over remaining weeks of (best legal lineup that week, empty slots streamed from free agents)
               minus a small depth term (expected points lost when a starter misses an unexpected week),
               with playoff weeks (15-17) weighted up for likely playoff teams.
Only trades where both teams gain, and the smaller gain is >= MIN_RATIO of the larger, are kept.
A public consensus (FantasyCalc redraft values + FantasyPros ROS ECR) flags trades a partner is unlikely to accept.

Usage: .venv/bin/python trade_finder.py --week 8 [--team 4] [--selftest]
Inputs: league_rosters_weekN.json, yahoo_offense_available_weekN.md, yahoo_league_weekN.md, consensus/ (re-fetched)
Outputs: trades_weekN.csv, page_trades_weekN.txt (const TRADES for the Page)
"""
import argparse, itertools, json, math, os, re, time, urllib.request
import numpy as np
import pandas as pd
import idp_ratings as M
import offense as O
from idp_ratings import norm_name
from fantasy import parse_offense_md, match_ids, team_code
from streamers import parse_league

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = dict(
    last_reg=14, last_week=17,      # regular season ends week 14; Yahoo playoffs assumed weeks 15-17 (not in exports)
    w_now=0.5,                      # current week: trades process ~1-2 days and Thursday games may be locked
    po_base=0.5, po_contend=1.0,    # playoff week weight = po_base + po_contend * P(make playoffs)
    playoff_teams=6, team_sd=22.0,  # for the playoff-odds Monte Carlo
    stream=0.85,                    # best free agent each week, discounted (you won't always guess the right one)
    # per-position override, calibrated on 2026 wks 2-7: actual pts of the top-projected FAs / their projection
    # (QB .84, RB .84, WR .90, TE .63; TE top pick alone .45). FA tight ends score far below their projections.
    stream_pos=dict(TE=float(os.environ.get("TF_STREAM_TE", 0.60))),
    p_miss=0.06,                    # per-week chance a healthy starter misses unexpectedly -> depth has value
    roster=16, ir_slots=2,
    min_ratio=0.40,                 # smaller gain must be >= 40% of the larger
    min_gain=3.0,                   # and >= 3 weighted ROS points (~0.3/week), below that it's noise
    cand=9,                         # tradeable candidates per team (by marginal lineup value)
)
IR_TAGS = {"IR", "IR-R", "IR-NR", "NA", "PUP", "PUP-R", "INA", "O"}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
GROUPS = ["QB", "RB", "WR", "TE", "K", "IDP"]


# ------------------------------------------------------------------ injuries by Yahoo tag, k = weeks from now
def inj_mult(tag, k, missed_recent=False):
    tag = (tag or "").upper()
    if tag == "Q":
        return [0.85, 0.95][k] if k < 2 else 1.0
    if tag == "D":
        return [0.25, 0.85][k] if k < 2 else 1.0
    if tag == "O":
        return [0.0, 0.7][k] if k < 2 else 1.0
    if tag in {"IR", "INA", "NA", "PUP", "PUP-R", "IR-NR"}:
        return 0.0 if k < 4 else 0.6
    if tag == "IR-R":
        return 0.0 if k < 4 else 0.9
    if tag == "SUSP":
        return 0.0 if k < 2 else 1.0
    if missed_recent:
        return 0.6 if k == 0 else (0.9 if k == 1 else 1.0)
    return 1.0


# ------------------------------------------------------------------ weekly projections
def offense_weekly(D, B, W, weeks):
    X0 = O.project(D, B, W)
    R = O.player_rates(B, D, W)
    cols = {}
    for w in weeks:
        X = X0 if w == W else O.project(D, B, W, gm=O.games_for_week(D, w))
        cols[w] = X.mean_pts
    P = pd.DataFrame(cols).reindex(R.index).fillna(0.0)
    ref = R[["player", "team", "pos"]].copy()
    ref["season_ppg"] = R.season_ppg
    ref["missed_recent"] = R.missed_recent.fillna(0) > 0
    ref["nfl_mult0"] = X0.p_play.reindex(R.index)    # nflverse injury report for this week (if any)
    return P, ref


def idp_weekly(D, W, weeks):
    """IDP model for future week w = run the week-W model with week-w's schedule relabelled as W (same data window)."""
    sched, inj = D["sched"], D["inj"]
    cols, refs = {}, []
    for w in weeks:
        D2 = dict(D)
        if w != W:
            fut = sched[sched.week == w].assign(week=W)
            D2["sched"] = pd.concat([sched[sched.week != W], fut], ignore_index=True)
            D2["inj"] = inj[inj.week != W]
        T = M.project(D2, W).drop_duplicates("gsis_id").set_index("gsis_id")
        cols[w] = T.proj_raw if w != W else T.proj_pts
        refs.append(T[["player", "team", "pos", "season_ppg"]])
    P = pd.DataFrame(cols).fillna(0.0)
    ref = pd.concat(refs)
    ref = ref[~ref.index.duplicated(keep="first")].reindex(P.index)
    return P, ref


# ------------------------------------------------------------------ consensus / perceived value
def fetch(url, path, binary=False):
    try:
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=30).read()
        if len(data) > 5000:
            open(path, "wb").write(data)
    except Exception as e:
        print("  consensus fetch failed:", url, e, "(using cached copy if present)")
    return path if os.path.exists(path) else None


def fp_ecr(path):
    s = open(path, encoding="utf-8", errors="ignore").read()
    m = re.search(r"var ecrData = (\{.*?\});\s*\n", s)
    d = json.loads(m.group(1))
    df = pd.DataFrame(d["players"])
    df.attrs.update(experts=d.get("total_experts"), updated=d.get("last_updated"))
    return df


def perceived_values(W):
    cdir = os.path.join(HERE, "consensus"); os.makedirs(cdir, exist_ok=True)
    src = {}
    fc_p = fetch("https://api.fantasycalc.com/values/current?isDynasty=false&numQbs=1&numTeams=12&ppr=0.5",
                 os.path.join(cdir, "fantasycalc_redraft.json"))
    fpo_p = fetch("https://www.fantasypros.com/nfl/rankings/ros-half-point-ppr-overall.php", os.path.join(cdir, "fp_ros_overall.html"))
    fpi_p = fetch("https://www.fantasypros.com/nfl/rankings/ros-idp.php", os.path.join(cdir, "fp_ros_idp.html"))
    rows = []
    fc = None
    if fc_p:
        fc = pd.DataFrame([dict(name=x["player"]["name"], team=team_code(x["player"].get("maybeTeam") or ""),
                                pos=x["player"]["position"], fc=x["value"]) for x in json.load(open(fc_p))])
        src["fantasycalc"] = f"FantasyCalc redraft trade values (12-team, 1QB, half PPR; {len(fc)} players, fetched {time.strftime('%Y-%m-%d')})"
    fpo = fp_ecr(fpo_p) if fpo_p else None
    fpi = fp_ecr(fpi_p) if fpi_p else None
    if fpo is not None:
        src["fp_overall"] = f"FantasyPros ROS half-PPR overall ECR ({len(fpo)} players, {fpo.attrs['experts']} experts, updated {fpo.attrs['updated']})"
    if fpi is not None:
        src["fp_idp"] = f"FantasyPros ROS IDP ECR ({len(fpi)} players, {fpi.attrs['experts']} experts, updated {fpi.attrs['updated']})"
    # value curve: FantasyCalc value as a function of FantasyPros overall rank (fit on players in both)
    curve = None
    if fpo is not None:
        fpo = fpo.assign(key=fpo.player_name.map(norm_name), team=fpo.player_team_id.map(team_code))
        if fc is not None:
            j = fpo.merge(fc.assign(key=fc.name.map(norm_name)), on="key").sort_values("rank_ecr")
            r, v = j.rank_ecr.values.astype(float), j.fc.values.astype(float)
            # monotone smooth: log-value vs log-rank linear fit
            b = np.polyfit(np.log(r), np.log(np.maximum(v, 50)), 2)
            curve = lambda rk: float(np.exp(np.polyval(b, np.log(max(rk, 1)))))
        else:
            curve = lambda rk: 10000.0 * math.exp(-rk / 45.0)
    vals = {}
    if fpo is not None:
        for p in fpo.itertuples():
            v = curve(p.rank_ecr) if p.player_position_id != "K" else min(curve(p.rank_ecr), 300.0)
            vals[(p.key, p.player_position_id if p.player_position_id != "DST" else "DST")] = (v, f"FP #{p.rank_ecr} {p.pos_rank}")
    if fc is not None:
        for p in fc.itertuples():
            vals[(norm_name(p.name), p.pos)] = (float(p.fc), f"FC {p.fc}")
    if fpi is not None and curve is not None:
        for p in fpi.itertuples():
            # 2 IDP starters per team: IDP1 ~ overall rank 90, then ~5 ranks per IDP rank
            vals[(norm_name(p.player_name), "IDP")] = (curve(85 + 5 * p.rank_ecr), f"FP IDP #{p.rank_ecr} {p.pos_rank}")
    return vals, src


# ------------------------------------------------------------------ league + pool assembly
def load_players(D, B, W, weeks, team_id):
    L = json.load(open(os.path.join(HERE, f"league_rosters_week{W}.json")))
    t0 = time.time()
    Poff, Roff = offense_weekly(D, B, W, weeks)
    Pidp, Ridp = idp_weekly(D, W, weeks)
    print(f"  projections {weeks[0]}-{weeks[-1]}: {time.time() - t0:.0f}s")
    rows = []
    for t in L["teams"]:
        for p in t["players"]:
            rows.append(dict(owner=t["team_id"], player_y=p["name"], team=team_code(p["nfl_team"] or ""),
                             ypos=p["positions"], slot=p["slot"], tag=p["status"] or ""))
    fa_off = parse_offense_md(os.path.join(HERE, f"yahoo_offense_available_week{W}.md"))
    for p in fa_off.itertuples():
        rows.append(dict(owner=0, player_y=p.player_y, team=p.team, ypos=p.pos, slot="FA", tag=p.tag))
    lp = os.path.join(HERE, f"yahoo_league_week{W}.md")
    if os.path.exists(lp):
        fa_idp = parse_league(lp)
        for p in fa_idp.itertuples():
            ypos = p.yahoo_pos if p.yahoo_pos not in {"DL"} else "DE"
            rows.append(dict(owner=0, player_y=p.player_y, team=p.team, ypos=ypos, slot="FA", tag=p.yahoo_tag))
    Y = pd.DataFrame(rows)
    Y = Y[~((Y.owner == 0) & Y.player_y.map(norm_name).isin(set(Y[Y.owner > 0].player_y.map(norm_name))))]
    Y = Y.drop_duplicates(["owner", "player_y", "team"]).reset_index(drop=True)
    Y["id_off"] = match_ids(Y, Roff[["player", "team"]])
    Y["id_idp"] = match_ids(Y, Ridp[["player", "team"]])
    # name-only fallback (team changes): unique normalized name
    for col, R in (("id_off", Roff), ("id_idp", Ridp)):
        nm = pd.Series(R.index.values, index=R.player.map(norm_name).values)
        nm = nm[~nm.index.duplicated(keep=False)]
        Y[col] = Y[col].fillna(Y.player_y.map(norm_name).map(nm))
    off_pos = {"QB", "RB", "WR", "TE", "K"}
    idp_pos = {"DE", "DT", "LB", "CB", "S", "DL", "DB"}
    recs = []
    nW = len(weeks)
    for y in Y.itertuples():
        ps = set(y.ypos.split(","))
        opts = []
        if ps & off_pos:
            g = [p for p in ["QB", "RB", "WR", "TE", "K"] if p in ps][0]
            pts = Poff.loc[y.id_off].values if isinstance(y.id_off, str) and y.id_off in Poff.index else np.zeros(nW)
            mr = bool(Roff.missed_recent.get(y.id_off, False)) if isinstance(y.id_off, str) else False
            ppg = Roff.season_ppg.get(y.id_off, np.nan) if isinstance(y.id_off, str) else np.nan
            opts.append((g, pts, mr, ppg, isinstance(y.id_off, str)))
        if ps & idp_pos:
            pts = Pidp.loc[y.id_idp].values if isinstance(y.id_idp, str) and y.id_idp in Pidp.index else np.zeros(nW)
            ppg = Ridp.season_ppg.get(y.id_idp, np.nan) if isinstance(y.id_idp, str) else np.nan
            opts.append(("IDP", pts, False, ppg, isinstance(y.id_idp, str)))
        if not opts:
            continue
        mult = np.array([inj_mult(y.tag, k, False) for k in range(nW)])
        best = None
        for g, pts, mr, ppg, matched in opts:
            m2 = np.array([inj_mult(y.tag, k, mr) for k in range(nW)])
            v = pts * m2
            if best is None or v.sum() > best[1].sum():
                best = (g, v, ppg, matched)
        g, v, ppg, matched = best
        recs.append(dict(owner=y.owner, name=y.player_y, nfl=y.team, ypos=y.ypos, slot=y.slot, tag=y.tag, grp=g,
                         lb="LB" in ps, ir_ok=(y.tag.upper() in IR_TAGS), matched=matched, season_ppg=ppg, pts=v))
    P = pd.DataFrame(recs)
    miss = P[(P.owner > 0) & ~P.matched]
    if len(miss):
        print("  unmatched rostered players (projected 0):", ", ".join(f"{r.name} ({r.nfl})" for r in miss.itertuples()))
    return P, L


# ------------------------------------------------------------------ lineup engine
class Engine:
    def __init__(self, P, weeks, W):
        self.P = P
        self.PTS = np.vstack(P.pts.values)
        self.G = P.grp.values
        self.LB = P.lb.values.astype(bool)
        self.IR = P.ir_ok.values.astype(bool)
        self.weeks = weeks
        nW = len(weeks)
        fa = P.owner.values == 0
        self.f = {}
        for g in GROUPS:
            m = fa & (self.G == g)
            self.f[g] = CFG["stream_pos"].get(g, CFG["stream"]) * (self.PTS[m].max(0) if m.any() else np.zeros(nW))
        m = fa & (self.G == "IDP") & self.LB
        self.f["LB"] = CFG["stream"] * (self.PTS[m].max(0) if m.any() else np.zeros(nW))
        self.f["D"] = self.f["IDP"]
        # FA add candidates (for teams left short): best 2 per group by ROS sum
        ros = self.PTS.sum(1)
        self.fa_add = []
        for g in GROUPS:
            idx = np.where(fa & (self.G == g))[0]
            self.fa_add += list(idx[np.argsort(-ros[idx])][:1])
        idx = np.where(fa & (self.G == "IDP") & self.LB)[0]
        self.fa_add += list(idx[np.argsort(-ros[idx])][:1])
        self.fa_add = sorted(set(self.fa_add))

    def _top(self, rows, g, k, mask=None):
        m = self.G[rows] == g
        if mask is not None:
            m = m & mask
        X = self.PTS[rows[m]]
        out = np.zeros((k, self.PTS.shape[1]))
        if len(X):
            S = -np.sort(-X, axis=0)[:k]
            out[:len(S)] = S
        return out

    def weekly(self, rows, detail=False):
        """Per-week lineup points (after depth term). rows: np.array of global indices."""
        rows = np.asarray(rows, dtype=int)
        f, pm = self.f, CFG["p_miss"]
        tot = 0.0; loss = 0.0; det = {}
        for g, n in (("QB", 1), ("K", 1)):
            s = self._top(rows, g, 2)
            st, bk = np.maximum(s[0], f[g]), np.maximum(s[1], f[g])
            tot = tot + st; loss = loss + pm * (st - bk); det[g] = st
        R = self._top(rows, "RB", 4); Wr = self._top(rows, "WR", 4); T = self._top(rows, "TE", 3)
        r1, r2 = np.maximum(R[0], f["RB"]), np.maximum(R[1], f["RB"])
        w1, w2 = np.maximum(Wr[0], f["WR"]), np.maximum(Wr[1], f["WR"])
        t1 = np.maximum(T[0], f["TE"])
        fx_opts = np.vstack([R[2], Wr[2], T[1], f["RB"], f["WR"], f["TE"]])
        src = fx_opts.argmax(0); flex = fx_opts.max(0)
        nR = np.where(src == 0, R[3], R[2]); nWr = np.where(src == 1, Wr[3], Wr[2]); nT = np.where(src == 2, T[2], T[1])
        bR, bW, bT = np.maximum(nR, f["RB"]), np.maximum(nWr, f["WR"]), np.maximum(nT, f["TE"])
        bF = np.maximum.reduce([bR, bW, bT])
        tot = tot + r1 + r2 + w1 + w2 + t1 + flex
        loss = loss + pm * ((r1 - bR).clip(0) + (r2 - bR).clip(0) + (w1 - bW).clip(0) + (w2 - bW).clip(0)
                            + (t1 - bT).clip(0) + (flex - bF).clip(0))
        det["RB"] = r1 + r2; det["WR"] = w1 + w2; det["TE"] = t1; det["FLEX"] = flex
        # IDP: one LB-eligible slot + one any-IDP slot
        idr = rows[self.G[rows] == "IDP"]
        nW = self.PTS.shape[1]
        if len(idr):
            X = self.PTS[idr]; lb = self.LB[idr]
            o = np.argsort(-X, axis=0)
            A = np.take_along_axis(X, o, 0)
            A = np.vstack([A, np.zeros((3, nW))])
            XL = np.where(lb[:, None], X, -1.0)
            iL0 = XL.argmax(0); L0 = XL.max(0).clip(0)
            XL2 = XL.copy(); XL2[iL0, np.arange(nW)] = -1.0
            L1 = XL2.max(0).clip(0)
            a0_is_l0 = (o[0] == iL0) & (XL.max(0) >= 0)
            dA = np.where(a0_is_l0, A[1], A[0])
            optA = L0 + np.maximum(dA, f["D"])
            optB = f["LB"] + np.maximum(A[0], f["D"])
            useA = optA >= optB
            pair = np.maximum(optA, optB)
            lbst = np.where(useA, L0, f["LB"]); dst = pair - lbst
            bkD = np.maximum(A[2], f["D"]); bkL = np.maximum(np.where(useA, L1, L0), f["LB"])
            loss = loss + pm * ((dst - bkD).clip(0) + (lbst - bkL).clip(0))
        else:
            pair = f["LB"] + f["D"]
        tot = tot + pair; det["IDP"] = pair
        out = tot - loss
        return (out, det) if detail else out

    def start_share(self, rows, i):
        """Share of remaining weeks player i would be in this roster's starting lineup (flex approximated)."""
        rows = np.asarray(rows, dtype=int); g = self.G[i]
        same = rows[self.G[rows] == g]
        rank = (self.PTS[same] > self.PTS[i][None, :]).sum(0)
        n0 = {"QB": 1, "K": 1, "RB": 2, "WR": 2, "TE": 1, "IDP": 2}[g]
        st = (rank < n0) & (self.PTS[i] >= self.f[g if g != "IDP" else "D"])
        if g in ("RB", "WR", "TE"):
            fx = np.maximum.reduce([self._top(rows, "RB", 3)[2], self._top(rows, "WR", 3)[2], self._top(rows, "TE", 2)[1],
                                    self.f["RB"], self.f["WR"], self.f["TE"]])
            st |= (rank == n0) & (self.PTS[i] >= fx - 1e-9)
        return float(st.mean())

    def value(self, rows, wts):
        return float(self.weekly(rows) @ wts)

    def normalize(self, rows, wts, protect=(), drop_pool=None):
        """Fill to roster limit with best FA / drop lowest-value non-protected player. Returns (rows, dropped, added)."""
        rows = list(rows); dropped, added = [], []
        lim = CFG["roster"] + min(CFG["ir_slots"], int(self.IR[rows].sum()))
        while len(rows) > lim:
            best = None
            for i in rows:
                if i in protect or (drop_pool is not None and i not in drop_pool):
                    continue
                r2 = [j for j in rows if j != i]
                v = self.value(r2, wts)
                if best is None or v > best[0]:
                    best = (v, i)
            if best is None:   # nothing in the drop pool left: fall back to everyone
                drop_pool = None; continue
            rows.remove(best[1]); dropped.append(best[1])
        while len(rows) < lim:
            best = None
            for i in self.fa_add:
                if i in rows:
                    continue
                v = self.value(rows + [i], wts)
                if best is None or v > best[0]:
                    best = (v, i)
            rows.append(best[1]); added.append(best[1])
        return rows, dropped, added


# ------------------------------------------------------------------ playoff odds
def playoff_odds(E, L, team_rows, W, weeks, n=20000, seed=7):
    reg = [i for i, w in enumerate(weeks) if w <= CFG["last_reg"]]
    ids = [t["team_id"] for t in L["teams"]]
    S = np.array([E.weekly(np.array(team_rows[t]))[reg].mean() if reg else 0 for t in ids])
    wins0 = np.array([int(str(t["record"]).split("-")[0]) for t in L["teams"]], dtype=float)
    rng = np.random.default_rng(seed)
    nt = len(ids); made = np.zeros(nt)
    sd = CFG["team_sd"]
    for _ in range(n // 100):
        wins = np.tile(wins0, (100, 1)); pf = np.zeros((100, nt))
        for _w in reg:
            perm = np.argsort(rng.random((100, nt)), axis=1)   # random pairings (real schedule not exported)
            sc = S[None, :] + rng.normal(0, sd, (100, nt))
            a, b = perm[:, 0::2], perm[:, 1::2]
            sa, sb = np.take_along_axis(sc, a, 1), np.take_along_axis(sc, b, 1)
            np.put_along_axis(wins, a, np.take_along_axis(wins, a, 1) + (sa > sb), 1)
            np.put_along_axis(wins, b, np.take_along_axis(wins, b, 1) + (sb > sa), 1)
            pf += sc
        key = wins * 1e4 + pf
        top = np.argsort(-key, axis=1)[:, :CFG["playoff_teams"]]
        for r in range(100):
            made[top[r]] += 1
    return dict(zip(ids, made / n)), dict(zip(ids, S))


# ------------------------------------------------------------------ search
def week_weights(weeks, W, p_po):
    w = np.array([CFG["w_now"] if x == W else 1.0 if x <= CFG["last_reg"] else CFG["po_base"] + CFG["po_contend"] * p_po
                  for x in weeks])
    return w


def kind(a, b):
    return f"{len(a)}-for-{len(b)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, required=True)
    ap.add_argument("--team", type=int, default=None, help="your team id (default roster.json / 4)")
    ap.add_argument("--all-pairs", type=int, default=1)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    W = a.week
    me = a.team or 4
    weeks = list(range(W, CFG["last_week"] + 1))
    t0 = time.time()
    if os.environ.get("TF_DEV") and os.path.exists(os.path.join(HERE, "off_cache.pkl")):
        import dev_cache; D, B = dev_cache.get()
    else:
        D = M.load_data(2026); B = O.build(D)
    P, L = load_players(D, B, W, weeks, me)
    E = Engine(P, weeks, W)
    names = {t["team_id"]: t["name"] for t in L["teams"]}
    team_rows = {t["team_id"]: list(np.where(P.owner.values == t["team_id"])[0]) for t in L["teams"]}
    p_po, strength = playoff_odds(E, L, team_rows, W, weeks)
    WT = {t: week_weights(weeks, W, p_po[t]) for t in team_rows}
    base = {}
    for t, r in team_rows.items():
        rr, _, _ = E.normalize(r, WT[t])
        base[t] = E.value(rr, WT[t])
    print("  playoff odds:", ", ".join(f"T{t} {p_po[t]:.0%}" for t in sorted(p_po)))

    # candidate pruning: marginal value of each player to his own team (value lost if replaced by a streamer)
    marg = {}
    for t, r in team_rows.items():
        for i in r:
            r2 = [j for j in r if j != i]
            marg[i] = base_val = E.value(r, WT[t]) - E.value(r2, WT[t])
    ros_pg = E.PTS.mean(1)
    droppool = {t: set(sorted(r, key=lambda i: marg[i])[:6]) for t, r in team_rows.items()}
    cands = {}
    for t, r in team_rows.items():
        ok = [i for i in r if P.grp[i] != "K" and E.PTS[i].sum() > 0]
        # keep starters/useful depth (marginal) + bench players who'd start elsewhere (ROS ppg well above streamers)
        fl = {g: E.f[g].mean() for g in GROUPS}
        score = {i: max(marg[i], 3.0 * (ros_pg[i] - fl[P.grp[i]] / CFG["stream_pos"].get(P.grp[i], CFG["stream"]))) for i in ok}
        cands[t] = sorted(ok, key=lambda i: -score[i])[:CFG["cand"]]

    def raw(A, B_, give, get):
        ra = [i for i in team_rows[A] if i not in give] + list(get)
        rb = [i for i in team_rows[B_] if i not in get] + list(give)
        return E.value(ra, WT[A]) - raw0[A], E.value(rb, WT[B_]) - raw0[B_]

    def evaluate(A, B_, give, get, detail=False):
        """A gives `give` to B_, receives `get`. Returns gains (weighted ROS points) and drop/add info."""
        ra = [i for i in team_rows[A] if i not in give] + list(get)
        rb = [i for i in team_rows[B_] if i not in get] + list(give)
        ra, da, aa = E.normalize(ra, WT[A], protect=set(get), drop_pool=droppool[A])
        rb, db, ab = E.normalize(rb, WT[B_], protect=set(give), drop_pool=droppool[B_])
        ga, gb = E.value(ra, WT[A]) - base[A], E.value(rb, WT[B_]) - base[B_]
        if detail:
            return ga, gb, dict(ra=ra, rb=rb, da=da, db=db, aa=aa, ab=ab)
        return ga, gb

    pairs = [(me, t) for t in team_rows if t != me]
    if a.all_pairs:
        pairs += [(x, y) for x, y in itertools.combinations(sorted(team_rows), 2) if me not in (x, y)]
    res = []
    t1 = time.time()
    raw0 = {t: E.value(r, WT[t]) for t, r in team_rows.items()}
    n_eval = 0
    for A, B_ in pairs:
        k = CFG["cand"] if me in (A, B_) else CFG["cand"] - 2
        ca, cb = cands[A][:k], cands[B_][:k]
        sizes = [(1, 1), (2, 1), (1, 2), (2, 2)]
        for na, nb in sizes:
            for give in itertools.combinations(ca, na):
                for get in itertools.combinations(cb, nb):
                    # cheap pre-screen without roster fill/drop (fill/drop moves values by a few points at most)
                    ra_, rb_ = raw(A, B_, give, get)
                    if min(ra_, rb_) < -4.0:
                        continue
                    n_eval += 1
                    ga, gb = evaluate(A, B_, give, get)
                    if ga > 0 and gb > 0:
                        res.append((A, B_, give, get, ga, gb))
    print(f"  searched {len(pairs)} pairs in {time.time() - t1:.0f}s ({n_eval} full evals), {len(res)} trades with both sides gaining")

    df = pd.DataFrame(res, columns=["A", "B", "give", "get", "gain_a", "gain_b"])
    df["min_gain"] = df[["gain_a", "gain_b"]].min(1)
    df["balance"] = df.min_gain / df[["gain_a", "gain_b"]].max(1)
    print("  balance distribution of win-win trades (min/max):",
          df.balance.quantile([.25, .5, .75, .9]).round(2).to_dict(),
          "| share with min gain >= 3:", round((df.min_gain >= CFG["min_gain"]).mean(), 2))
    keep = df[(df.balance >= CFG["min_ratio"]) & (df.min_gain >= CFG["min_gain"])].copy()
    keep = keep.sort_values("min_gain", ascending=False)
    # dedupe: drop a bigger trade if a sub-trade between the same teams already gets >= 90% of its min gain
    kept, seen = [], {}
    for r in keep.itertuples():
        key = (r.A, r.B)
        sub_best = 0.0
        for g2 in [r.give] + [c for k in range(1, len(r.give)) for c in itertools.combinations(r.give, k)]:
            for h2 in [r.get] + [c for k in range(1, len(r.get)) for c in itertools.combinations(r.get, k)]:
                if (g2, h2) != (r.give, r.get):
                    sub_best = max(sub_best, seen.get((key, g2, h2), 0.0))
        seen[(key, r.give, r.get)] = r.min_gain
        if sub_best >= 0.9 * r.min_gain:
            continue
        kept.append(r)
    keep = pd.DataFrame(kept).drop(columns="Index") if kept else keep.iloc[:0]
    print(f"  {len(keep)} trades pass balance >= {CFG['min_ratio']} and min gain >= {CFG['min_gain']} (after dedupe)")

    # perceived value
    vals, src = perceived_values(W)
    def pval(i):
        nm, g = norm_name(P.name[i]), P.grp[i]
        if g == "IDP":
            return vals.get((nm, "IDP"), (60.0, "IDP unranked"))
        for k in [(nm, g)]:
            if k in vals:
                return vals[k]
        if g == "K":
            return (150.0, "K")
        # fallback: season ppg relative scale
        ppg = P.season_ppg[i]
        return (max(0.0, (ppg if ppg == ppg else 0) - 5) * 250.0, f"no consensus; {ppg:.1f} ppg" if ppg == ppg else "unranked")

    def pkg(ix):
        v = sorted([pval(i)[0] for i in ix], reverse=True)
        return v[0] + 0.7 * sum(v[1:])

    def accept(give_b, get_b):
        """From the partner's view: what they give vs get on paper."""
        pg, pr = pkg(give_b), pkg(get_b)
        ratio = pg / max(pr, 1.0)
        if ratio > 1.30 and pg - pr > 600:
            return ratio, "Unlikely", "they give the bigger name on paper"
        if ratio > 1.12 and pg - pr > 300:
            return ratio, "Hard sell", "a bit more name value going their way out"
        if ratio < 0.80:
            return ratio, "Easy yes", "they get the bigger name; you pay on paper"
        return ratio, "Fair on paper", "consensus values are close"

    GN = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "K": "K", "IDP": "IDP"}
    nW = sum(1 for w in weeks)
    def side_reason(t, before_rows, after_rows, got, gave):
        _, d0 = E.weekly(np.array(before_rows), detail=True)
        _, d1 = E.weekly(np.array(after_rows), detail=True)
        delta = {g: float((d1[g] - d0[g]).mean()) for g in d0}
        net = float((E.weekly(np.array(after_rows)) - E.weekly(np.array(before_rows))).mean())
        last = lambda ix: "/".join(P.name[i].split()[1] if len(P.name[i].split()) > 1 else P.name[i] for i in ix)
        moves = sorted([(g, d) for g, d in delta.items() if abs(d) >= 0.3], key=lambda x: -x[1])
        txt = ", ".join(f"{g} {d:+.1f}" for g, d in moves) or "lineup about the same"
        txt += f" = net {net:+.1f}/wk"
        bench = [i for i in gave if E.start_share(before_rows, i) < 0.35]
        if bench:
            txt += f"; {last(bench)} {'was' if len(bench) == 1 else 'were'} mostly bench"
        return txt

    out = []
    for r in keep.itertuples():
        ga, gb, info = evaluate(r.A, r.B, r.give, r.get, detail=True)
        ratio, flag, why = accept(r.get, r.give)   # partner B gives r.get, receives r.give
        ra_reason = side_reason(r.A, E.normalize(team_rows[r.A], WT[r.A])[0], info["ra"], r.get, r.give)
        rb_reason = side_reason(r.B, E.normalize(team_rows[r.B], WT[r.B])[0], info["rb"], r.give, r.get)
        fmt = lambda ix: " + ".join(f"{P.name[i]} ({P.grp[i] if P.grp[i] != 'IDP' else P.ypos[i]}, {P.nfl[i]})" for i in ix)
        drops = [f"T{r.A} drops {P.name[i]}" for i in info["da"]] + [f"T{r.B} drops {P.name[i]}" for i in info["db"]]
        adds = [f"T{r.A} adds FA {P.name[i]}" for i in info["aa"]] + [f"T{r.B} adds FA {P.name[i]}" for i in info["ab"]]
        na_ = "You" if r.A == me else names[r.A]
        reason = f"{na_}: {ra_reason}. {names[r.B]}: {rb_reason}."
        out.append(dict(team_a=r.A, team_a_name=names[r.A], team_b=r.B, team_b_name=names[r.B], kind=kind(r.give, r.get),
                        a_gives=fmt(r.give), a_gets=fmt(r.get), gain_a=round(ga, 1), gain_b=round(gb, 1),
                        gain_a_pw=round(ga / WT[r.A].sum(), 2), gain_b_pw=round(gb / WT[r.B].sum(), 2),
                        min_gain=round(min(ga, gb), 1), balance=round(min(ga, gb) / max(ga, gb), 2),
                        b_gives_value=round(pkg(r.get)), b_gets_value=round(pkg(r.give)), b_value_ratio=round(ratio, 2),
                        accept=flag, accept_note=why,
                        consensus_a_gives="; ".join(pval(i)[1] for i in r.give),
                        consensus_a_gets="; ".join(pval(i)[1] for i in r.get),
                        roster_moves="; ".join(drops + adds), reason=reason, mine=int(me in (r.A, r.B))))
    T = pd.DataFrame(out)
    if len(T):
        T = T.sort_values(["mine", "min_gain"], ascending=[False, False])
    T.to_csv(os.path.join(HERE, f"trades_week{W}.csv"), index=False)

    # sanity tests
    tests = selftest(E, P, team_rows, cands, evaluate, me, names)
    meta = dict(week=W, weeks=f"{weeks[0]}-{weeks[-1]}", sources=list(src.values()), cfg=CFG,
                playoff_odds={names[t]: round(p_po[t], 2) for t in p_po},
                weights_me=[round(x, 2) for x in WT[me]], n_winwin=int(len(df)), n_kept=int(len(T)), tests=tests,
                me=me, me_name=names[me])
    write_page_data(T, meta, W, names, p_po)
    print(f"  wrote trades_week{W}.csv ({len(T)} trades; {int(T.mine.sum()) if len(T) else 0} involve team {me}) in {time.time() - t0:.0f}s")
    if len(T):
        mine = T[T.mine == 1].head(8)
        for r in mine.itertuples():
            you_get = r.a_gets if r.team_a == me else r.a_gives
            you_give = r.a_gives if r.team_a == me else r.a_gets
            g_me, g_them = (r.gain_a, r.gain_b) if r.team_a == me else (r.gain_b, r.gain_a)
            other = r.team_b_name if r.team_a == me else r.team_a_name
            print(f"  [{other}] get {you_get} | give {you_give} | you +{g_me} / them +{g_them} | {r.accept}\n      {r.reason}")


def selftest(E, P, team_rows, cands, evaluate, me, names):
    """1) star-for-scrub must be rejected; 2) a surplus-for-need swap must score as mutual."""
    out = []
    WTd = None
    # 1) my best player for another team's worst rostered non-K player
    best_me = max(cands[me], key=lambda i: E.PTS[i].sum())
    other = [t for t in team_rows if t != me][0]
    scrub = min([i for i in team_rows[other] if P.grp[i] != "K"], key=lambda i: E.PTS[i].sum())
    ga, gb = evaluate(me, other, (best_me,), (scrub,))
    ok1 = not (ga > 0 and gb > 0 and min(ga, gb) / max(ga, gb) >= CFG["min_ratio"])
    out.append(dict(test="star-for-scrub rejected", trade=f"T{me} gives {P.name[best_me]} for {P.name[scrub]} (T{other})",
                    gain_me=round(ga, 1), gain_them=round(gb, 1), passed=bool(ok1)))
    # 2) synthetic surplus-for-need: team X with 5 good RBs, 1 WR vs team Y with 5 good WRs, 1 RB; swap RB4 for WR4
    rb = [i for i in np.argsort(-E.PTS.sum(1)) if P.grp[i] == "RB"][:12]
    wr = [i for i in np.argsort(-E.PTS.sum(1)) if P.grp[i] == "WR"][:12]
    core = lambda t: [i for i in team_rows[t] if P.grp[i] in ("QB", "TE", "K", "IDP")]
    tX = core(1)[:7] + rb[0:8:2] + [rb[8]] + [wr[11]]          # RB-rich, WR-poor
    tY = core(2)[:7] + wr[0:8:2] + [wr[8]] + [rb[11]]          # WR-rich, RB-poor
    w = np.ones(len(E.weeks))
    vX0, vY0 = E.value(tX, w), E.value(tY, w)
    gx_rb, gy_wr = rb[6], wr[6]
    tX1 = [i for i in tX if i != gx_rb] + [gy_wr]; tY1 = [i for i in tY if i != gy_wr] + [gx_rb]
    dX, dY = E.value(tX1, w) - vX0, E.value(tY1, w) - vY0
    ok2 = dX > 0 and dY > 0 and min(dX, dY) / max(dX, dY) >= CFG["min_ratio"]
    out.append(dict(test="surplus-for-need swap is mutual", trade=f"RB-rich team gives {P.name[gx_rb]} for {P.name[gy_wr]}",
                    gain_me=round(dX, 1), gain_them=round(dY, 1), passed=bool(ok2)))
    for t in out:
        print(f"  selftest {'PASS' if t['passed'] else 'FAIL'}: {t['test']}: {t['trade']} -> {t['gain_me']:+} / {t['gain_them']:+}")
    return out


def write_page_data(T, meta, W, names, p_po):
    me = meta["me"]
    rows = []
    for r in T.itertuples():
        mine = r.team_a == me or r.team_b == me
        if mine:
            flip = r.team_b == me
            you_get, you_give = (r.a_gives, r.a_gets) if flip else (r.a_gets, r.a_gives)
            g_me, g_them = (r.gain_b, r.gain_a) if flip else (r.gain_a, r.gain_b)
            partner = r.team_a_name if flip else r.team_b_name
            pid = r.team_a if flip else r.team_b
        else:
            you_get, you_give, g_me, g_them = r.a_gets, r.a_gives, r.gain_a, r.gain_b
            partner, pid = r.team_b_name, r.team_b
        rows.append(dict(mine=bool(mine), a=r.team_a_name if not mine else meta["me_name"], aid=int(r.team_a if not mine else me),
                         b=partner, bid=int(pid), kind=r.kind, get=you_get, give=you_give, ga=float(g_me), gb=float(g_them),
                         bal=float(r.balance), minG=float(r.min_gain), accept=r.accept, note=r.accept_note,
                         ratio=float(r.b_value_ratio), moves=r.roster_moves or "", reason=r.reason))
    data = dict(week=W, weeks=meta["weeks"], me=meta["me_name"], sources=meta["sources"], minRatio=CFG["min_ratio"],
                minGain=CFG["min_gain"], nWinWin=meta["n_winwin"], nKept=meta["n_kept"],
                odds=[dict(team=k, p=v) for k, v in sorted(meta["playoff_odds"].items(), key=lambda x: -x[1])],
                tests=meta["tests"], rows=rows)
    _j = lambda o: json.dumps(o, separators=(",", ":"), ensure_ascii=False)
    head = _j({k: v for k, v in data.items() if k != "rows"})[:-1]
    body = ",\n".join(_j(r) for r in data["rows"])
    open(os.path.join(HERE, f"page_trades_week{W}.txt"), "w").write(f"const TRADES: TradeData = {head},\n\"rows\":[\n{body}\n]}};\n")


if __name__ == "__main__":
    main()
