"""Parse a standard-layout results file and print every lifter.

    python -m bgopl.main results.xlsx            # lifters, then a findings summary
    python -m bgopl.main results.xlsx --issues   # also list every finding
    python -m bgopl.main results.xlsx --status guest   # only guest / disqualified / ranked
    python -m bgopl.main results.xlsx --file-order     # the order of the sheet, not by category

By default lifters are grouped by sex, equipment, division and weight class, and listed by total
(highest first, equal totals by the lighter lifter) inside each group. Lifters without a total
(no valid lift, disqualified) come last in their class; guests are listed after the classes.

The output holds athlete names, so it is meant for the terminal, not for committing.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from .models import LifterStatus, Severity, StandardMeet
from .parse_standard import parse_standard
from .validate_standard import validate_standard
from .views import COLUMNS, NUMERIC_COLUMNS, group_lifters, lifter_cells


def format_lifters(meet: StandardMeet, status: str | None = None, by_class: bool = True) -> str:
    """The lifter table. Grouped by weight class and sorted by total unless by_class is False,
    which keeps the order of the sheet with a header whenever the section changes."""
    chosen = [(i, x) for i, x in enumerate(meet.lifters, 1) if status in (None, x.status.value)]
    if by_class:
        index_of = {id(x): i for i, x in chosen}
        blocks = [(h, [(index_of[id(x)], x) for x in members])
                  for h, members in group_lifters([x for _, x in chosen])]
    else:
        blocks, current = [], None
        for i, x in chosen:
            if x.group[0] != current:
                current = x.group[0]
                blocks.append((f"{x.section} ({x.equipment})", []))
            blocks[-1][1].append((i, x))

    table = {i: [str(i), *lifter_cells(x)] for _, members in blocks for i, x in members}
    widths = [max(len(COLUMNS[c]), *(len(r[c]) for r in table.values())) if table
              else len(COLUMNS[c]) for c in range(len(COLUMNS))]
    numeric = NUMERIC_COLUMNS

    def fmt(cells: list[str]) -> str:
        return "  ".join(
            cell.rjust(widths[c]) if c in numeric else cell.ljust(widths[c])
            for c, cell in enumerate(cells)
        ).rstrip()

    lines = [fmt(list(COLUMNS))]
    for header, members in blocks:
        lines.append(f"-- {header} --")
        lines.extend(fmt(table[i]) for i, _ in members)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bgopl.main", description=__doc__.splitlines()[0])
    parser.add_argument("file", help="standard-layout .xlsx file")
    parser.add_argument("--sheet", help="worksheet name (default: the first sheet)")
    parser.add_argument("--status", choices=[s.value for s in LifterStatus],
                        help="only print lifters with this status")
    parser.add_argument("--issues", action="store_true", help="list every finding")
    parser.add_argument("--file-order", action="store_true",
                        help="keep the order of the sheet instead of grouping by weight class")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        meet = parse_standard(args.file, args.sheet)
    except (ValueError, KeyError, OSError) as exc:
        print(f"cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    issues = meet.issues + validate_standard(meet)

    print(f"{meet.title or '(no title)'}")
    print(f"{meet.federation or '?'} | {meet.city or '?'} | {meet.date or '?'}")
    print()
    print(format_lifters(meet, args.status, by_class=not args.file_order))
    print()
    counts = Counter(x.status for x in meet.lifters)
    print(f"{len(meet.lifters)} lifters: {counts[LifterStatus.RANKED]} ranked, "
          f"{counts[LifterStatus.GUEST]} guest, {counts[LifterStatus.DISQUALIFIED]} disqualified")
    by_severity = Counter(i.severity for i in issues if i.code != "SUMMARY")
    print("findings: " + ", ".join(
        f"{by_severity[s]} {s.value}" for s in (Severity.ERROR, Severity.WARNING, Severity.INFO)))
    if args.issues:
        print()
        order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
        for i in sorted((x for x in issues if x.code != "SUMMARY"),
                        key=lambda x: (order[x.severity], x.row or 0)):
            where = f"row {i.row}" if i.row else "file"
            print(f"  {i.severity.value.upper():7} {i.code:34} {where:8} {i.message}")
    return 1 if any(i.severity is Severity.ERROR for i in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())