"""Join ratings_week<N>.csv to the Yahoo available-player lists and rank streamers for the two IDP slots.

Usage: python streamers.py --week 8 [--league yahoo_league_week8.md]
LB slot = Yahoo positions containing LB (incl. LB,DE edges); D slot = anyone (DL/DE included).
Two lists per slot:
  safe = by injury-adjusted mean (rounded to 0.25), tiebreak simulated floor (P10), then median weekly points
  boom = by P(>=10 pts) (the boom metric that beat a position base rate out of sample), tiebreak P90
The Monte Carlo is re-run here so Yahoo Q/D tags (no NFL report yet) lower play probability, floor and boom odds.
"""
import argparse, os, re
import pandas as pd
import warnings; warnings.filterwarnings("ignore")
import idp_ratings as M
import boom
from idp_ratings import norm_name

YAHOO_TEAM = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS"}
TAGS = {"Q", "D", "O", "IR", "SUSP", "PUP", "NA"}
# Applied only when the model itself has no injury report for the player (week-8 reports are mostly not out yet).
TAG_MULT = {"Q": 0.85, "D": 0.25, "O": 0.0, "IR": 0.0, "SUSP": 0.0, "PUP": 0.0, "NA": 0.0}
STARTERS = {"D": ("Quinnen Williams", "DAL"), "LB": ("Andrew Van Ginkel", "MIN")}


