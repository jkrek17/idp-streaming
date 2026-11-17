"""Compact dashboard_data_weekN.json into one `const DATA = ...;` line for the Page."""
import json, sys
wk = sys.argv[1] if len(sys.argv) > 1 else "8"
d = json.load(open(f"dashboard_data_week{wk}.json"))
TOP = {"QB": 16, "RB": 24, "WR": 30, "TE": 14, "K": 10, "DL": 14, "LB": 22, "DB": 18}
FA_TOP = 6
keep = []
for pos, n in TOP.items():
    rows = sorted([p for p in d["players"] if p[2] == pos], key=lambda p: -(p[4] or 0))
    fa = [p for p in rows if p[16] in ("FA", "W")][:FA_TOP]
    sel = rows[:n] + [p for p in rows if p[16] == "mine"] + fa
    seen = set()
    for p in sel:
        k = (p[0], p[1])
        if k in seen: continue
        seen.add(k)
        r = list(p) + ([False] if len(p) == 18 else [])
        r[19 - 1] = bool(r[18])
        keep.append(r)
d["players"] = keep
def trim(x):
    if isinstance(x, float): return round(x, 2)
    if isinstance(x, list): return [trim(i) for i in x]
    if isinstance(x, dict): return {k: trim(v) for k, v in x.items()}
    return x
d = trim(d)
d.pop("cols", None)
d["waivers"] = d["waivers"][:32]
J = lambda x: json.dumps(x, separators=(",", ":"), ensure_ascii=True)
parts = []
for k, v in d.items():
    if isinstance(v, list) and v and not isinstance(v[0], str):
        parts.append(J(k) + ":[\n" + ",\n".join(J(i) for i in v) + "\n]")
    elif k == "lineup":
        parts.append(J(k) + ":{" + ",\n".join(J(m) + ":[\n" + ",\n".join(J(i) for i in v[m]) + "\n]" for m in v) + "}")
    else:
        parts.append(J(k) + ":" + J(v))
s = "{\n" + ",\n".join(parts) + "\n}"
open(f"page_data_week{wk}.txt", "w").write("const DATA: Data = " + s + ";\n")
print(len(keep), len(s))
