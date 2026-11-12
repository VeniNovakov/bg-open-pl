"""Builds synthetic, anonymised workbooks in the standard full-power layout.

Names, clubs and numbers are invented. Points and totals are computed, so a workbook built
without overrides is clean and each test injects exactly one defect.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import openpyxl

from bgopl.points import ipf_gl_points

HEADER = ["Place", None, "Club", "Division", "Bodyweight", "Category",
          "Squat-1", "Squat-2", "Squat-3", "Best squat",
          "Bench-1", "Bench-2", "Bench-3", "Best bench",
          "Deadlift-1", "Deadlift-2", "Deadlift-3", "Best deadlift",
          "Total kg", "IPF GL points", "Team points", None]
TITLE = "Test championship powerlifting city Sofia 01-02 January 2026"
TEAM_SCALE = {1: 12, 2: 9, 3: 8}


def _best(attempts):
    good = [a for a in attempts if a is not None and a > 0]
    return max(good) if good else None


def lifter(name, bw, squat, bench, dead, *, place=1, club="Club Alpha", division="Open",
           category=None, sex="F", equipment="classic", points="auto", team="auto",
           total="auto", bests=None):
    """One athlete row (list of cell values). Attempts are signed: negative = failed."""
    s_best, b_best, d_best = bests or (_best(squat), _best(bench), _best(dead))
    if total == "auto":
        parts = [s_best, b_best, d_best]
        total = sum(parts) if all(p is not None for p in parts) else None
    if points == "auto":
        points = None
        if total and isinstance(place, int):
            pts = ipf_gl_points(sex, equipment, Decimal(str(bw)), Decimal(str(total)))
            points = float(round(pts, 2)) if pts is not None else None
    if team == "auto":
        team = TEAM_SCALE.get(place) if isinstance(place, int) else None
    if category is None:
        category = "n/a"
    pad = lambda a: [*a, *([None] * (3 - len(a)))]
    return [place, name, club, division, bw, category,
            *pad(squat), s_best, *pad(bench), b_best, *pad(dead), d_best,
            total, points, team, None]


def section(text):
    return [None, text, *([None] * 20)]


def klass(value):
    return [value, *([None] * 21)]


def write_standard(path: Path, blocks, *, title=TITLE, tail=None, header=True,
                   date="2026-01-01") -> Path:

    rows = [[title, *([None] * 21)], ["BPF", date, *([None] * 20)], [None] * 22]
    if header:
        rows.append(HEADER)
    rows.extend(blocks)
    rows.append([None] * 22)
    rows.extend(tail or [])
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Protocol"
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


def clean_blocks():
    return [
        section("Women "),
        klass(63.0),
        lifter("Anna First", 60.0, [100, 105, -110], [60, 62.5, 65], [120, 125, 130],
               place=1, category=63.0),
        lifter("Bella Second", 62.0, [90, 95, 100], [50, 55, -57.5], [110, 115, 120],
               place=2, club="Club Beta", category=63.0),
        section("Men"),
        klass(74.0),
        lifter("Victor First", 73.0, [200, 210, 220], [140, 145, -150], [230, 240, 250],
               place=1, sex="M", category=74.0),
        klass(83.0),
        lifter("George Second", 80.0, [190, 200, -210], [130, 135, 140], [220, 230, 240],
               place=1, club="Club Beta", sex="M", category=83.0),
        lifter("Daniel Third", 82.0, [180, 190, 200], [120, 125, -130], [200, 210, 220],
               place=2, sex="M", category=83.0),
        section("Veterans - M1"),
        klass("M1 - 74"),
        lifter("Emil Veteran", 72.0, [150, 160, 170], [100, 105, 110], [180, 190, 200],
               place=1, sex="M", division="M1", category=74.0),
        lifter("Guest Person", 90.0, [150, 160, 170], [100, 105, 110], [180, 190, 200],
               place="DQ", sex="M", division="M1", category="n/a", points=None, team=None),
    ]
