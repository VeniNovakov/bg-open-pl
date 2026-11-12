"""JSON shapes of the API. Weights and points are floats here, Decimals in the parser."""

from __future__ import annotations

from pydantic import BaseModel

from ..models import AttemptStatus, Lifter, StandardMeet
from .store import MeetRecord


class AttemptOut(BaseModel):
    weight_kg: float | None
    result: str | None  # "good", "fail" or null when not taken


class LiftOut(BaseModel):
    attempts: list[AttemptOut]
    best_kg: float | None


class LifterOut(BaseModel):
    name: str
    sex: str | None
    club: str
    division: str
    weight_class: str | None
    equipment: str
    status: str  # ranked, guest, disqualified
    place: int | None
    body_weight_kg: float | None
    squat: LiftOut
    bench: LiftOut
    deadlift: LiftOut
    total_kg: float | None
    points: float | None
    points_kind: str
    meet: str  # meet slug


class ClassGroupOut(BaseModel):
    header: str
    lifters: list[LifterOut]


class FindingOut(BaseModel):
    code: str
    severity: str
    message: str
    row: int | None


class MeetSummaryOut(BaseModel):
    slug: str
    title: str | None
    federation: str | None
    city: str | None
    date: str | None
    lifters: int
    errors: int
    warnings: int


class MeetOut(MeetSummaryOut):
    classes: list[ClassGroupOut]


class RankingRowOut(BaseModel):
    rank: int
    lifter: LifterOut


def _f(value) -> float | None:
    return None if value is None else float(value)


def _lift(lift) -> LiftOut:
    return LiftOut(
        attempts=[AttemptOut(
            weight_kg=_f(a.weight_kg),
            result=None if a.weight_kg is None else
            ("fail" if a.status is AttemptStatus.FAIL else "good"))
            for a in lift.attempts],
        best_kg=_f(lift.best_kg))


def lifter_out(lifter: Lifter, slug: str) -> LifterOut:
    return LifterOut(
        name=lifter.name, sex=lifter.sex, club=lifter.club, division=lifter.division,
        weight_class=lifter.class_label, equipment=lifter.equipment, status=lifter.status.value,
        place=lifter.place, body_weight_kg=_f(lifter.body_weight_kg),
        squat=_lift(lifter.lifts["S"]), bench=_lift(lifter.lifts["B"]),
        deadlift=_lift(lifter.lifts["D"]), total_kg=_f(lifter.total_kg),
        points=_f(lifter.points), points_kind=lifter.points_kind, meet=slug)


def finding_out(issue) -> FindingOut:
    return FindingOut(code=issue.code, severity=issue.severity.value, message=issue.message,
                      row=issue.row)


def meet_summary(rec: MeetRecord) -> MeetSummaryOut:
    meet: StandardMeet = rec.meet
    return MeetSummaryOut(
        slug=rec.slug, title=meet.title, federation=meet.federation, city=meet.city,
        date=str(meet.date) if meet.date else None, lifters=len(rec.lifters),
        errors=sum(1 for i in rec.findings if i.severity.value == "error"),
        warnings=sum(1 for i in rec.findings if i.severity.value == "warning"))
