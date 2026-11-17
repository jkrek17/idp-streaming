#!/usr/bin/env python3
"""Weekly fantasy power-rankings graphic for Irene's Bush League.

Reads weekly_scores.csv (week,team,points,opponent), computes power/luck
through the latest week N, Monte Carlo playoff odds, weekly awards, and
writes /workspace/power_rankings_wkN.png.

Power = 1/3 all-play win% + 1/3 (H2H+median) win% + 1/3 min-max PF.
Luck  = actual wins - all-play expected wins  (shown to 1 decimal).

Awards strip (current week only):
  CSV-derived: highest team, bad beat, closest, blowout
  extras CSV:  highest player, survivor eliminated, highest defense
"""
from __future__ import annotations

import argparse
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_CSV = HERE / "weekly_scores.csv"
EXTRAS_CSV = HERE / "weekly_awards_extra.csv"
MANAGERS_CSV = HERE / "managers.csv"
OUT_DIR = Path("/workspace")
LEAGUE = "Irene's Bush League"
USER_TEAM = "Breeces Pieces"

REG_SEASON_WEEKS = 14
PLAYOFF_TEAMS = 6
N_SIMS = 12_000
RNG_SEED = 42


# --------------------------------------------------------------------------- IO
def load_scores(path: Path):
    rows = list(csv.DictReader(path.open()))
    pts = defaultdict(dict)
    opp = defaultdict(dict)
    for r in rows:
        w = int(r["week"])
        pts[w][r["team"]] = float(r["points"])
        opp[w][r["team"]] = r["opponent"]
    return pts, opp


def load_managers(path: Path = MANAGERS_CSV):
    """Return team->manager and manager->team from proven mapping file."""
    t2m, m2t = {}, {}
    if not path.exists():
        return t2m, m2t
    for r in csv.DictReader(path.open()):
        m, t = r["manager"].strip(), r["team"].strip()
        t2m[t] = m
        m2t[m] = t
    return t2m, m2t


def load_extras(path: Path = EXTRAS_CSV):
    """week -> award -> {team, detail, points}."""
    by = defaultdict(dict)
    if not path.exists():
        return by
    for r in csv.DictReader(path.open()):
        w = int(r["week"])
        pts = r["points"].strip()
        by[w][r["award"].strip()] = dict(
            team=r["team"].strip(),
            detail=r.get("detail", "").strip(),
            points=float(pts) if pts else None,
        )
    return by


def label_mgr_team(team: str, t2m: dict, maxlen_team: int = 28) -> str:
    """'Manager (Team)' when mapped, else just team. Prefer full names."""
    mgr = t2m.get(team)
    tshort = team if len(team) <= maxlen_team else team[: maxlen_team - 1] + "…"
    if mgr:
        return f"{mgr} ({tshort})"
    return tshort


def mgr_of(team: str, t2m: dict) -> str:
    return t2m.get(team) or team


def short_team(team: str, n: int = 26) -> str:
    return team if len(team) <= n else team[: n - 1] + "…"


