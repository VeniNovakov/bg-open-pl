"""What the athlete page shows, computed from the store: one card per meet, personal bests per
equipment, and a points history. Pure functions, no web code."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..models import AttemptStatus, Lifter, LifterStatus
from .store import MeetRecord

LIFT_NAMES = (("S", "Squat"), ("B", "Bench press"), ("D", "Deadlift"))


@dataclass
class ResultCard:
    rec: MeetRecord
    lifter: Lifter
    class_place: str  # "1 of 7", or "" when the lifter is not ranked
    points_rank: str  # "3 of 64 men", or "" when not ranked
    made: int  # attempts with a weight
    good: int
    shares: list[tuple[str, Decimal | None, int]]  # lift name, best, share of total in percent


@dataclass
class PersonalBest:
    label: str
    value: Decimal
    meet: MeetRecord
    is_points: bool = False


def _rank_text(lifter: Lifter, rec: MeetRecord) -> tuple[str, str]:
    if lifter.status is not LifterStatus.RANKED:
        return "", ""
    in_class = [x for x in rec.lifters
                if x.group == lifter.group and x.status is LifterStatus.RANKED]
    class_place = f"{lifter.place} of {len(in_class)}" if lifter.place else ""
    if lifter.points is None:
        return class_place, ""
    pool = [x for x in rec.lifters
            if x.sex == lifter.sex and x.equipment == lifter.equipment
            and x.status is LifterStatus.RANKED and x.points is not None]
    rank = 1 + sum(1 for x in pool if x.points > lifter.points)
    noun = {"F": "women", "M": "men"}.get(lifter.sex or "", "lifters")
    return class_place, f"{rank} of {len(pool)} {noun}"


def build_cards(results: list[tuple[MeetRecord, Lifter]]) -> list[ResultCard]:
    cards = []
    for rec, lifter in results:
        class_place, points_rank = _rank_text(lifter, rec)
        attempts = [a for lift in lifter.lifts.values() for a in lift.attempts
                    if a.weight_kg is not None]
        bests = [lift.best_kg for lift in lifter.lifts.values()]
        total = sum((b for b in bests if b is not None), Decimal(0))
        shares = []
        for key, name in LIFT_NAMES:
            best = lifter.lifts[key].best_kg
            percent = round(float(best / total) * 100) if best is not None and total else 0
            shares.append((name, best, percent))
        cards.append(ResultCard(
            rec=rec, lifter=lifter, class_place=class_place, points_rank=points_rank,
            made=len(attempts), good=sum(1 for a in attempts if a.status is AttemptStatus.GOOD),
            shares=shares))
    return cards


def personal_bests(results: list[tuple[MeetRecord, Lifter]]) -> dict[str, list[PersonalBest]]:
    """Best squat, bench, deadlift, total and points per equipment. The total and points
    count only ranked results; the single lifts count any result that has them."""
    out: dict[str, list[PersonalBest]] = {}
    for equipment in sorted({x.equipment for _, x in results}):
        mine = [(rec, x) for rec, x in results if x.equipment == equipment]
        bests: list[PersonalBest] = []
        for key, name in LIFT_NAMES:
            have = [(rec, x.lifts[key].best_kg) for rec, x in mine
                    if x.lifts[key].best_kg is not None]
            if have:
                rec, value = max(have, key=lambda t: t[1])
                bests.append(PersonalBest(name, value, rec))
        ranked = [(rec, x) for rec, x in mine if x.status is LifterStatus.RANKED]
        totals = [(rec, x.total_kg) for rec, x in ranked if x.total_kg is not None]
        if totals:
            rec, value = max(totals, key=lambda t: t[1])
            bests.append(PersonalBest("Total", value, rec))
        points = [(rec, x.points) for rec, x in ranked if x.points is not None]
        if points:
            rec, value = max(points, key=lambda t: t[1])
            bests.append(PersonalBest("IPF GL points", value, rec, is_points=True))
        out[equipment] = bests
    return out


def history(results: list[tuple[MeetRecord, Lifter]]) -> list[tuple[str, Lifter]]:
    """Ranked results with points, oldest first (the chart needs at least two)."""
    rows = [(rec.slug, x) for rec, x in results
            if x.status is LifterStatus.RANKED and x.points is not None]
    return sorted(rows, key=lambda t: t[0])


def sparkline(values: list[float], width: int = 260, height: int = 56,
              pad: int = 6) -> list[tuple[float, float]]:
    """Scaled (x, y) coordinates for an inline SVG line; y grows downwards."""
    low, high = min(values), max(values)
    span = (high - low) or 1.0
    step = (width - 2 * pad) / max(len(values) - 1, 1)
    return [(round(pad + i * step, 1),
             round(height - pad - (v - low) / span * (height - 2 * pad), 1))
            for i, v in enumerate(values)]