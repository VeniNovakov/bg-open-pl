from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from itertools import pairwise

from .models import (
    AttemptStatus,
    Issue,
    Lifter,
    LifterStatus,
    Severity,
    StandardMeet,
)
from .points import ipf_gl_points

PLATE_STEP = Decimal("2.5")
POINTS_TOLERANCE = Decimal("0.011")
TEAM_POINTS_BY_PLACE = {1: 12, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}
LIFT_NAMES = {"S": "squat", "B": "bench", "D": "deadlift"}


def _issue(code: str, severity: Severity, message: str, lifter: Lifter | None = None) -> Issue:
    return Issue(code, severity, message, lifter.row if lifter else None)


def _who(lifter: Lifter) -> str:
    return f"{lifter.name} ({lifter.section}, {lifter.class_label or 'no class'})"


def _same_club(a: str, b: str) -> bool:
    x, y = a.casefold().strip(), b.casefold().strip()
    return bool(x) and bool(y) and (x == y or x in y or y in x)


def _check_lifts(lifter: Lifter) -> list[Issue]:
    out: list[Issue] = []
    who = _who(lifter)
    for key, lift in lifter.lifts.items():
        name = LIFT_NAMES[key]
        good = lift.good_weights
        expected = max(good) if good else None
        if lift.best_kg != expected:
            out.append(_issue(
                "BEST_NOT_MAX_GOOD", Severity.ERROR,
                f"{who}: {name} best is {lift.best_kg}, the heaviest good attempt is {expected}",
                lifter))

        weights = [a.weight_kg for a in lift.attempts]
        for a in lift.attempts:
            if a.weight_kg is not None and a.weight_kg % PLATE_STEP:
                out.append(_issue(
                    "ATTEMPT_NOT_PLATE_INCREMENT", Severity.WARNING,
                    f"{who}: {name} attempt {a.number} is {a.weight_kg} kg, not a multiple of "
                    f"{PLATE_STEP}", lifter))
        for i in range(2):
            if weights[i] is None and weights[i + 1] is not None:
                out.append(_issue(
                    "ATTEMPT_GAP", Severity.WARNING,
                    f"{who}: {name} attempt {i + 2} has a weight but attempt {i + 1} is empty",
                    lifter))
        done = [a for a in lift.attempts if a.weight_kg is not None]
        for prev, nxt in pairwise(done):
            if nxt.weight_kg < prev.weight_kg:
                out.append(_issue(
                    "ATTEMPT_WEIGHT_DECREASES", Severity.WARNING,
                    f"{who}: {name} attempt {nxt.number} ({nxt.weight_kg}) is lighter than "
                    f"attempt {prev.number} ({prev.weight_kg})", lifter))
            elif prev.status is AttemptStatus.GOOD and nxt.weight_kg == prev.weight_kg:
                out.append(_issue(
                    "ATTEMPT_NOT_INCREASED_AFTER_GOOD_LIFT", Severity.WARNING,
                    f"{who}: {name} attempt {nxt.number} repeats {prev.weight_kg} kg after a "
                    "good lift", lifter))
    return out


