from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .models import AttemptStatus, LifterStatus
from .parse_standard import parse_standard
from .validate_standard import validate_standard

LIFT_NAMES = {"S": "squat", "B": "bench", "D": "deadlift"}


def lifter_id(sex: str | None, name: str) -> str:
    return hashlib.sha256(f"{sex or '?'}|{name.casefold().strip()}".encode()).hexdigest()[:10]


def load_frames(directory: str | Path, include_names: bool = False):
    lifter_rows, attempt_rows, finding_rows = [], [], []
    folder = Path(directory)
    files = [p for p in sorted(folder.glob("*.xlsx")) if not p.name.startswith("~$")]
    if not files:
        raise FileNotFoundError(
            f"no .xlsx files in {folder.resolve()} (set BGOPL_DATA_DIR to the folder with the "
            "normalised results files)")
    for path in files:
        meet = parse_standard(path)
        meet_id = meet.date.isoformat() if meet.date else path.stem
        for issue in meet.issues + validate_standard(meet):
            finding_rows.append({"meet": meet_id, "code": issue.code,
                                 "severity": issue.severity.value})
        for x in meet.lifters:
            who = lifter_id(x.sex, x.name)
            row = {
                "meet": meet_id, "lifter_id": who, "sex": x.sex, "equipment": x.equipment,
                "division": x.division, "class_label": x.class_label,
                "status": x.status.value, "place": x.place, "club": x.club,
                "bodyweight": _f(x.body_weight_kg), "total": _f(x.total_kg),
                "points": _f(x.points),
            }
            if include_names:
                row["name"] = x.name
            for key, lift in LIFT_NAMES.items():
                row[f"best_{lift}"] = _f(x.lifts[key].best_kg)
            lifter_rows.append(row)
            for key, lift in LIFT_NAMES.items():
                for a in x.lifts[key].attempts:
                    if a.weight_kg is None:
                        continue
                    attempt_rows.append({
                        "meet": meet_id, "lifter_id": who, "sex": x.sex,
                        "equipment": x.equipment, "division": x.division, "lift": lift,
                        "attempt": a.number, "weight": float(a.weight_kg),
                        "good": a.status is AttemptStatus.GOOD,
                        "ranked": x.status is LifterStatus.RANKED})
    lifters = pd.DataFrame(lifter_rows)
    attempts = pd.DataFrame(attempt_rows)
    findings = pd.DataFrame(finding_rows)
    if not lifters.empty:
        lifters["meet"] = pd.Categorical(lifters["meet"], sorted(lifters["meet"].unique()),
                                         ordered=True)
    return lifters, attempts, findings


def _f(value):
    return None if value is None else float(value)