# --------------------------------------------------------------------------- standings
def compute_standings(pts, opp, through_week: int):
    weeks = [w for w in sorted(pts) if w <= through_week]
    teams = sorted({t for w in weeks for t in pts[w]})
    S = {t: defaultdict(float) for t in teams}
    weekly = {t: [] for t in teams}

    for w in weeks:
        sc = pts[w]
        med = st.median(sc.values())
        for t, p in sc.items():
            o = sc[opp[w][t]]
            s = S[t]
            s["W"] += p > o
            s["L"] += p < o
            s["T"] += p == o
            s["PF"] += p
            s["G"] += 1
            weekly[t].append(p)
            for u, q in sc.items():
                if u != t:
                    s["aW"] += p > q
                    s["aL"] += p < q
                    s["aT"] += p == q
            s["mW"] += p > med
            s["mL"] += p < med
            s["mT"] += p == med

    pfs = [S[t]["PF"] for t in teams]
    lo, hi = min(pfs), max(pfs)
    out = []
    for t in teams:
        s = S[t]
        ap = (s["aW"] + 0.5 * s["aT"]) / (s["aW"] + s["aL"] + s["aT"])
        hm = (s["W"] + s["mW"] + 0.5 * (s["T"] + s["mT"])) / (2 * s["G"])
        pfn = (s["PF"] - lo) / (hi - lo) if hi > lo else 0.5
        luck = s["W"] + 0.5 * s["T"] - ap * s["G"]
        power = (ap + hm + pfn) / 3
        aw, al, at = int(s["aW"]), int(s["aL"]), int(s["aT"])
        allplay = f"{aw}-{al}" if at == 0 else f"{aw}-{al}-{at}"
        w_, l_, t_ = int(s["W"]), int(s["L"]), int(s["T"])
        record = f"{w_}-{l_}" if t_ == 0 else f"{w_}-{l_}-{t_}"
        out.append(
            dict(
                team=t,
                record=record,
                W=w_,
                L=l_,
                T=t_,
                allplay=allplay,
                allplay_pct=ap,
                PF=round(s["PF"], 2),
                luck=round(luck, 1),
                power=power,
                scores=weekly[t],
                mean=float(np.mean(weekly[t])),
                std=float(np.std(weekly[t], ddof=1)) if len(weekly[t]) > 1 else 20.0,
            )
        )
    out.sort(key=lambda r: -r["power"])
    for i, r in enumerate(out, 1):
        r["power_rank"] = i
    return out


def week_games(pts, opp, week: int):
    sc = pts[week]
    seen, games = set(), []
    for t, p in sc.items():
        o = opp[week][t]
        key = tuple(sorted([t, o]))
        if key in seen:
            continue
        seen.add(key)
        op = sc[o]
        winner = t if p > op else o
        loser = o if p > op else t
        games.append(
            dict(
                winner=winner,
                loser=loser,
                w_pts=max(p, op),
                l_pts=min(p, op),
                margin=abs(p - op),
            )
        )
    return games


def compute_awards(pts, opp, week: int, extras_by_week, t2m: dict):
    """Build the 7 weekly awards for `week`. Missing extras → pending."""
    sc = pts[week]
    games = week_games(pts, opp, week)
    flags = []  # sheet/CSV disagreement notes for stdout

    # Manager-first display: big value + manager name (no team names).

    # 1) Highest scoring team
    top_team = max(sc, key=sc.get)
    top_pts = sc[top_team]
    a_highest = dict(
        key="highest_team",
        title="HIGHEST TEAM",
        value=f"{top_pts:.1f}",
        manager=mgr_of(top_team, t2m),
        detail="",
        pending=False,
    )

    # 2) Highest scoring player (extras)
    ex = extras_by_week.get(week, {})
    hp = ex.get("highest_player")
    if hp and hp["team"]:
        a_player = dict(
            key="highest_player",
            title="TOP PLAYER",
            value=f"{hp['points']:.1f}",
            manager=mgr_of(hp["team"], t2m),
            detail=hp["detail"] or "",
            pending=False,
        )
    else:
        a_player = dict(
            key="highest_player", title="TOP PLAYER",
            value="", manager="", detail="", pending=True,
        )

    # 3) Weekly Bad Beat = highest score that lost
    bb_game = max(games, key=lambda g: g["l_pts"])
    a_badbeat = dict(
        key="bad_beat",
        title="BAD BEAT",
        value=f"{bb_game['l_pts']:.1f}",
        manager=mgr_of(bb_game["loser"], t2m),
        detail=f"lost to {mgr_of(bb_game['winner'], t2m)}",
        pending=False,
    )

    # 4) Survivor eliminated
    sev = ex.get("survivor_eliminated")
    if sev and sev["team"]:
        a_surv = dict(
            key="survivor",
            title="SURVIVOR OUT",
            value=f"{sev['points']:.2f}" if sev["points"] is not None else "",
            manager=mgr_of(sev["team"], t2m),
            detail="",
            pending=False,
        )
    else:
        a_surv = dict(
            key="survivor", title="SURVIVOR OUT",
            value="", manager="", detail="", pending=True,
        )

    # 5) Highest cumulative defense
    hd = ex.get("highest_defense")
    if hd and hd["team"]:
        a_def = dict(
            key="highest_defense",
            title="TOP DEFENSE",
            value=f"{hd['points']:.1f}",
            manager=mgr_of(hd["team"], t2m),
            detail="IDP",
            pending=False,
        )
    else:
        a_def = dict(
            key="highest_defense", title="TOP DEFENSE",
            value="", manager="", detail="", pending=True,
        )

    # 6) Closest game
    closest = min(games, key=lambda g: g["margin"])
    a_close = dict(
        key="closest",
        title="CLOSEST",
        value=f"+{closest['margin']:.1f}",
        manager=f"{mgr_of(closest['winner'], t2m)} over {mgr_of(closest['loser'], t2m)}",
        detail=f"{closest['w_pts']:.1f}–{closest['l_pts']:.1f}",
        pending=False,
    )

    # 7) Biggest blowout
    blow = max(games, key=lambda g: g["margin"])
    a_blow = dict(
        key="blowout",
        title="BLOWOUT",
        value=f"+{blow['margin']:.1f}",
        manager=f"{mgr_of(blow['winner'], t2m)} over {mgr_of(blow['loser'], t2m)}",
        detail=f"{blow['w_pts']:.1f}–{blow['l_pts']:.1f}",
        pending=False,
    )

    awards = [a_highest, a_player, a_badbeat, a_surv, a_def, a_close, a_blow]
    meta = dict(
        highest_team=(top_team, top_pts),
        bad_beat=(bb_game["loser"], bb_game["l_pts"]),
        closest=closest,
        blowout=blow,
        flags=flags,
    )
    return awards, meta