def _check_total_and_points(lifter: Lifter) -> list[Issue]:
    out: list[Issue] = []
    who = _who(lifter)
    bests = [lift.best_kg for lift in lifter.lifts.values()]
    if all(b is not None for b in bests):
        total = sum(bests, Decimal(0))
        if lifter.total_kg is None:
            out.append(_issue("TOTAL_MISSING", Severity.ERROR,
                              f"{who}: all three lifts have a best ({total} kg) but no total",
                              lifter))
        elif lifter.total_kg != total:
            out.append(_issue("TOTAL_MISMATCH", Severity.ERROR,
                              f"{who}: total {lifter.total_kg} but the bests add up to {total}",
                              lifter))
    elif lifter.total_kg is not None:
        out.append(_issue("TOTAL_WITHOUT_ALL_LIFTS", Severity.WARNING,
                          f"{who}: total {lifter.total_kg} printed although a lift has no good "
                          "attempt", lifter))

    if lifter.status is not LifterStatus.RANKED:
        if lifter.points is not None or lifter.team_points not in (None, 0):
            out.append(_issue("POINTS_FOR_UNRANKED", Severity.WARNING,
                              f"{who}: {lifter.status.value} lifter has points", lifter))
        return out

    if lifter.total_kg is None:
        return out
    if lifter.points is None:
        out.append(_issue("POINTS_MISSING", Severity.ERROR,
                          f"{who}: ranked with total {lifter.total_kg} but no points", lifter))
        return out
    if lifter.body_weight_kg is None or lifter.sex is None:
        return out
    for sex in ("F", "M"):
        calc = ipf_gl_points(sex, lifter.equipment, lifter.body_weight_kg, lifter.total_kg)
        if calc is not None and abs(calc - lifter.points) <= POINTS_TOLERANCE:
            if sex != lifter.sex:
                out.append(_issue(
                    "SEX_MISMATCH", Severity.ERROR,
                    f"{who}: the printed points fit the {sex} coefficients, but the section says "
                    f"{lifter.sex}", lifter))
            return out
    calc = ipf_gl_points(lifter.sex, lifter.equipment, lifter.body_weight_kg, lifter.total_kg)
    if calc is None:
        out.append(_issue("POINTS_NOT_CHECKED", Severity.INFO,
                          f"{who}: no IPF GL coefficients for {lifter.sex} {lifter.equipment}",
                          lifter))
    else:
        out.append(_issue(
            "POINTS_MISMATCH", Severity.ERROR,
            f"{who}: printed {lifter.points} but IPF GL for {lifter.total_kg} kg at "
            f"{lifter.body_weight_kg} kg is {calc:.2f}; bodyweight, total or points is wrong",
            lifter))
    return out


def _class_floors(meet: StandardMeet) -> dict[tuple, list[Decimal]]:
    limits: dict[tuple, set[Decimal]] = defaultdict(set)
    for lifter in meet.lifters:
        if lifter.status is LifterStatus.GUEST or lifter.sex is None:
            continue
        if lifter.class_limit_kg is not None:
            limits[(lifter.sex,)].add(lifter.class_limit_kg)
        if lifter.class_floor_kg is not None:
            limits[(lifter.sex,)].add(lifter.class_floor_kg)
    return {k: sorted(v) for k, v in limits.items()}


def _check_classes(meet: StandardMeet) -> list[Issue]:
    out: list[Issue] = []
    observed = _class_floors(meet)
    for lifter in meet.lifters:
        if lifter.status is LifterStatus.GUEST or lifter.body_weight_kg is None:
            continue
        who = _who(lifter)
        bw = lifter.body_weight_kg
        if lifter.class_limit_kg is not None and bw > lifter.class_limit_kg:
            out.append(_issue("BODYWEIGHT_OUTSIDE_CLASS", Severity.ERROR,
                              f"{who}: bodyweight {bw} above class limit {lifter.class_limit_kg}",
                              lifter))
        floor = lifter.class_floor_kg
        if floor is None and lifter.class_limit_kg is not None and lifter.sex:
            lower = [x for x in observed.get((lifter.sex,), []) if x < lifter.class_limit_kg]
            floor = lower[-1] if lower else None
        if floor is not None and bw <= floor:
            out.append(_issue("BODYWEIGHT_BELOW_CLASS", Severity.ERROR,
                              f"{who}: bodyweight {bw} is not above {floor}, so the lifter "
                              "belongs in a lighter class", lifter))
        if (lifter.class_context is not None and lifter.class_label is not None
                and lifter.class_context != lifter.class_label):
            out.append(_issue("CLASS_CELL_DIFFERS_FROM_HEADING", Severity.WARNING,
                              f"{who}: category cell {lifter.class_label!r} under class row "
                              f"{lifter.class_context!r}", lifter))
    return out