def parse_league(path):
    rows = []
    for line in open(path):
        m = re.match(r"^(DL|LB|DB): (.*)$", line.strip())
        if not m:
            continue
        body = re.sub(r"\(plus .*?\)", "", m.group(2)).rstrip(". ")
        for item in body.split(";"):
            # week-9+ format: Name Team POS vs/@:opp [inj:TAG] [W [(date)]]
            m9 = re.match(r"^(.*?) (\S+) ([A-Z,]+) vs/@:(.*?)(?: inj:(\S+))?(?: (W)(?: \(.*?\))?)?$", item.strip().rstrip("."))
            if m9:
                name, team, ypos, opp, tag, w = m9.groups()
                team = team.upper()
                rows.append(dict(player_y=name, team_y=team, team=YAHOO_TEAM.get(team, team), yahoo_pos=ypos,
                                 waiver="W" if w else "FA", yahoo_tag=tag or "", list=m.group(1), opp_y=opp))
                continue
            toks = item.strip().rstrip(".").split()
            if not toks:
                continue
            w = toks[-1] == "W"
            toks = toks[:-1] if w else toks
            tag = toks[-1] if toks[-1] in TAGS else ""
            toks = toks[:-1] if tag else toks
            # list header decides position when Yahoo positions are omitted (LB/DB lists)
            if re.fullmatch(r"[A-Z,]+", toks[-1]) and "," in toks[-1] or toks[-1] in {"DE", "DT", "DL"}:
                ypos, toks = toks[-1], toks[:-1]
            else:
                ypos = {"LB": "LB", "DB": "DB", "DL": "DL"}[m.group(1)]
            team, name = toks[-1], " ".join(toks[:-1])
            rows.append(dict(player_y=name, team_y=team, team=YAHOO_TEAM.get(team, team), yahoo_pos=ypos,
                             waiver="W (until Oct 31)" if w else "FA", yahoo_tag=tag, list=m.group(1)))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=8)
    ap.add_argument("--league", default=None)
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    R = pd.read_csv(os.path.join(here, f"ratings_week{a.week}.csv"))
    L = parse_league(a.league or os.path.join(here, f"yahoo_league_week{a.week}.md"))
    R["k"] = R.player.map(norm_name) + "|" + R.team
    L["k"] = L.player_y.map(norm_name) + "|" + L.team
    # fallback for nickname/initial variants (Josh/Joshua, Cam/Camryn, C./C.J.): last name + team + first initial, unique only
    def lk(n):
        w = norm_name(n).split()
        return f"{w[-1]}|{w[0][0]}" if w else ""
    R["k2"] = R.player.map(lk) + "|" + R.team
    uniq = R.drop_duplicates("k2", keep=False).set_index("k2").k
    miss = ~L.k.isin(R.k)
    L.loc[miss, "k"] = (L.loc[miss, "player_y"].map(lk) + "|" + L.loc[miss, "team"]).map(uniq).fillna(L.loc[miss, "k"])
    J = L.merge(R.drop(columns="k2"), on=["k", "team"], how="left")
    unmatched = J[J.proj_pts.isna()]
    J = J.dropna(subset=["proj_pts"]).copy()

    def adj(df):
        no_rep = df.inj_report.isna() | (df.inj_report.astype(str).str.strip() == "")
        mult = pd.to_numeric(df.yahoo_tag.astype(object).map(TAG_MULT), errors="coerce").astype(float).fillna(1.0).where(no_rep, 1.0)
        return (df.proj_pts * mult).round(2)
    J["proj_adj"] = adj(J)

    # re-simulate with Yahoo tag applied (play probability = proj_adj / proj_raw)
    D = M.load_data(M.nfl.get_current_season())
    T = M.project(D, a.week)
    st_ids = {R[R.k == norm_name(nm) + "|" + tm].gsis_id.iloc[0]: ("Q" if nm == "David Bailey" else "") for nm, tm in STARTERS.values()}
    adjmap = dict(zip(J.gsis_id, J.proj_adj))
    for gid, tag in st_ids.items():
        r = R[R.gsis_id == gid].iloc[0]
        no_rep = pd.isna(r.inj_report) or str(r.inj_report).strip() == ""
        adjmap[gid] = round(r.proj_pts * (TAG_MULT.get(tag, 1) if no_rep and tag else 1), 2)
    T = T[T.gsis_id.isin(adjmap)].copy()
    T["proj_pts"] = T.gsis_id.map(adjmap)
    B = boom.simulate(T, D, a.week).set_index("gsis_id")
    simc = ["sim_mean", "sim_median", "floor_p10", "p90", "p_ge10", "p_ge12", "p_sack", "p_takeaway"]
    J = J.drop(columns=[c for c in simc if c in J]).join(B[simc], on="gsis_id")

    # starters (Yahoo tags from the league file: Bailey Q)
    st = {}
    for slot, (nm, tm) in STARTERS.items():
        r = R[R.k == norm_name(nm) + "|" + tm].iloc[0]
        tag = "Q" if nm == "David Bailey" else ""
        no_rep = pd.isna(r.inj_report) or str(r.inj_report).strip() == ""
        st[slot] = dict(name=nm, proj=r.proj_pts, proj_adj=adjmap[r.gsis_id], matchup=r.matchup, tag=tag,
                        **{c: B.loc[r.gsis_id, c] for c in simc}, row=r)

    out = []
    J["safe_key"] = (J.proj_adj * 4).round() / 4
    for slot, pool in [("LB", J[J.yahoo_pos.str.contains("LB")]), ("D", J)]:
        pool = pool.drop_duplicates("k")
        lists = {"safe": pool.sort_values(["safe_key", "floor_p10", "median_ppg"], ascending=False),
                 "boom": pool.sort_values(["p_ge10", "p90", "p_ge12"], ascending=False)}
        s = st[slot]
        for lt, srt in lists.items():
            top = srt.head(15).copy()
            top.insert(0, "list_type", lt)
            top.insert(0, "slot", slot)
            top["slot_rank"] = range(1, len(top) + 1)
            top["vs_starter"] = s["name"]
            top["starter_proj"] = s["proj"]
            top["starter_proj_adj"] = s["proj_adj"]
            top["starter_p90"] = s["p90"]
            top["starter_p_ge10"] = s["p_ge10"]
            top["starter_p_ge12"] = s["p_ge12"]
            top["delta_vs_starter"] = (top.proj_adj - s["proj_adj"]).round(2)
            out.append(top)
        # starter row for comparison
        r = s["row"].copy()
        srow = pd.DataFrame([{**r.to_dict(), "slot": slot, "list_type": "starter", "slot_rank": 0, "waiver": "rostered",
                              "yahoo_tag": s["tag"], "yahoo_pos": "", "proj_adj": s["proj_adj"], "vs_starter": s["name"],
                              "starter_proj": s["proj"], "starter_proj_adj": s["proj_adj"], "delta_vs_starter": 0.0,
                              **{c: s[c] for c in simc}}])
        out.append(srow)
    O = pd.concat(out, ignore_index=True)
    O["mean"] = O.proj_adj
    cols = ["slot", "list_type", "slot_rank", "player", "team", "yahoo_pos", "role", "matchup", "gameday", "waiver",
            "yahoo_tag", "proj_pts", "proj_adj", "mean", "sim_median", "floor_p10", "p90", "p_ge10", "p_ge12", "p_sack",
            "p_takeaway", "median_ppg", "games_ge6", "cv_pts", "ppg_ex_best", "best_game_pts", "rating_overall",
            "vs_starter", "starter_proj", "starter_proj_adj", "starter_p90", "starter_p_ge10", "starter_p_ge12",
            "delta_vs_starter", "season_ppg", "recent_ppg", "proj_snap_pct", "ol_matchup", "flags", "reason"]
    for c in ["sim_median", "floor_p10", "p90", "p_ge10", "p_ge12", "p_sack", "p_takeaway", "cv_pts", "ppg_ex_best"]:
        O[c] = O[c].astype(float).round(3)
    O[cols].to_csv(os.path.join(here, f"streamers_week{a.week}.csv"), index=False)
    BS = O[O.list_type.isin(["boom", "starter"])][["slot", "list_type", "slot_rank", "player", "team", "yahoo_pos", "role",
          "matchup", "waiver", "yahoo_tag", "mean", "sim_median", "floor_p10", "p90", "p_ge10", "p_ge12", "p_sack",
          "p_takeaway", "ol_matchup"]]
    BS.to_csv(os.path.join(here, f"streamers_boom_week{a.week}.csv"), index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
    show = ["slot_rank", "player", "team", "yahoo_pos", "role", "matchup", "waiver", "yahoo_tag", "mean", "floor_p10",
            "p90", "p_ge10", "p_ge12", "median_ppg", "games_ge6"]
    for slot in ["LB", "D"]:
        s = st[slot]
        print(f"\n=== {slot} slot: starter {s['name']} {s['matchup']} mean {s['proj_adj']} P10 {s['floor_p10']} P90 {s['p90']} "
              f"P10+ {s['p_ge10']:.1%} P12+ {s['p_ge12']:.1%}{' (Yahoo Q)' if s['tag'] else ''} ===")
        for lt in ["safe", "boom"]:
            print(f"-- {lt} --")
            print(O[(O.slot == slot) & (O.list_type == lt)][show].head(10).round(3).to_string(index=False))
    print(f"\nParsed {len(L)} Yahoo-listed players, matched {len(J)}; unmatched: {len(unmatched)}")
    print(unmatched[["player_y", "team_y", "yahoo_pos", "yahoo_tag"]].to_string(index=False))


if __name__ == "__main__":
    main()
