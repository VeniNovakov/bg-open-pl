"""Regression test against the real standard-layout file (Gorna Oryahovitsa, 19-20.09.2026).
Opt-in: the file holds athlete names, so it is never committed. Run with
BGOPL_STD_FILE=/path/to/file.xlsx pytest tests/test_real_standard_file.py
"""

import os
from collections import Counter

import pytest

from bgopl.models import LifterStatus, Severity
from bgopl.parse_standard import parse_standard
from bgopl.validate_standard import validate_standard

PATH = os.environ.get("BGOPL_STD_FILE")
pytestmark = pytest.mark.skipif(not PATH, reason="BGOPL_STD_FILE not set")


def test_2026_gorna_oryahovitsa_full_power():
    meet = parse_standard(PATH)
    assert (meet.federation, meet.city, str(meet.date)) == ("БФСТ", "Горна Оряховица", "2026-09-19")
    assert len(meet.lifters) == 84
    assert Counter(x.status for x in meet.lifters) == {
        LifterStatus.RANKED: 82, LifterStatus.GUEST: 1, LifterStatus.DISQUALIFIED: 1}
    assert Counter(x.equipment for x in meet.lifters) == {"classic": 80, "equipped": 4}
    assert Counter(x.sex for x in meet.lifters) == {"M": 69, "F": 15}
    assert len(meet.team_rows) == 42 and len(meet.best_lifters) == 8

    found = Counter(
        (i.severity, i.code) for i in meet.issues + validate_standard(meet)
        if i.severity is not Severity.INFO
    )
    # Pinned findings (see docs/layout-standard.md). A change means the parser or the file changed.
    assert found == {
        (Severity.WARNING, "ATTEMPT_NOT_PLATE_INCREMENT"): 5,
        (Severity.WARNING, "TEAM_CLUB_UNKNOWN"): 4,
        (Severity.WARNING, "TEAM_POINTS_MISMATCH"): 3,
        (Severity.WARNING, "TEAM_SUM_MISMATCH"): 2,
    }