def playoff_odds(standings, weeks_played: int, n_sims=N_SIMS, seed=RNG_SEED):
    remaining = REG_SEASON_WEEKS - weeks_played
    teams = [r["team"] for r in standings]
    nt = len(teams)
    wins0 = np.array([r["W"] + 0.5 * r["T"] for r in standings], dtype=float)
    pf0 = np.array([r["PF"] for r in standings], dtype=float)
    means = np.array([r["mean"] for r in standings], dtype=float)
    stds = np.array([max(r["std"], 15.0) for r in standings], dtype=float)

    rng = np.random.default_rng(seed)
    made = np.zeros(nt)
    batch = 100
    assert n_sims % batch == 0
    for _ in range(n_sims // batch):
        wins = np.tile(wins0, (batch, 1))
        pf = np.tile(pf0, (batch, 1))
        for _w in range(remaining):
            order = np.argsort(rng.random((batch, nt)), axis=1)
            scores = means[None, :] + rng.normal(0, 1, (batch, nt)) * stds[None, :]
            pf += scores
            a = order[:, 0::2]
            b = order[:, 1::2]
            sa = np.take_along_axis(scores, a, 1)
            sb = np.take_along_axis(scores, b, 1)
            aw = sa > sb
            bw = sb > sa
            np.put_along_axis(wins, a, np.take_along_axis(wins, a, 1) + aw, 1)
            np.put_along_axis(wins, b, np.take_along_axis(wins, b, 1) + bw, 1)
        key = wins * 1e6 + pf
        top = np.argsort(-key, axis=1)[:, :PLAYOFF_TEAMS]
        for r in range(batch):
            made[top[r]] += 1
    return {teams[i]: made[i] / n_sims for i in range(nt)}


# --------------------------------------------------------------------------- themes
THEMES = {
    "dark": dict(
        BG="#0B1220", PANEL="#121A2B", PANEL2="#162033", RULE="#243049",
        TEXT="#E8EEF9", MUTED="#8B9BB8", ACCENT="#3B82F6", TITLE_ACCENT="#F5C542",
        GREEN="#22C55E", RED="#EF4444",
        HIGHLIGHT="#1A4A7A", HIGHLIGHT_EDGE="#60A5FA", USER_NAME="#F5C542",
        ROW_ALT="#0E1626", LUCK_ZERO="#3A4A66", LUCK_GUIDE="#1A2438",
        CARD_ACCENTS=["#3B82F6", "#F5C542", "#EF4444", "#22C55E", "#A78BFA", "#F97316", "#14B8A6"],
        PO_HIGH="#22C55E", PO_MID="#E8EEF9", PO_LOW="#8B9BB8",
    ),
    "editorial": dict(
        # sports-section print: cream, deep navy, one strong red accent
        BG="#F4EFE4", PANEL="#FFFDF8", PANEL2="#FFFDF8", RULE="#D6CBB6",
        TEXT="#0B1B33", MUTED="#5C6B7A", ACCENT="#9B1C2C", TITLE_ACCENT="#9B1C2C",
        GREEN="#1B7A4E", RED="#B42318",
        HIGHLIGHT="#F3E0E3", HIGHLIGHT_EDGE="#9B1C2C", USER_NAME="#9B1C2C",
        ROW_ALT="#F7F1E6", LUCK_ZERO="#C4B6A0", LUCK_GUIDE="#E8DFD0",
        CARD_ACCENTS=["#9B1C2C", "#0B1B33", "#9B1C2C", "#0B1B33", "#9B1C2C", "#0B1B33", "#9B1C2C"],
        PO_HIGH="#1B7A4E", PO_MID="#0B1B33", PO_LOW="#5C6B7A",
    ),
    "clean": dict(
        # modern SaaS dashboard: white, slate, blue/teal
        BG="#F5F7FA", PANEL="#FFFFFF", PANEL2="#FFFFFF", RULE="#E2E8F0",
        TEXT="#0F172A", MUTED="#64748B", ACCENT="#0D9488", TITLE_ACCENT="#0369A1",
        GREEN="#059669", RED="#DC2626",
        HIGHLIGHT="#E0F2FE", HIGHLIGHT_EDGE="#0284C7", USER_NAME="#0369A1",
        ROW_ALT="#F8FAFC", LUCK_ZERO="#CBD5E1", LUCK_GUIDE="#EEF2F7",
        CARD_ACCENTS=["#0284C7", "#0D9488", "#7C3AED", "#DC2626", "#D97706", "#059669", "#0369A1"],
        PO_HIGH="#059669", PO_MID="#0F172A", PO_LOW="#94A3B8",
    ),
    "field": dict(
        # football field: light turf, forest green, gold
        BG="#F3F6EF", PANEL="#FFFFFF", PANEL2="#FFFEF8", RULE="#D5DEC8",
        TEXT="#14261A", MUTED="#5B6B5A", ACCENT="#1B4332", TITLE_ACCENT="#B8860B",
        GREEN="#2D6A4F", RED="#C1121F",
        HIGHLIGHT="#E8F0DC", HIGHLIGHT_EDGE="#B8860B", USER_NAME="#1B4332",
        ROW_ALT="#F0F4E8", LUCK_ZERO="#B7C4A8", LUCK_GUIDE="#E4EBD8",
        CARD_ACCENTS=["#1B4332", "#B8860B", "#2D6A4F", "#C1121F", "#1B4332", "#B8860B", "#2D6A4F"],
        PO_HIGH="#2D6A4F", PO_MID="#14261A", PO_LOW="#7A8A74",
    ),
    "navy_gold": dict(
        # sleek modern cards: cream page, deep navy, matte gold accents
        BG="#F5F0E6", PANEL="#FFFCF7", PANEL2="#FFFCF7", RULE="#E2D9C8",
        TEXT="#14213D", MUTED="#6B7280", ACCENT="#B8975A", TITLE_ACCENT="#B8975A",
        GREEN="#3D7A5A", RED="#B54A3A",
        HIGHLIGHT="#F3EBD8", HIGHLIGHT_EDGE="#B8975A", USER_NAME="#14213D",
        ROW_ALT="#F8F4EC", LUCK_ZERO="#D4CBB8", LUCK_GUIDE="#EDE6D8",
        # award top accents alternate navy / matte gold
        CARD_ACCENTS=["#14213D", "#B8975A", "#14213D", "#B8975A", "#14213D", "#B8975A", "#14213D"],
        PO_HIGH="#3D7A5A", PO_MID="#14213D", PO_LOW="#9CA3AF",
        # navy_gold extras
        HEADER_BG="#14213D", HEADER_TEXT="#F5F0E6", HEADER_SUB="#B8975A",
        HEADER_MUTED="#C5C9D3", TABLE_HEADER_BG="#14213D", TABLE_HEADER_TEXT="#F5F0E6",
        SHADOW="#D6CDBB",
    ),
}


# --------------------------------------------------------------------------- draw
def _theme_colors(theme: str):
    if theme not in THEMES:
        raise SystemExit(f"Unknown theme {theme!r}; choose from {sorted(THEMES)}")
    T = THEMES[theme]
    return T


def _soft_card(ax, x, y, w, h, *, face, edge, shadow, radius=0.012, lw=1.2, z=1):
    ax.add_patch(
        FancyBboxPatch(
            (x + 0.004, y - 0.004), w, h,
            boxstyle=f"round,pad=0.002,rounding_size={radius}",
            facecolor=shadow, edgecolor="none", alpha=0.35,
            transform=ax.transAxes, clip_on=False, zorder=z,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad=0.002,rounding_size={radius}",
            facecolor=face, edgecolor=edge, linewidth=lw,
            transform=ax.transAxes, clip_on=False, zorder=z + 0.1,
        )
    )


def _new_fig(W_PX=1236, H_PX=1800, DPI=100, bg="#F5F0E6"):
    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI), dpi=DPI, facecolor=bg)
    fig.patch.set_facecolor(bg)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor(bg)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    return fig, ax