def _check_places(meet: StandardMeet) -> list[Issue]:
    out: list[Issue] = []
    groups: dict[tuple, list[Lifter]] = defaultdict(list)
    for lifter in meet.lifters:
        if lifter.status is LifterStatus.RANKED and lifter.place is not None:
            groups[lifter.group].append(lifter)
    for group, lifters in groups.items():
        first = lifters[0]
        label = f"{first.section} / {group[1] or 'all classes'}"
        places = sorted(lifter.place for lifter in lifters)
        if places != list(range(1, len(lifters) + 1)):
            out.append(_issue("PLACE_SEQUENCE_BROKEN", Severity.WARNING,
                              f"{label}: places are {places}, expected 1..{len(lifters)}", first))
        mixed = group[1] is None  # a block ranked across classes is ordered by points
        ordered = sorted(lifters, key=lambda x: x.place)
        keys = []
        for lifter in ordered:
            if mixed:
                keys.append((-(lifter.points or Decimal(0)),))
            else:
                keys.append((-(lifter.total_kg or Decimal(0)), lifter.body_weight_kg or Decimal(0)))
        for (lo, key_lo), (hi, key_hi) in zip(
                zip(ordered, keys, strict=True), list(zip(ordered, keys, strict=True))[1:],
                strict=False):
            if key_hi < key_lo:
                out.append(_issue(
                    "PLACE_ORDER_INCONSISTENT", Severity.WARNING,
                    f"{label}: {hi.name} (place {hi.place}) beats {lo.name} (place {lo.place}) "
                    + ("on points" if mixed else "on total, then lighter bodyweight"), hi))
    return out


def _check_duplicates(meet: StandardMeet) -> list[Issue]:
    seen: dict[tuple, Lifter] = {}
    out = []
    for lifter in meet.lifters:
        key = (lifter.name.casefold(), lifter.sex, lifter.equipment)
        if key in seen:
            out.append(_issue("DUPLICATE_LIFTER_IN_MEET", Severity.WARNING,
                              f"{lifter.name} appears twice in the same block "
                              f"(rows {seen[key].row} and {lifter.row})", lifter))
        else:
            seen[key] = lifter
    return out


def _check_team_points(meet: StandardMeet) -> list[Issue]:
    out: list[Issue] = []
    if all(x.team_points is None for x in meet.lifters):
        return out 
    
    beyond: dict[bool, list[int]] = {True: [], False: []}
    for lifter in meet.lifters:
        if lifter.status is not LifterStatus.RANKED or lifter.place is None:
            continue
        if lifter.place in TEAM_POINTS_BY_PLACE:
            if lifter.team_points != TEAM_POINTS_BY_PLACE[lifter.place]:
                out.append(_issue(
                    "TEAM_POINTS_NOT_BY_SCALE", Severity.WARNING,
                    f"{_who(lifter)}: place {lifter.place} has {lifter.team_points} team points, "
                    f"the scale gives {TEAM_POINTS_BY_PLACE[lifter.place]}", lifter))
        else:
            beyond[bool(lifter.team_points)].append(lifter.place)
    if beyond[True]:
        out.append(Issue("TEAM_POINTS_BEYOND_TENTH", Severity.INFO,
                         f"places {sorted(beyond[True])} score team points although the usual "
                         f"scale stops at 10; places {sorted(beyond[False])} score none"))
    return out


