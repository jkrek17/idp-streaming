"""WR2-upgrade trade search for one team (analysis only; never touches Yahoo).

Same engine, balance rule and market check as trade_finder.py, restricted to trades where
  * locked players (default Brock Bowers) are never sent out,
  * soft-locked players (default Hunter Henry) may be sent but every such trade is flagged,
  * you receive a WR projecting >= --min-wr pts/wk ROS (non-bye average) and above your current WR2,
  * your lineup gain comes mainly from the WR slots (WR delta is your largest positive slot change and >= 50% of the positives).
Usage: TF_DEV=1 .venv/bin/python wr2_finder.py --week 8 [--team 4] [--lock "Brock Bowers"] [--soft "Hunter Henry"]
Outputs: trades_week8_wr2.csv (all rows + shortlist flag) and merges rows tagged preset=wr2_no_bowers into trades_week8.csv.\nRe-run trade_finder.py first if you rerun both: it rewrites trades_week8.csv without the preset rows.
"""
import argparse, itertools, os, pickle, time
import numpy as np, pandas as pd
import trade_finder as TF
from trade_finder import CFG, Engine, playoff_odds, week_weights, perceived_values, kind, norm_name

HERE = TF.HERE


def nonbye_avg(row):
    z = (row == 0).sum()
    n = len(row) - (1 if z >= 1 else 0)
    return float(row.sum() / max(n, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=8)
    ap.add_argument("--team", type=int, default=4)
    ap.add_argument("--lock", default="Brock Bowers,CeeDee Lamb")
    ap.add_argument("--soft", default="Hunter Henry")
    ap.add_argument("--min-wr", type=float, default=9.5)
    ap.add_argument("--max-give", type=int, default=3)
    ap.add_argument("--preset", default="wr2_no_bowers")
    a = ap.parse_args()
    W, me = a.week, a.team
    weeks = list(range(W, CFG["last_week"] + 1))
    t0 = time.time()
    cache = "/tmp/tfP.pkl"
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(os.path.join(HERE, f"league_rosters_week{W}.json")):
        P, L = pickle.load(open(cache, "rb"))
    else:
        import dev_cache; D, B = dev_cache.get()
        P, L = TF.load_players(D, B, W, weeks, me)
        pickle.dump((P, L), open(cache, "wb"))
    E = Engine(P, weeks, W)
    names = {t["team_id"]: t["name"] for t in L["teams"]}
    team_rows = {t["team_id"]: list(np.where(P.owner.values == t["team_id"])[0]) for t in L["teams"]}
    p_po, _ = playoff_odds(E, L, team_rows, W, weeks)
    WT = {t: week_weights(weeks, W, p_po[t]) for t in team_rows}
    base = {t: E.value(E.normalize(r, WT[t])[0], WT[t]) for t, r in team_rows.items()}
    marg = {}
    for t, r in team_rows.items():
        v0 = E.value(r, WT[t])
        for i in r:
            marg[i] = v0 - E.value([j for j in r if j != i], WT[t])
    droppool = {t: set(sorted(r, key=lambda i: marg[i])[:6]) for t, r in team_rows.items()}
    ros = np.array([nonbye_avg(E.PTS[i]) for i in range(len(P))])
    N = lambda i: P.name[i]
    lock = {x.strip() for x in a.lock.split(",") if x.strip()}
    soft = {x.strip() for x in a.soft.split(",") if x.strip()}

    mine = team_rows[me]
    my_wr = sorted([i for i in mine if P.grp[i] == "WR"], key=lambda i: -ros[i])
    wr2 = my_wr[1]
    print(f"  your WR1 {N(my_wr[0])} {ros[my_wr[0]]:.1f}/wk, WR2 {N(wr2)} {ros[wr2]:.1f}/wk; bar = max({a.min_wr}, WR2 + 1)")
    bar = max(a.min_wr, ros[wr2] + 1.0)
    give_pool = [i for i in mine if N(i) not in lock and P.grp[i] != "K" and E.PTS[i].sum() > 0]
    print("  give pool:", ", ".join(f"{N(i)}{' (flag)' if N(i) in soft else ''}" for i in give_pool))

    # partner side: target WRs + their tradeable pieces (top by marginal/ros) as add-ons
    targets, extras = {}, {}
    for t, r in team_rows.items():
        if t == me:
            continue
        targets[t] = [i for i in r if P.grp[i] == "WR" and ros[i] >= bar]
        ok = [i for i in r if P.grp[i] != "K" and E.PTS[i].sum() > 0]
        fl = {g: E.f[g].mean() for g in TF.GROUPS}
        sc = {i: max(marg[i], 3.0 * (ros[i] - fl[P.grp[i]] / CFG["stream_pos"].get(P.grp[i], CFG["stream"]))) for i in ok}
        extras[t] = sorted(ok, key=lambda i: -sc[i])[:9]
    print("  WR targets >= %.1f/wk: " % bar + "; ".join(f"{N(i)} ({names[t]}) {ros[i]:.1f}" for t in targets for i in targets[t]))

    raw0 = {t: E.value(r, WT[t]) for t, r in team_rows.items()}
    def raw(B_, give, get):
        ra = [i for i in mine if i not in give] + list(get)
        rb = [i for i in team_rows[B_] if i not in get] + list(give)
        return E.value(ra, WT[me]) - raw0[me], E.value(rb, WT[B_]) - raw0[B_]
    def evaluate(B_, give, get, detail=False):
        ra = [i for i in mine if i not in give] + list(get)
        rb = [i for i in team_rows[B_] if i not in get] + list(give)
        ra, da, aa = E.normalize(ra, WT[me], protect=set(get), drop_pool=droppool[me])
        rb, db, ab = E.normalize(rb, WT[B_], protect=set(give), drop_pool=droppool[B_])
        ga, gb = E.value(ra, WT[me]) - base[me], E.value(rb, WT[B_]) - base[B_]
        return (ga, gb, dict(ra=ra, rb=rb, da=da, db=db, aa=aa, ab=ab)) if detail else (ga, gb)
    my_before = E.normalize(mine, WT[me])[0]
    def deltas(after):
        _, d0 = E.weekly(np.array(my_before), detail=True)
        _, d1 = E.weekly(np.array(after), detail=True)
        return {g: float(((d1[g] - d0[g]) * WT[me]).sum()) for g in d0}

    res, n_eval = [], 0
    t1 = time.time()
    for t in targets:
        if not targets[t]:
            continue
        gets = set()
        for w in targets[t]:
            gets.add((w,))
            for x in extras[t]:
                if x != w:
                    gets.add(tuple(sorted((w, x))))
            for w2 in targets[t]:
                if w2 != w:
                    gets.add(tuple(sorted((w, w2))))
        for ng in range(1, a.max_give + 1):
            for give in itertools.combinations(give_pool, ng):
                for get in gets:
                    ra_, rb_ = raw(t, give, get)
                    if min(ra_, rb_) < -4.0:
                        continue
                    n_eval += 1
                    ga, gb = evaluate(t, give, get)
                    if ga > 0 and gb > 0:
                        res.append((t, give, get, ga, gb))
    print(f"  {n_eval} full evals in {time.time() - t1:.0f}s; {len(res)} win-win")
    df = pd.DataFrame(res, columns=["B", "give", "get", "ga", "gb"])
    df["min_gain"] = df[["ga", "gb"]].min(1)
    df["balance"] = df.min_gain / df[["ga", "gb"]].max(1)
    keep = df[(df.balance >= CFG["min_ratio"]) & (df.min_gain >= CFG["min_gain"])].sort_values("min_gain", ascending=False)

    # WR-led filter
    rows = []
    for r in keep.itertuples():
        ga, gb, info = evaluate(r.B, r.give, r.get, detail=True)
        d = deltas(info["ra"])
        pos = {g: v for g, v in d.items() if v > 0.05}
        wr_led = d["WR"] > 0 and d["WR"] >= max(pos.values()) - 1e-9 and d["WR"] >= 0.5 * sum(pos.values())
        if wr_led:
            rows.append((r, ga, gb, info, d))
    print(f"  {len(keep)} pass balance; {len(rows)} WR-led")

    # dedupe: drop a bigger package if a sub-package with the same partner keeps >= 90% of the min gain
    seen, kept = {}, []
    for r, ga, gb, info, d in rows:
        sb = 0.0
        for g2 in [c for k in range(1, len(r.give) + 1) for c in itertools.combinations(r.give, k)]:
            for h2 in [c for k in range(1, len(r.get) + 1) for c in itertools.combinations(r.get, k)]:
                if (g2, h2) != (r.give, r.get):
                    sb = max(sb, seen.get((r.B, tuple(sorted(g2)), tuple(sorted(h2))), 0.0))
        seen[(r.B, tuple(sorted(r.give)), tuple(sorted(r.get)))] = r.min_gain
        if sb < 0.9 * r.min_gain:
            kept.append((r, ga, gb, info, d))

    vals, src = perceived_values(W)
    def pval(i):
        nm, g = norm_name(P.name[i]), P.grp[i]
        if g == "IDP":
            return vals.get((nm, "IDP"), (60.0, "IDP unranked"))
        if (nm, g) in vals:
            return vals[(nm, g)]
        ppg = P.season_ppg[i]
        return (max(0.0, (ppg if ppg == ppg else 0) - 5) * 250.0, "no consensus")
    def pkg(ix):
        v = sorted([pval(i)[0] for i in ix], reverse=True)
        return v[0] + 0.7 * sum(v[1:])
    def accept(give_b, get_b):
        pg, pr = pkg(give_b), pkg(get_b)
        ratio = pg / max(pr, 1.0)
        if ratio > 1.30 and pg - pr > 600:
            return ratio, "Unlikely", "they give the bigger name on paper"
        if ratio > 1.12 and pg - pr > 300:
            return ratio, "Hard sell", "a bit more name value going their way out"
        if ratio < 0.80:
            return ratio, "Easy yes", "they get the bigger name; you pay on paper"
        return ratio, "Fair on paper", "consensus values are close"

    fmt = lambda ix: " + ".join(f"{P.name[i]} ({P.grp[i] if P.grp[i] != 'IDP' else P.ypos[i]}, {P.nfl[i]})" for i in ix)
    out = []
    for r, ga, gb, info, d in kept:
        ratio, flag, why = accept(r.get, r.give)
        wr_in = [i for i in r.get if P.grp[i] == "WR"]
        wr_txt = ", ".join(f"{N(i)} {ros[i]:.1f}/wk vs {N(wr2)} {ros[wr2]:.1f}" for i in wr_in)
        _, d0 = E.weekly(np.array(my_before), detail=True); _, d1 = E.weekly(np.array(info["ra"]), detail=True)
        pw = {g: float((d1[g] - d0[g]).mean()) for g in d0}
        _, e0 = E.weekly(np.array(E.normalize(team_rows[r.B], WT[r.B])[0]), detail=True); _, e1 = E.weekly(np.array(info["rb"]), detail=True)
        pwb = {g: float((e1[g] - e0[g]).mean()) for g in e0}
        mv = lambda p: ", ".join(f"{g} {v:+.1f}" for g, v in sorted(p.items(), key=lambda x: -x[1]) if abs(v) >= 0.3) or "about the same"
        henry = [N(i) for i in r.give if N(i) in soft]
        moves = [f"You drop {N(i)}" for i in info["da"]] + [f"{names[r.B]} drops {N(i)}" for i in info["db"]] + \
                [f"You add FA {N(i)}" for i in info["aa"]] + [f"{names[r.B]} adds FA {N(i)}" for i in info["ab"]]
        reason = f"You: {mv(pw)}/wk ({wr_txt}). {names[r.B]}: {mv(pwb)}/wk."
        if henry:
            reason += f" FLAG: includes {', '.join(henry)} (soft-locked)."
        out.append(dict(team_a=me, team_a_name=names[me], team_b=r.B, team_b_name=names[r.B], kind=kind(r.give, r.get),
                        a_gives=fmt(r.give), a_gets=fmt(r.get), gain_a=round(ga, 1), gain_b=round(gb, 1),
                        gain_a_pw=round(ga / WT[me].sum(), 2), gain_b_pw=round(gb / WT[r.B].sum(), 2),
                        min_gain=round(min(ga, gb), 1), balance=round(min(ga, gb) / max(ga, gb), 2),
                        b_gives_value=round(pkg(r.get)), b_gets_value=round(pkg(r.give)), b_value_ratio=round(ratio, 2),
                        accept=flag, accept_note=why,
                        consensus_a_gives="; ".join(pval(i)[1] for i in r.give),
                        consensus_a_gets="; ".join(pval(i)[1] for i in r.get),
                        roster_moves="; ".join(moves), reason=reason, mine=1, preset=a.preset,
                        wr_in=", ".join(N(i) for i in wr_in), wr_in_ros=round(max(ros[i] for i in wr_in), 1),
                        wr_slot_gain=round(d["WR"], 1), henry_flag=int(bool(henry))))
    T = pd.DataFrame(out).sort_values("min_gain", ascending=False).reset_index(drop=True)
    # page shortlist: one row per (partner, package received); the fewest pieces given that keeps >= 75% of the best
    # smaller gain; a Henry version only when it beats the best non-Henry version by more than 1.5
    T["n_give"] = T.a_gives.str.count(r" \+ ") + 1
    reps = []
    for _, x in T.groupby(["team_b", "a_gets"]):
        for h in (0, 1):
            y = x[x.henry_flag == h]
            if len(y):
                reps.append(y[y.min_gain >= 0.75 * y.min_gain.max()].sort_values(["n_give", "min_gain"], ascending=[True, False]).index[0])
    short = []
    for i in reps:
        r = T.loc[i]
        alt = [j for j in reps if T.team_b[j] == r.team_b and T.a_gets[j] == r.a_gets and T.henry_flag[j] == 0]
        if r.henry_flag and alt and T.min_gain[alt].max() >= r.min_gain - 1.5:
            continue
        short.append(i)
    T["shortlist"] = T.index.isin(short).astype(int)
    T = T.drop(columns="n_give")
    T.to_csv(os.path.join(HERE, f"trades_week{W}_wr2.csv"), index=False)
    # merge into the main CSV, tagged (idempotent: replaces earlier rows with the same preset)
    mp = os.path.join(HERE, f"trades_week{W}.csv")
    if os.path.exists(mp):
        Mn = pd.read_csv(mp)
        if "preset" in Mn.columns:
            Mn = Mn[Mn.preset.fillna("") != a.preset]
        pd.concat([Mn, T], ignore_index=True).to_csv(mp, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    for r in T.itertuples():
        print(f"[{r.team_b_name}] give {r.a_gives} | get {r.a_gets} | you +{r.gain_a} / them +{r.gain_b} | {r.accept} ({r.b_value_ratio}) {'HENRY' if r.henry_flag else ''}\n    {r.reason} | {r.roster_moves}")
    print(f"  {len(T)} WR2 trades in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