def _award_bits(a):
    if a.get("pending"):
        return a.get("title", "AWARD"), "—", "pending"
    key = a.get("key", "")
    title = a.get("title", "AWARD")
    val = a.get("value", "")
    mgr = a.get("manager", "")
    detail = a.get("detail", "")
    if key == "highest_player" and detail:
        return title, val, f"{detail} · {mgr}"
    if key == "bad_beat":
        return title, val, f"{mgr} ({detail})" if detail else mgr
    if key in ("closest", "blowout"):
        return title, val, mgr
    return title, val, mgr


def render_awards(awards, week: int, out_path: Path, theme: str = "navy_gold"):
    """Header + 7 award cards. ~1236x1800 phone frame."""
    T = _theme_colors(theme)
    BG, PANEL, PANEL2, RULE = T["BG"], T["PANEL"], T["PANEL2"], T["RULE"]
    TEXT, MUTED, ACCENT = T["TEXT"], T["MUTED"], T["ACCENT"]
    TITLE_ACCENT = T["TITLE_ACCENT"]
    CARD_ACCENTS = T["CARD_ACCENTS"]
    HEADER_BG = T.get("HEADER_BG", PANEL)
    HEADER_TEXT = T.get("HEADER_TEXT", TEXT)
    HEADER_SUB = T.get("HEADER_SUB", ACCENT)
    SHADOW = T.get("SHADOW", RULE)

    W_PX, H_PX, DPI = 1236, 1800, 100
    fig, ax = _new_fig(W_PX, H_PX, DPI, BG)

    # Header band
    _soft_card(ax, 0.04, 0.88, 0.92, 0.09, face=HEADER_BG, edge=HEADER_BG, shadow=SHADOW, radius=0.02, lw=0)
    ax.add_patch(
        Rectangle(
            (0.07, 0.888), 0.86, 0.008, facecolor=ACCENT, edgecolor="none",
            transform=ax.transAxes, clip_on=False, zorder=3,
        )
    )
    ax.text(
        0.07, 0.935, LEAGUE.upper(),
        color=HEADER_TEXT, fontsize=36, fontweight="bold", va="center", ha="left",
        fontfamily="DejaVu Sans", zorder=4, transform=ax.transAxes,
    )
    ax.text(
        0.07, 0.905, f"POWER RANKINGS  ·  WEEK {week}",
        color=HEADER_SUB, fontsize=22, fontweight="bold", va="center", ha="left",
        fontfamily="DejaVu Sans", zorder=4, transform=ax.transAxes,
    )

    ax.text(
        0.05, 0.855, f"WEEK {week} AWARDS",
        color=TITLE_ACCENT, fontsize=22, fontweight="bold", va="top", ha="left",
        fontfamily="DejaVu Sans", zorder=4, transform=ax.transAxes,
    )

    n_aw = len(awards)
    cols_a = 2
    rows_a = (n_aw + cols_a - 1) // cols_a
    gap_x, gap_y = 0.03, 0.018
    grid_top, grid_bot = 0.82, 0.04
    grid_h = grid_top - grid_bot
    cell_h = (grid_h - gap_y * (rows_a - 1)) / rows_a
    cell_w = (0.92 - gap_x) / cols_a
    x0 = 0.04

    for i, a in enumerate(awards):
        r_i, c_i = divmod(i, cols_a)
        x = x0 + c_i * (cell_w + gap_x)
        y = grid_top - (r_i + 1) * cell_h - r_i * gap_y
        if i == n_aw - 1 and (n_aw % 2 == 1):
            x = x0 + (0.92 - cell_w) / 2.0
        accent = CARD_ACCENTS[i % len(CARD_ACCENTS)]
        _soft_card(ax, x, y, cell_w, cell_h, face=PANEL2, edge=RULE, shadow=SHADOW, radius=0.018, lw=1.0)
        ax.add_patch(
            Rectangle(
                (x + 0.015, y + cell_h * 0.88), cell_w - 0.03, cell_h * 0.08,
                facecolor=accent, edgecolor="none",
                transform=ax.transAxes, clip_on=False, zorder=3,
            )
        )
        label, big, small = _award_bits(a)
        ax.text(
            x + 0.035, y + cell_h * 0.72, label,
            color=MUTED, fontsize=16, fontweight="bold", va="center", ha="left",
            fontfamily="DejaVu Sans", zorder=4, transform=ax.transAxes,
        )
        ax.text(
            x + 0.035, y + cell_h * 0.45, big,
            color=TEXT, fontsize=36, fontweight="bold", va="center", ha="left",
            fontfamily="DejaVu Sans", zorder=4, transform=ax.transAxes,
        )
        ax.text(
            x + 0.035, y + cell_h * 0.18, small,
            color=MUTED, fontsize=20, va="center", ha="left",
            fontfamily="DejaVu Sans", zorder=4, transform=ax.transAxes,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)
    return out_path