def _check_team_tables(meet: StandardMeet) -> list[Issue]:
    out: list[Issue] = []
    clubs = sorted({lifter.club for lifter in meet.lifters if lifter.club})
    variants: dict[str, list[str]] = {}
    sexes = {"women": "F", "men": "M", "жени": "F", "мъже": "M"}

    for team in meet.team_rows:
        where = f"team table '{team.table}', {team.club}"
        row = team.row
        if team.printed_total is not None and sum(team.scorers) != team.printed_total:
            out.append(Issue("TEAM_SUM_MISMATCH", Severity.WARNING,
                             f"{where}: {'+'.join(map(str, team.scorers))} adds up to "
                             f"{sum(team.scorers)}, the table says {team.printed_total}", row))
        matched = [c for c in clubs if _same_club(team.club, c)]
        if not matched:
            out.append(Issue("TEAM_CLUB_UNKNOWN", Severity.WARNING,
                             f"{where}: no athlete row has a club with this name", row))
            continue
        if all(team.club.casefold().strip() != c.casefold().strip() for c in matched):
            variants[team.club] = matched
        entry_points = sorted(
            (lifter.team_points for lifter in meet.lifters
             if lifter.team_points and lifter.club in matched
             and (team.table == "overall"
                  or (lifter.sex == sexes[team.table] and lifter.equipment != "equipped"))),
            reverse=True)
        table_points = sorted((p for p in team.scorers if p), reverse=True)
        if entry_points != table_points:
            out.append(Issue("TEAM_POINTS_MISMATCH", Severity.WARNING,
                             f"{where}: table scores {table_points}, the athlete rows give "
                             f"{entry_points}", row))
    if variants:
        pairs = "; ".join(f"{k!r} = {v}" for k, v in sorted(variants.items()))
        out.append(Issue("TEAM_CLUB_NAME_VARIANT", Severity.INFO,
                         f"the team tables spell {len(variants)} clubs differently from the "
                         f"athlete rows: {pairs}"))
    return out


def _check_best_lifters(meet: StandardMeet) -> list[Issue]:
    out: list[Issue] = []
    by_section: dict[str, list] = defaultdict(list)
    for best in meet.best_lifters:
        by_section[best.section].append(best)
    for section, bests in by_section.items():
        low = section.lower()
        sex = "F" if low.startswith(("жени", "women")) else "M" if low.startswith(("мъже", "men")) else None
        veterans = "ветеран" in low
        pool = [x for x in meet.lifters
                if x.sex == sex and x.status is LifterStatus.RANKED and x.points is not None
                and x.equipment == "classic" and (x.division != "Open") == veterans]
        ranked = sorted(pool, key=lambda x: -x.points)

        expected = ranked[: len(bests)]
        if not veterans and len(bests) < min(3, len(ranked)):
            out.append(Issue("BEST_LIFTERS_SHORT", Severity.WARNING,
                             f"'{section}': {len(bests)} listed, expected {min(3, len(ranked))}",
                             bests[0].row))
        if [b.name for b in bests] != [x.name for x in expected]:
            out.append(Issue("BEST_LIFTERS_MISMATCH", Severity.WARNING,
                             f"'{section}': table lists {[b.name for b in bests]}, the top "
                             f"points in the athlete rows are {[x.name for x in expected]}",
                             bests[0].row))
        by_name = {x.name: x for x in meet.lifters}
        for best in bests:
            lifter = by_name.get(best.name)
            if lifter is None:
                out.append(Issue("BEST_LIFTER_UNKNOWN", Severity.WARNING,
                                 f"'{section}': {best.name} is not an athlete row", best.row))
            elif (best.points is None or lifter.points is None
                  or abs(best.points - lifter.points) > POINTS_TOLERANCE):
                out.append(Issue("BEST_LIFTER_POINTS_MISMATCH", Severity.WARNING,
                                 f"'{section}': {best.name} has {best.points} here and "
                                 f"{lifter.points} in the athlete rows", best.row))
    return out


def validate_standard(meet: StandardMeet) -> list[Issue]:
    issues: list[Issue] = []
    for lifter in meet.lifters:
        issues.extend(_check_lifts(lifter))
        issues.extend(_check_total_and_points(lifter))
    issues.extend(_check_classes(meet))
    issues.extend(_check_places(meet))
    issues.extend(_check_duplicates(meet))
    issues.extend(_check_team_points(meet))
    issues.extend(_check_team_tables(meet))
    issues.extend(_check_best_lifters(meet))
    counts = Counter(lifter.status for lifter in meet.lifters)
    issues.append(Issue("SUMMARY", Severity.INFO,
                        f"{len(meet.lifters)} lifters: {counts[LifterStatus.RANKED]} ranked, "
                        f"{counts[LifterStatus.GUEST]} guest, "
                        f"{counts[LifterStatus.DISQUALIFIED]} disqualified"))
    return issues