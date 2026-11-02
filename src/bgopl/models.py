"""Plain data containers shared by the parser, validator and loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AttemptStatus(str, Enum):
    GOOD = "good"
    FAIL = "fail"
    UNKNOWN = "unknown"


class StatusSource(str, Enum):
    EXPLICIT = "explicit"  # the file said so (for example a negative weight)
    INFERRED = "inferred"  # derived from RESULT and attempt order, see outcomes.py
    NONE = "none"  # nothing known


@dataclass(frozen=True)
class Issue:
    code: str
    severity: Severity
    message: str
    row: int | None = None  # 1-based worksheet row; None means the whole file


@dataclass
class Attempt:
    number: int
    raw: str  # cell text exactly as read
    weight_kg: Decimal | None
    status: AttemptStatus = AttemptStatus.UNKNOWN
    status_source: StatusSource = StatusSource.NONE
    note: str = ""  # text after the weight, e.g. the "1" in "150.0 1"; meaning unknown


@dataclass
class Entry:
    row: int  # worksheet row, also the key into ParsedMeet.raw_rows
    division: str  # label as printed: "Juniors", "Seniors", "Masters 1"
    class_label: str  # "57" or "84+"
    class_limit_kg: Decimal | None  # upper limit, None for an open-ended "+" class
    place_raw: str
    place: int | None
    name: str
    birth_year: int | None
    club_raw: str  # abbreviation as printed in the row
    club: str  # resolved through the sheet's abbreviation table
    body_weight_kg: Decimal | None
    factor: Decimal | None  # "WF" column
    lot: int | None
    attempts: list[Attempt]
    result_kg: Decimal | None
    points: Decimal | None  # "Pts." column
    status: str = "ok"  # "ok" or "disqualified" (the sheet prints "disq." under W.pts.)
    status_raw: str = ""  # the cell text that decided it


@dataclass
class TeamStanding:
    """One row of a "Nation (points)" table. Derived data, kept only for cross-checks."""

    row: int
    division: str
    place: int | None
    club: str  # as printed (already the full name in the 2026 NSA file)
    points: int | None  # team points, e.g. 21
    scorers: list[int]  # the "[12+9]" breakdown
    weighted_points: Decimal | None  # the "109.15 w.pts." part, printed with 2 decimals


@dataclass
class BestLifter:
    """One row of a "Best Lifters of ..." table. Derived data, kept only for cross-checks."""

    row: int
    division: str
    place: int | None
    name: str
    club: str
    body_weight_kg: Decimal | None
    factor: Decimal | None
    result_kg: Decimal | None
    points: Decimal | None  # printed with 2 decimals


@dataclass
class ParsedMeet:
    sheet: str
    title: str | None
    country: str | None
    city: str | None
    date: date | None
    sex_hint: str | None  # "F" or "M" guessed from the title prefix, to be confirmed by a human
    event_hint: str | None  # "B" guessed from the title
    club_abbreviations: dict[str, str]
    entries: list[Entry]
    raw_rows: dict[int, list[str]]  # every non-empty worksheet row, kept for traceability
    issues: list[Issue] = field(default_factory=list)
    team_standings: list[TeamStanding] = field(default_factory=list)
    best_lifters: list[BestLifter] = field(default_factory=list)
    sex_hint_source: str | None = None  # "title" or "filename"
    parser_name: str = "scoresheet"
    parser_version: str = "0.1.0"


# ---------------------------------------------------------------------------------------------
# The "standard" full-power layout (Bulgarian headers, three lifts, IPF GL points).
# ---------------------------------------------------------------------------------------------


class LifterStatus(str, Enum):
    RANKED = "ranked"
    GUEST = "guest"  # category cell reads "n/a": competes outside the ranking
    DISQUALIFIED = "disqualified"  # place cell reads "DQ"


@dataclass
class LiftResult:
    """One lift (squat, bench or deadlift): three attempts and the printed best."""

    attempts: list[Attempt]
    best_kg: Decimal | None  # as printed in the "best" column

    @property
    def good_weights(self) -> list[Decimal]:
        return [a.weight_kg for a in self.attempts
                if a.weight_kg is not None and a.status is AttemptStatus.GOOD]


@dataclass
class Lifter:
    row: int
    section: str  # nearest section heading, e.g. "Жени", "Ветерани - М1"
    group: tuple  # ranking group: lifters in one group are placed against each other
    sex: str | None  # "F" or "M", from the nearest "Жени"/"Мъже" heading
    sex_source: str  # "heading" or "inherited"
    equipment: str  # "classic" or "equipped" (equipped only under an explicit heading)
    division: str  # column "Дивизия": Open, M1, M2, M3
    class_label: str | None  # from the category cell: "47", "84+"; None for a guest
    class_context: str | None  # from the class row above the lifter; None in a block without them
    class_limit_kg: Decimal | None  # None for open-ended "+" classes
    class_floor_kg: Decimal | None  # lower bound of a "+" class
    place_raw: str
    place: int | None
    status: LifterStatus
    name: str
    club: str
    body_weight_kg: Decimal | None
    lifts: dict[str, LiftResult]  # keys "S", "B", "D"
    total_kg: Decimal | None
    points: Decimal | None
    points_kind: str  # header text of the points column, e.g. "IPF GL точки"
    team_points: int | None

    def __str__(self) -> str:
        from .views import lifter_line

        return lifter_line(self)

    def describe(self) -> str:
        """A multi-line card with every attempt (ok = good, x = failed)."""
        from .views import lifter_detail

        return lifter_detail(self)


@dataclass
class StdTeamRow:
    row: int
    table: str  
    place: int | None
    club: str
    scorers: list[int]
    printed_total: int | None
    raw: str


@dataclass
class StdBestLifter:
    row: int
    section: str
    name: str
    points: Decimal | None
    club: str


@dataclass
class StandardMeet:
    sheet: str
    title: str | None
    federation: str | None
    city: str | None
    date: date | None
    lifters: list[Lifter]
    team_rows: list[StdTeamRow]
    best_lifters: list[StdBestLifter]
    raw_rows: dict[int, list[str]]
    issues: list[Issue] = field(default_factory=list)
    parser_name: str = "standard"
    parser_version: str = "0.1.0"

    def __iter__(self):
        return iter(self.lifters)

    def __len__(self) -> int:
        return len(self.lifters)

    def by_class(self) -> list[tuple[str, list[Lifter]]]:
        """(header, lifters) per sex / equipment / division / weight class, sorted by total."""
        from .views import group_lifters

        return group_lifters(self.lifters)

    def find(self, text: str) -> list[Lifter]:
        """Lifters whose name contains the text (case-insensitive)."""
        needle = text.casefold()
        return [x for x in self.lifters if needle in x.name.casefold()]