def render_rankings(standings, prev_ranks, odds, week: int, out_path: Path,
                    theme: str = "navy_gold", highlight_team: str | None = None, t2m: dict | None = None):
    """Compact header + 12-row table + footnote. ~1236x1800 phone frame."""
    T = _theme_colors(theme)
    BG, PANEL, PANEL2, RULE = T["BG"], T["PANEL"], T["PANEL2"], T["RULE"]
    TEXT, MUTED, ACCENT = T["TEXT"], T["MUTED"], T["ACCENT"]
    GREEN, RED = T["GREEN"], T["RED"]
    HIGHLIGHT, HIGHLIGHT_EDGE = T["HIGHLIGHT"], T["HIGHLIGHT_EDGE"]
    USER_NAME = T["USER_NAME"]
    ROW_ALT = T["ROW_ALT"]
    PO_HIGH, PO_MID, PO_LOW = T["PO_HIGH"], T["PO_MID"], T["PO_LOW"]
    HEADER_BG = T.get("HEADER_BG", PANEL)
    HEADER_TEXT = T.get("HEADER_TEXT", TEXT)
    HEADER_SUB = T.get("HEADER_SUB", ACCENT)
    TABLE_HEADER_BG = T.get("TABLE_HEADER_BG", TEXT)
    TABLE_HEADER_TEXT = T.get("TABLE_HEADER_TEXT", BG)
    SHADOW = T.get("SHADOW", RULE)

    W_PX, H_PX, DPI = 1236, 1800, 100
    fig, ax = _new_fig(W_PX, H_PX, DPI, BG)

    # Compact header
    _soft_card(ax, 0.04, 0.915, 0.92, 0.06, face=HEADER_BG, edge=HEADER_BG, shadow=SHADOW, radius=0.018, lw=0)
    ax.add_patch(
        Rectangle(
            (0.07, 0.920), 0.86, 0.006, facecolor=ACCENT, edgecolor="none",
            transform=ax.transAxes, clip_on=False, zorder=3,
        )
    )
    ax.text(
        0.07, 0.952, LEAGUE.upper(),
        color=HEADER_TEXT, fontsize=28, fontweight="bold", va="center", ha="left",
        fontfamily="DejaVu Sans", zorder=4, transform=ax.transAxes,
    )
    ax.text(
        0.07, 0.930, f"STANDINGS  ·  WEEK {week}",
        color=HEADER_SUB, fontsize=18, fontweight="bold", va="center", ha="left",
        fontfamily="DejaVu Sans", zorder=4, transform=ax.transAxes,
    )

    # Table card
    y_table, h_table = 0.055, 0.845
    _soft_card(ax, 0.035, y_table, 0.93, h_table, face=PANEL, edge=RULE, shadow=SHADOW, radius=0.014, lw=1.2)

    hdr_h = 0.045
    ax.add_patch(
        FancyBboxPatch(
            (0.045, y_table + h_table - hdr_h - 0.012), 0.91, hdr_h,
            boxstyle="round,pad=0.001,rounding_size=0.01",
            facecolor=TABLE_HEADER_BG, edgecolor="none",
            transform=ax.transAxes, clip_on=False, zorder=2,
        )
    )
    cols = [
        ("#", 0.06, "center"),
        ("", 0.110, "center"),
        ("NAME", 0.150, "left"),
        ("REC", 0.420, "center"),
        ("PF", 0.540, "right"),
        ("POW", 0.640, "center"),
        ("LUCK", 0.760, "center"),
        ("PO%", 0.900, "center"),
    ]
    hdr_y = y_table + h_table - hdr_h / 2 - 0.012
    for lab, x, ha in cols:
        ax.text(
            x, hdr_y, lab, color=TABLE_HEADER_TEXT, fontsize=18, fontweight="bold",
            va="center", ha=ha, fontfamily="DejaVu Sans", zorder=3, transform=ax.transAxes,
        )

    n = len(standings)
    body_top = y_table + h_table - hdr_h - 0.020
    body_bot = y_table + 0.018
    row_h = (body_top - body_bot) / n
    lucks = [r["luck"] for r in standings]
    luck_abs = max(2.5, max(abs(min(lucks)), abs(max(lucks))))
    _t2m = t2m or {}

    for i, r in enumerate(standings):
        y = body_top - (i + 0.5) * row_h
        y0 = y - row_h * 0.42
        rh = row_h * 0.84
        is_hi = bool(highlight_team) and r["team"] == highlight_team
        if is_hi:
            ax.add_patch(
                Rectangle(
                    (0.045, y0), 0.91, rh,
                    facecolor=HIGHLIGHT, edgecolor=HIGHLIGHT_EDGE, linewidth=2.0,
                    transform=ax.transAxes, clip_on=False, zorder=1.5,
                )
            )
        elif i % 2 == 1:
            ax.add_patch(
                Rectangle(
                    (0.045, y0), 0.91, rh,
                    facecolor=ROW_ALT, edgecolor="none",
                    transform=ax.transAxes, clip_on=False, zorder=1.5,
                )
            )

        prev = prev_ranks.get(r["team"])
        if prev is None:
            arrow, acol = "–", MUTED
        else:
            delta = prev - r["power_rank"]
            if delta > 0:
                arrow, acol = f"▲{delta}", (ACCENT if theme == "navy_gold" else GREEN)
            elif delta < 0:
                arrow, acol = f"▼{abs(delta)}", RED
            else:
                arrow, acol = "–", MUTED

        po = odds[r["team"]] * 100
        po_color = PO_HIGH if po >= 50 else (PO_MID if po >= 20 else PO_LOW)
        name_color = USER_NAME if is_hi else TEXT
        L = r["luck"]
        luck_color = GREEN if L > 0 else (RED if L < 0 else MUTED)
        dname = _t2m.get(r["team"], r["team"])

        bar_cx, bar_half_w = 0.760, 0.040
        ax.add_patch(
            Rectangle(
                (bar_cx - bar_half_w, y - row_h * 0.28), 2 * bar_half_w, row_h * 0.08,
                facecolor=RULE, edgecolor="none", alpha=0.45,
                transform=ax.transAxes, clip_on=False, zorder=2,
            )
        )
        frac = max(-1.0, min(1.0, L / luck_abs))
        if abs(frac) > 0.02:
            if frac >= 0:
                ax.add_patch(
                    Rectangle(
                        (bar_cx, y - row_h * 0.26), bar_half_w * frac, row_h * 0.12,
                        facecolor=GREEN, edgecolor="none",
                        transform=ax.transAxes, clip_on=False, zorder=2.2,
                    )
                )
            else:
                ax.add_patch(
                    Rectangle(
                        (bar_cx + bar_half_w * frac, y - row_h * 0.26), bar_half_w * (-frac), row_h * 0.12,
                        facecolor=RED, edgecolor="none",
                        transform=ax.transAxes, clip_on=False, zorder=2.2,
                    )
                )

        vals = [
            (f"{r['power_rank']}", 0.06, "center", TEXT, "bold", 26),
            (arrow, 0.110, "center", acol, "bold", 22),
            (dname, 0.150, "left", name_color, "bold", 26),
            (r["record"], 0.420, "center", TEXT, "bold", 24),
            (f"{r['PF']:.0f}", 0.540, "right", TEXT, "bold", 24),
            (f"{r['power']:.2f}", 0.640, "center", MUTED, "bold", 22),
            (f"{L:+.1f}", 0.760, "center", luck_color, "bold", 20),
            (f"{po:.0f}%", 0.900, "center", po_color, "bold", 26),
        ]
        for text, x, ha, color, weight, fs in vals:
            dy = row_h * 0.16 if x == 0.760 else 0.0
            ax.text(
                x, y + dy, text, color=color, fontsize=fs, fontweight=weight,
                va="center", ha=ha, fontfamily="DejaVu Sans", zorder=3,
                transform=ax.transAxes,
            )

    # Footnote
    _soft_card(ax, 0.04, 0.012, 0.92, 0.032, face=PANEL2, edge=RULE, shadow=SHADOW, radius=0.012, lw=0.8)
    ax.text(
        0.06, 0.028,
        f"Week {week} · 12k sims · 14-wk season · top 6 (W then PF)",
        color=MUTED, fontsize=15, va="center", ha="left",
        fontfamily="DejaVu Sans", zorder=3, transform=ax.transAxes,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)
    return out_path


