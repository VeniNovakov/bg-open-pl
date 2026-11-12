
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..models import Issue, Lifter, LifterStatus, StandardMeet
from ..parse_standard import parse_standard
from ..validate_standard import validate_standard


def _key(sex: str | None, name: str) -> tuple[str, str]:
    return (sex or "?", name.casefold().strip())


def read_suppressed(path: Path | None) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    if path is None or not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sex, _, name = line.partition("|") if "|" in line else ("*", "", line)
        out.add((sex.strip().upper() if sex != "*" else "*", name.casefold().strip()))
    return out

def _class_order(label: str) -> tuple[Decimal, int]:
    try:
        return Decimal(label.rstrip("+")), label.endswith("+")
    except InvalidOperation:
        return Decimal(10**6), False

@dataclass
class MeetRecord:
    slug: str
    source_name: str
    meet: StandardMeet
    lifters: list[Lifter]  # without suppressed lifters
    findings: list[Issue]  # without findings that point at suppressed lifters


@dataclass
class Store:
    suppressed: set[tuple[str, str]] = field(default_factory=set)
    meets: dict[str, MeetRecord] = field(default_factory=dict)
    failed: list[tuple[str, str]] = field(default_factory=list)

    def is_hidden(self, lifter: Lifter) -> bool:
        sex, name = _key(lifter.sex, lifter.name)
        return (sex, name) in self.suppressed or ("*", name) in self.suppressed

    def add_file(self, path: Path) -> None:
        try:
            meet = parse_standard(path)
        except Exception as exc:  # noqa: BLE001 - any unreadable file is skipped, never fatal
            self.failed.append((path.name, f"{type(exc).__name__}: {exc}"))
            return
        findings = meet.issues + validate_standard(meet)
        hidden_rows = {x.row for x in meet.lifters if self.is_hidden(x)}
        visible = [x for x in meet.lifters if x.row not in hidden_rows]
        findings = [i for i in findings if i.row not in hidden_rows]

        base = str(meet.date) if meet.date else "undated"
        slug, n = base, 2
        while slug in self.meets:
            slug, n = f"{base}-{n}", n + 1
        self.meets[slug] = MeetRecord(slug, path.name, meet, visible, findings)

    @classmethod
    def load_dir(cls, directory: str | Path, suppress_file: str | Path | None = None) -> Store:
        store = cls(suppressed=read_suppressed(Path(suppress_file) if suppress_file else None))
        folder = Path(directory)
        if folder.is_dir():
            for path in sorted(folder.glob("*.xlsx")):
                if not path.name.startswith("~$"):  # Excel lock files
                    store.add_file(path)
        else:
            store.failed.append((str(folder), "data folder not found"))
        return store

    # -- queries -----------------------------------------------------------------------------

    def athlete_results(self, sex: str, name: str) -> list[tuple[MeetRecord, Lifter]]:
        want = _key(None if sex == "U" else sex, name)
        out = [(rec, x) for rec in self.meets.values() for x in rec.lifters
               if _key(x.sex, x.name) == want]
        return sorted(out, key=lambda t: t[0].slug, reverse=True)

    def rankings(self, sex: str | None = None, equipment: str = "classic",
                 division: str | None = None, weight_class: str | None = None) -> list[tuple[MeetRecord, Lifter]]:
        best: dict[tuple[str, str], tuple[MeetRecord, Lifter]] = {}
        for rec in self.meets.values():
            for x in rec.lifters:
                if (x.status is not LifterStatus.RANKED or x.points is None
                        or x.equipment != equipment
                        or (sex and x.sex != sex) or (division and x.division != division)
                        or (weight_class and x.class_label != weight_class)):
                    continue
                key = _key(x.sex, x.name)
                if key not in best or x.points > best[key][1].points:
                    best[key] = (rec, x)

        return sorted(best.values(), key=lambda t: (-t[1].points, t[1].name))

    def weight_classes(self, sex: str | None = None, equipment: str = "classic",
    division: str | None = None) -> list[str]:
        labels = {x.class_label for rec in self.meets.values() for x in rec.lifters
            if x.status is LifterStatus.RANKED and x.points is not None
            and x.class_label and x.equipment == equipment
            and (not sex or x.sex == sex) and (not division or x.division == division)}
        return sorted(labels, key=_class_order)
