"""Validator paths the main tests leave out. One defect per workbook, as in test_standard."""

from helpers_standard import clean_blocks, klass, lifter, section, write_standard

from bgopl.models import LifterStatus, Severity
from bgopl.parse_standard import parse_standard
from bgopl.validate_standard import validate_standard


def findings(tmp_path, blocks):
    meet = parse_standard(write_standard(tmp_path / "meet.xlsx", blocks))
    return meet, validate_standard(meet)


def codes(issues):
    return [i.code for i in issues if i.code != "SUMMARY"]


def test_a_file_without_any_team_points_gets_no_team_findings(tmp_path):
    blocks = [section("Women "), klass(63.0),
              lifter("Anna", 60.0, [100, 105, 110], [60, 62.5, 65], [120, 125, 130],
                     place=1, category=63.0, team=None),
              lifter("Bella", 62.0, [90, 95, 100], [50, 55, 57.5], [110, 115, 120],
                     place=2, category=63.0, team=None)]
    _, issues = findings(tmp_path, blocks)
    assert not [c for c in codes(issues) if c.startswith("TEAM_")]


def test_a_missing_team_point_is_still_flagged_when_other_rows_have_them(tmp_path):
    blocks = [section("Women "), klass(63.0),
              lifter("Anna", 60.0, [100, 105, 110], [60, 62.5, 65], [120, 125, 130],
                     place=1, category=63.0),
              lifter("Bella", 62.0, [90, 95, 100], [50, 55, 57.5], [110, 115, 120],
                     place=2, category=63.0, team=None)]
    _, issues = findings(tmp_path, blocks)
    assert codes(issues) == ["TEAM_POINTS_NOT_BY_SCALE"]


def test_all_three_lifts_good_but_no_total_is_an_error(tmp_path):
    blocks = [section("Women "), klass(63.0),
              lifter("Anna", 60.0, [100, 105, 110], [60, 62.5, 65], [120, 125, 130],
                     place=1, category=63.0, total=None)]
    _, issues = findings(tmp_path, blocks)
    assert "TOTAL_MISSING" in codes(issues)
    assert next(i for i in issues if i.code == "TOTAL_MISSING").severity is Severity.ERROR


def test_a_total_next_to_a_failed_lift_is_flagged(tmp_path):
    blocks = [section("Women "), klass(63.0),
              lifter("Anna", 60.0, [-100, -105, -110], [60, 62.5, 65], [120, 125, 130],
                     place=1, category=63.0, total=185, points=None)]
    _, issues = findings(tmp_path, blocks)
    assert "TOTAL_WITHOUT_ALL_LIFTS" in codes(issues)


def test_a_disqualified_lifter_with_points_is_flagged(tmp_path):
    blocks = [section("Men"), klass(74.0),
              lifter("Victor", 73.0, [200, 210, 220], [140, 145, -150], [230, 240, 250],
                     place="DQ", sex="M", category=74.0, points=95.0, team=None)]
    meet, issues = findings(tmp_path, blocks)
    assert meet.lifters[0].status is LifterStatus.DISQUALIFIED
    assert "POINTS_FOR_UNRANKED" in codes(issues)


def test_a_clean_guest_or_disqualified_lifter_adds_nothing(tmp_path):
    meet, issues = findings(tmp_path, clean_blocks())
    assert {x.status for x in meet.lifters} >= {LifterStatus.GUEST, LifterStatus.RANKED}
    assert codes(issues) == []


def test_the_summary_counts_the_statuses(tmp_path):
    _, issues = findings(tmp_path, clean_blocks())
    summary = next(i for i in issues if i.code == "SUMMARY")
    assert summary.message == "7 lifters: 6 ranked, 1 guest, 0 disqualified"
    assert summary.severity is Severity.INFO