def render(standings, prev_ranks, awards, odds, week: int, out_dir: Path,
           theme: str = "navy_gold", highlight_team: str | None = None, t2m: dict | None = None):
    """Write the two Slack-friendly phone images for the week."""
    out_dir = Path(out_dir)
    awards_path = out_dir / f"power_rankings_wk{week}_awards.png"
    ranks_path = out_dir / f"power_rankings_wk{week}_rankings.png"
    render_awards(awards, week, awards_path, theme=theme)
    render_rankings(standings, prev_ranks, odds, week, ranks_path,
                    theme=theme, highlight_team=highlight_team, t2m=t2m)
    return awards_path, ranks_path



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--sims", type=int, default=N_SIMS)
    ap.add_argument(
        "--theme", default="navy_gold",
        choices=sorted(THEMES.keys()),
        help="Visual theme: dark | editorial | clean | field | navy_gold",
    )
    ap.add_argument(
        "--highlight", default=None, metavar="TEAM",
        help="Optional team name to highlight (default: none)",
    )
    args = ap.parse_args()

    pts, opp = load_scores(args.csv)
    week = args.week or max(pts)
    out_dir = Path(args.out).parent if args.out else OUT_DIR
    t2m, m2t = load_managers()
    extras = load_extras()

    standings = compute_standings(pts, opp, week)
    prev = compute_standings(pts, opp, week - 1) if week > 1 else []
    prev_ranks = {r["team"]: r["power_rank"] for r in prev}
    awards, meta = compute_awards(pts, opp, week, extras, t2m)
    odds = playoff_odds(standings, week, n_sims=args.sims)

    awards_path, ranks_path = render(
        standings, prev_ranks, awards, odds, week, out_dir,
        theme=args.theme, highlight_team=args.highlight, t2m=t2m,
    )

    print(f"Wrote {awards_path}  (theme={args.theme})")
    print(f"Wrote {ranks_path}  (theme={args.theme})")
    print(f"Managers mapped ({len(t2m)}):")
    for t, m in sorted(t2m.items(), key=lambda x: x[1]):
        print(f"  {m:8s} -> {t}")
    print(f"Week {week} awards:")
    for a in awards:
        if a.get("pending"):
            print(f"  {a['title']:18s} pending")
        else:
            print(f"  {a['title']:18s} {a.get('value','')}  |  {a.get('manager','')}  {a.get('detail','')}")


if __name__ == "__main__":
    main()
