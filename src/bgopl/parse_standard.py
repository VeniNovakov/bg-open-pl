"""Parser for the standard full-power results sheet (Bulgarian headers, IPF GL points).

Layout, top to bottom (see docs/layout-standard.md):

    title row, then "federation | ISO date", then the header row ("Място", "Отбор", ...)
    section rows   "Жени", "Мъже", "Ветерани - М1", "Шамшион на шампионите екипировъчен ..."
    class rows     47.0 | "84+" | "М1 - 69"
    athlete rows   place, name, club, division, bodyweight, category, 3 x (3 attempts + best),
                   total, points, team points
    derived tables best lifters ("Шамшион на шампионите"), team tables ("Отборно класиране",
                   "Отбор жени", "Отбор мъже"): parsed only to cross-check the athlete rows

A failed attempt is a negative weight. A category of "n/a" marks a guest lifter, a place of "DQ"
a disqualified one. A bad row becomes an Issue instead of aborting the parse.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

from .models import (
    Attempt,
    AttemptStatus,
    Issue,
    Lifter,
    LifterStatus,
    LiftResult,
    Severity,
    StandardMeet,
    StatusSource,
    StdBestLifter,
    StdTeamRow,
)

PARSER_VERSION = "0.1.0"

HEADER_KEYS = {
    "място": "place",
    "отбор": "club",
    "дивизия": "division",
    "лично тегло": "bw",
    "категория": "category",
    "най-добър клек": "best_S",
    "най-добър лег": "best_B",
    "най-добра тяга": "best_D",
    "тотал кг": "total",
    "точки за отбор": "team_points",
    "place": "place",
    "club": "club",
    "division": "division",
    "bodyweight": "bw",
    "category": "category",
    "best squat": "best_S",
    "best bench": "best_B",
    "best deadlift": "best_D",
    "total kg": "total",
    "team points": "team_points",
}

ATTEMPT_HEADER_RE = re.compile(
    r"^(клек|лег|м\.?\s*тяга|squat|bench|deadlift)\s*-\s*([123])$")
LIFT_OF_WORD = {"клек": "S", "лег": "B", "squat": "S", "bench": "B"} 
WOMEN_WORDS = ("жени", "women")
MEN_WORDS = ("мъже", "men")
GUEST_MARKERS = {"n/a", "na", "н/д", "гост", "guest"}
CLASS_RE = re.compile(
    r"^(?:[mм]\s*\d\s*-\s*)?(?P<n>\d+(?:[.,]\d+)?)\s*(?P<plus>\+)?\s*(?:кг|kg)?$", re.IGNORECASE
)
CHAMPION_HEADING_RE = re.compile(r"(?:ша?м[пш]ион на шампионите|champion of champions)")
DIVISION_IN_HEADING_RE = re.compile(r"\b[mм]\s*(\d)\b")
HEADING_DIVISION_RE = re.compile(r"\b(sjr|jr|open)\b")
CITY_RE = re.compile(r"(?:град|city)\s+(?P<city>.+?)\s+\d", re.IGNORECASE)
TEAM_TOTAL_RE = re.compile(r"=\s*(\d+)\s*$")
TEAM_SCORERS_RE = re.compile(r"(?:^|[\s=\-])(\d+(?:\s*\+\s*\d+)*)\s*\+?\s*$")
LIFTS = ("S", "B", "D")


_INVISIBLE = {0x200E: None, 0x200F: None}


def _clean(value) -> str:
    if value is None:
        return ""
    text = str(value).translate(_INVISIBLE).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _low(value) -> str:
    return _clean(value).lower()


def _num(value) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None if value is None else _bad(value)
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = _clean(value).replace(",", ".")
    if text == "" or text in {"-", "–", "—"}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return _bad(value)


def _bad(value):
    raise ValueError(f"not a number: {value!r}")


def _int(value) -> int | None:
    number = _num(value)
    if number is None:
        return None
    if number != number.to_integral_value():
        raise ValueError(f"not a whole number: {value!r}")
    return int(number)


def _label(number: Decimal) -> str:
    return str(int(number)) if number == number.to_integral_value() else str(number.normalize())


def parse_class(value) -> tuple[str, Decimal | None, Decimal | None, str | None] | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        text = str(value)
    else:
        text = _clean(value)
    match = CLASS_RE.match(text)
    if not match:
        return None
    number = Decimal(match["n"].replace(",", "."))
    division = DIVISION_IN_HEADING_RE.search(text.lower())
    div = f"M{division[1]}" if division else None
    if match["plus"]:
        return f"{_label(number)}+", None, number, div
    return _label(number), number, None, div


def norm_division(value) -> str:
    text = _clean(value)
    return re.sub(r"^[Мм](?=\d)", "M", text)


def parse_team_text(text: str) -> tuple[str, list[int], int | None] | None:
    t = _clean(text)
    total = None
    m_total = TEAM_TOTAL_RE.search(t)
    rest = t
    if m_total:
        total = int(m_total[1])
        rest = t[: m_total.start()].rstrip()
    m_scorers = TEAM_SCORERS_RE.search(rest)
    nums = [int(x) for x in re.findall(r"\d+", m_scorers[1])] if m_scorers else []
    if total is not None and (not nums or (len(nums) == 1 and nums[0] != total)):

        scorers, club = [total], rest.strip(" =-")
    elif m_scorers:
        scorers = nums
        club = rest[: m_scorers.start()].strip(" =-")
    else:
        return None
    if not club:
        return None
    return club, scorers, total


class _Parser:
    def __init__(self, rows: list[tuple[int, list]]) -> None:
        self.rows = rows
        self.issues: list[Issue] = []
        self.cols: dict[str, int] = {}
        self.attempt_cols: dict[str, list[int]] = {}
        self.name_col = 1
        self.points_col: int | None = None
        self.points_kind = ""
        self.lifters: list[Lifter] = []
        self.team_rows: list[StdTeamRow] = []
        self.best_lifters: list[StdBestLifter] = []

    def issue(self, code: str, severity: Severity, message: str, row: int | None = None) -> None:
        self.issues.append(Issue(code, severity, message, row))

    def _read_header(self) -> int:
        for index, (_, cells) in enumerate(self.rows):
            lows = [_low(c) for c in cells]
            if ("място" in lows or "place" in lows) and ("тотал кг" in lows or "total kg" in lows):
                self._map_header(lows)
                return index
        raise ValueError("no header row found (expected a row with 'Място' and 'Тотал КГ', or 'Place' and 'Total kg')")

    def _map_header(self, lows: list[str]) -> None:
        self.attempt_cols = {k: [] for k in LIFTS}
        for i, text in enumerate(lows):
            if text in HEADER_KEYS:
                self.cols[HEADER_KEYS[text]] = i
            elif text.startswith("ipf"):
                self.points_col, self.points_kind = i, text
            elif m := ATTEMPT_HEADER_RE.match(text):
                word = m[1].replace(" ", "").replace(".", "")
                lift = LIFT_OF_WORD.get(word, "D")
                self.attempt_cols[lift].append(i)
        missing = [k for k in ("place", "club", "bw", "category", "total") if k not in self.cols]
        missing += [f"attempts {k}" for k in LIFTS if len(self.attempt_cols[k]) != 3]
        missing += [f"best {k}" for k in LIFTS if f"best_{k}" not in self.cols]
        if missing or self.points_col is None:
            raise ValueError(f"header row is missing columns: {missing or ['IPF points']}")
        place = self.cols["place"]
        self.name_col = place + 1 if not lows[place + 1] else lows.index("име" if "име" in lows else "name")
        text = lows[self.points_col]
        self.points_kind = "IPF GL" if text.startswith("ipf gl") else text

    def run(self) -> None:
        start = self._read_header()
        mode = "athletes"  
        sex: str | None = None
        sex_row_section: str | None = None
        section = ""
        section_no = 0
        equipment = "classic"
        class_ctx: tuple | None = None
        section_division: str | None = None
        team_table = "overall"
        best_section = ""
        inherited = 0

        for row, cells in self.rows[start + 1 :]:
            if not any(_clean(c) for c in cells):
                continue
            a = cells[self.cols["place"]] if self.cols["place"] < len(cells) else None
            name = cells[self.name_col] if self.name_col < len(cells) else None
            others = [
                c for i, c in enumerate(cells)
                if i not in (self.cols["place"], self.name_col) and _clean(c)
            ]
            a_text, name_text = _clean(a), _clean(name)

            if not a_text and name_text and not others:
                low = name_text.lower()
                if CHAMPION_HEADING_RE.match(low):
                    if "екипир" in low or "equipped" in low:
                        mode, equipment = "athletes", "equipped"
                        section, section_no, class_ctx = name_text, section_no + 1, None
                        sex_row_section = None
                    else:
                        mode, best_section = "best", ""
                    continue
                if low.startswith(("отборно класиране", "team ranking")):
                    mode, team_table = "team", "overall"
                    continue
                if low.startswith(("отбор жени", "women team")):
                    mode, team_table = "team", "women"
                    continue
                if low.startswith(("отбор мъже", "men team")):
                    mode, team_table = "team", "men"
                    continue
                if mode == "best":
                    best_section = name_text
                    continue
                if mode == "team":
                    self._team_row(row, cells, team_table, a, name_text)
                    continue

                equipment = "equipped" if ("екипир" in low or "equipped" in low) else "classic"
                section, section_no, class_ctx = name_text, section_no + 1, None
                if low.startswith(WOMEN_WORDS):
                    sex = "F"
                elif low.startswith(MEN_WORDS):
                    sex = "M"
                sex_row_section = (section if low.startswith(WOMEN_WORDS + MEN_WORDS)
                                   else sex_row_section)
                m = DIVISION_IN_HEADING_RE.search(low)
                named = HEADING_DIVISION_RE.search(low)
                section_division = (f"M{m[1]}" if m
                                    else {"sjr": "SJR", "jr": "JR", "open": "Open"}[named[1]]
                                    if named else None)
                continue

            if mode == "best":
                if name_text:
                    self._best_row(row, cells, best_section, name_text)
                continue
            if mode == "team":
                self._team_row(row, cells, team_table, a, name_text)
                continue

            if a_text and not name_text and not others:
                parsed = parse_class(a)
                if parsed is None:
                    self.issue("UNRECOGNISED_ROW", Severity.WARNING,
                               f"cannot read {a_text!r} as a class row", row)
                    continue
                class_ctx = (parsed[0], parsed[1], parsed[2])
                if parsed[3]:
                    section_division = parsed[3]
                continue

            if not name_text:
                self.issue("UNRECOGNISED_ROW", Severity.WARNING, "row without a name", row)
                continue

            group = (section_no, class_ctx[0] if class_ctx else None)
            source = "heading" if sex_row_section == section else "inherited"
            try:
                lifter = self._athlete(row, cells, section, group, sex, source, equipment, class_ctx)
            except ValueError as exc:
                self.issue("ROW_UNPARSEABLE", Severity.ERROR, f"{exc}; row skipped", row)
                continue
            if source == "inherited":
                inherited += 1
            if (section_division and lifter.division != section_division
                    and lifter.status is not LifterStatus.GUEST):
                self.issue("DIVISION_SECTION_MISMATCH", Severity.WARNING,
                           f"{lifter.name}: division {lifter.division!r} under heading "
                           f"{section!r}", row)
            self.lifters.append(lifter)

        if inherited:
            self.issue("SEX_INHERITED", Severity.INFO,
                       f"{inherited} lifters have no sex heading of their own; the sex of the "
                       "last 'Жени'/'Мъже' heading was used (cross-checked against the points)")


    def _cell(self, cells: list, index: int):
        return cells[index] if index < len(cells) else None

    def _attempt(self, number: int, value, row: int) -> Attempt:
        if value is None or _clean(value) == "":
            return Attempt(number, "", None)
        raw = _clean(value)
        if isinstance(value, str) and raw.lower() in {"x", "х", "xx", "-", "–", "—"}:
            self.issue("ATTEMPT_MARKER", Severity.WARNING,
                       f"attempt cell {raw!r} has no weight; meaning not stated", row)
            return Attempt(number, raw, None)
        weight = _num(value)
        if weight is None or weight == 0:
            self.issue("ATTEMPT_ZERO", Severity.WARNING, f"attempt cell {raw!r} read as no weight", row)
            return Attempt(number, raw, None)
        if weight < 0:  # the file's convention: negative weight = failed lift
            return Attempt(number, raw, -weight, AttemptStatus.FAIL, StatusSource.EXPLICIT)
        return Attempt(number, raw, weight, AttemptStatus.GOOD, StatusSource.EXPLICIT)

    def _athlete(self, row, cells, section, group, sex, source, equipment, class_ctx) -> Lifter:
        place_raw = _clean(self._cell(cells, self.cols["place"]))
        category_cell = self._cell(cells, self.cols["category"])
        category_low = _low(category_cell)
        place = None
        status = LifterStatus.RANKED
        if category_low in GUEST_MARKERS:
            status = LifterStatus.GUEST
            if place_raw.upper() == "DQ":
                self.issue("GUEST_PLACE_PRINTED_DQ", Severity.INFO,
                           f"{_clean(self._cell(cells, self.name_col))}: place is printed 'DQ' "
                           "but the category is n/a, so the lifter is a guest", row)
            elif place_raw:
                self.issue("GUEST_HAS_PLACE", Severity.WARNING,
                           f"guest lifter has place {place_raw!r}", row)
        elif place_raw.upper() == "DQ":
            status = LifterStatus.DISQUALIFIED
        else:
            place = _int(self._cell(cells, self.cols["place"]))
            if place is None or place < 1:
                raise ValueError(f"place {place_raw!r} is not a place, 'DQ' or a guest marker")

        klass = parse_class(category_cell) if status is not LifterStatus.GUEST else None
        if status is not LifterStatus.GUEST and klass is None and category_low:
            self.issue("CATEGORY_UNREADABLE", Severity.WARNING,
                       f"category {category_low!r} is not a weight class", row)

        lifts = {}
        for lift in LIFTS:
            attempts = [self._attempt(n, self._cell(cells, col), row)
                        for n, col in enumerate(self.attempt_cols[lift], 1)]
            lifts[lift] = LiftResult(attempts, _num(self._cell(cells, self.cols[f"best_{lift}"])))

        club_col = self.cols["club"]
        return Lifter(
            row=row,
            section=section,
            group=group,
            sex=sex,
            sex_source=source,
            equipment=equipment,
            division=norm_division(self._cell(cells, self.cols["division"])),
            class_label=klass[0] if klass else None,
            class_context=class_ctx[0] if class_ctx else None,
            class_limit_kg=klass[1] if klass else None,
            class_floor_kg=klass[2] if klass else None,
            place_raw=place_raw,
            place=place,
            status=status,
            name=_clean(self._cell(cells, self.name_col)),
            club=_clean(self._cell(cells, club_col)),
            body_weight_kg=_num(self._cell(cells, self.cols["bw"])),
            lifts=lifts,
            total_kg=_num(self._cell(cells, self.cols["total"])),
            points=_num(self._cell(cells, self.points_col)),
            points_kind=self.points_kind,
            team_points=_int(self._cell(cells, self.cols["team_points"]))
            if "team_points" in self.cols else None,
        )

    # -- derived tables ----------------------------------------------------------------------

    def _best_row(self, row: int, cells: list, section: str, name: str) -> None:
        try:
            points = _num(self._cell(cells, self.name_col + 1))
        except ValueError:
            self.issue("DERIVED_ROW_UNPARSEABLE", Severity.WARNING,
                       "best-lifter row without numeric points", row)
            return
        self.best_lifters.append(
            StdBestLifter(row, section, name, points, _clean(self._cell(cells, self.name_col + 2)))
        )

    def _team_row(self, row: int, cells: list, table: str, place_cell, text: str) -> None:
        parsed = parse_team_text(text)
        if parsed is None:
            self.issue("DERIVED_ROW_UNPARSEABLE", Severity.WARNING,
                       f"team row {text!r} has no readable points", row)
            return
        club, scorers, total = parsed
        try:
            place = _int(place_cell)
        except ValueError:
            place = None
        self.team_rows.append(StdTeamRow(row, table, place, club, scorers, total, text))


def _read_rows(path: Path, sheet: str | None) -> tuple[str, list[tuple[int, list]]]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet is not None else wb.worksheets[0]
    return ws.title, [(i, list(r)) for i, r in enumerate(ws.iter_rows(values_only=True), 1)]

def _parse_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(_clean(value))
    except ValueError:
        return None


def parse_standard(path: str | Path, sheet: str | None = None) -> StandardMeet:
    path = Path(path)
    title_sheet, rows = _read_rows(path, sheet)
    parser = _Parser(rows)

    title = federation = city = None
    meet_date = None
    for _, cells in rows[:3]:
        texts = [_clean(c) for c in cells]
        if not any(texts):
            continue
        if title is None:
            title = texts[0]
            if m := CITY_RE.search(title):
                city = m["city"]
        elif federation is None:
            federation = texts[0]
            meet_date = _parse_date(cells[1]) if len(cells) > 1 else None
    if title is None:
        parser.issue("META_TITLE_MISSING", Severity.WARNING, "no title row")
    if meet_date is None:
        parser.issue("META_DATE_MISSING", Severity.WARNING,
                     "no ISO date next to the federation name on the second row")

    parser.run()
    raw_rows = {i: [_clean(c) for c in cells] for i, cells in rows if any(_clean(c) for c in cells)}
    return StandardMeet(
        sheet=title_sheet,
        title=title,
        federation=federation,
        city=city,
        date=meet_date,
        lifters=parser.lifters,
        team_rows=parser.team_rows,
        best_lifters=parser.best_lifters,
        raw_rows=raw_rows,
        issues=parser.issues,
        parser_version=PARSER_VERSION,
    )