
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from .models import AttemptStatus, LifterStatus

if TYPE_CHECKING:
    from .models import Attempt, Lifter

COLUMNS = ("File#", "Place", "Name", "Sex", "Club", "Div", "Class", "BW", "Squat", "Bench",
           "Dead", "Total", "Points")
NUMERIC_COLUMNS = {0, 7, 8, 9, 10, 11, 12}
DIVISION_ORDER = {"Open": 0, "M1": 1, "M2": 2, "M3": 3}
LIFT_NAMES = {"S": "Squat", "B": "Bench", "D": "Deadlift"}


def fmt_kg(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}" if value == value.to_integral_value() else f"{value.normalize():f}"


def place_text(lifter: Lifter) -> str:
    if lifter.status is LifterStatus.GUEST:
        return "guest"
    if lifter.status is LifterStatus.DISQUALIFIED:
        return "DQ"
    return str(lifter.place)


def lifter_cells(lifter: Lifter) -> list[str]:
    return [
        place_text(lifter),
        lifter.name,
        lifter.sex or "?",
        lifter.club,
        lifter.division,
        lifter.class_label or "-",
        fmt_kg(lifter.body_weight_kg),
        fmt_kg(lifter.lifts["S"].best_kg),
        fmt_kg(lifter.lifts["B"].best_kg),
        fmt_kg(lifter.lifts["D"].best_kg),
        fmt_kg(lifter.total_kg),
        f"{lifter.points:.2f}" if lifter.points is not None else "-",
    ]


def lifter_line(lifter: Lifter) -> str:
    c = lifter_cells(lifter)
    return (f"{c[0]:>5}  {c[1]}  [{c[2]}] {c[3]}  {c[4]} {c[5]} kg  bw {c[6]}  "
            f"S {c[7]}  B {c[8]}  D {c[9]}  total {c[10]}  pts {c[11]}")


def _attempt_text(attempt: Attempt) -> str:
    if attempt.weight_kg is None:
        return "   -   "
    mark = "x" if attempt.status is AttemptStatus.FAIL else "ok"
    return f"{fmt_kg(attempt.weight_kg):>6}{mark}"


def lifter_detail(lifter: Lifter) -> str:
    sex = {"F": "women", "M": "men"}.get(lifter.sex or "", "sex unknown")
    klass = f"{lifter.class_label} kg" if lifter.class_label else "no class"
    points = f"{lifter.points:.2f}" if lifter.points is not None else "-"
    team = lifter.team_points if lifter.team_points is not None else "-"
    lines = [
        f"{lifter.name}   ({lifter.club})",
        (f"  {sex} | {lifter.division} | {klass} | {lifter.equipment}"
         f"   place: {place_text(lifter)} ({lifter.status.value})"),
        f"  bodyweight {fmt_kg(lifter.body_weight_kg)} kg   points {points}   team points {team}",
    ]
    for key, lift in lifter.lifts.items():
        attempts = " ".join(_attempt_text(a) for a in lift.attempts)
        lines.append(f"  {LIFT_NAMES[key]:<9}{attempts}   best {fmt_kg(lift.best_kg)}")
    lines.append(f"  total {fmt_kg(lifter.total_kg)} kg")
    return "\n".join(lines)


def _class_sort_key(lifter: Lifter) -> tuple:
    """Lightest class first, open-ended "+" classes last."""
    if lifter.class_limit_kg is not None:
        return (0, lifter.class_limit_kg)
    return (1, lifter.class_floor_kg or Decimal(0))


def total_sort_key(lifter: Lifter) -> tuple:
    """Highest total first, equal totals by the lighter lifter, no total last."""
    total = lifter.total_kg
    return (total is None, -(total or Decimal(0)), lifter.body_weight_kg or Decimal(0),
            lifter.name)


def group_lifters(lifters: list[Lifter]) -> list[tuple[str, list[Lifter]]]:
    """(header, lifters) per sex / equipment / division / class, each sorted by total."""
    groups: dict[tuple, list[Lifter]] = {}
    for lifter in lifters:
        sex_rank = {"F": 0, "M": 1}.get(lifter.sex or "", 2)
        if lifter.status is LifterStatus.GUEST:
            key = (sex_rank, 2, 9, (2, Decimal(0)), "guest")
        else:
            key = (sex_rank, lifter.equipment == "equipped",
                   DIVISION_ORDER.get(lifter.division, 9), _class_sort_key(lifter),
                   lifter.class_label or "")
        groups.setdefault(key, []).append(lifter)

    sex_names = {"F": "Women", "M": "Men"}
    out = []
    for key in sorted(groups):
        members = sorted(groups[key], key=total_sort_key)
        first = members[0]
        sex = sex_names.get(first.sex or "", "Sex unknown")
        if key[4] == "guest":
            header = f"{sex} | guest lifters"
        else:
            klass = f"{first.class_label} kg" if first.class_label else "no class"
            header = f"{sex} | {first.division} | {klass} | {first.equipment}"
        out.append((header, members))
    return out