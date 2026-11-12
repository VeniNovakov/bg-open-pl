from decimal import Decimal

import pytest
from helpers_standard import (
    clean_blocks,
    klass,
    lifter,
    section,
    write_standard,
)

from bgopl.models import AttemptStatus, LifterStatus, Severity
from bgopl.parse_standard import parse_standard, parse_team_text
from bgopl.validate_standard import validate_standard


def parsed(tmp_path, blocks=None, **kw):
    return parse_standard(write_standard(tmp_path / "s.xlsx", blocks or clean_blocks(), **kw))


def found(tmp_path, blocks, **kw):
    meet = parsed(tmp_path, blocks, **kw)
    return meet, meet.issues + validate_standard(meet)


def codes(issues):
    return {i.code for i in issues}


# -- parsing ---------------------------------------------------------------------------------


def test_meet_metadata(tmp_path):
    meet = parsed(tmp_path)
    assert meet.federation == "BPF" and str(meet.date) == "2026-01-01" and meet.city == "Sofia"


def test_lifters_sections_sex_and_classes(tmp_path):
    meet = parsed(tmp_path)
    assert len(meet.lifters) == 7
    by_name = {x.name: x for x in meet.lifters}
    ana = by_name["Anna First"]
    assert (ana.sex, ana.sex_source, ana.division, ana.class_label) == ("F", "heading", "Open", "63")
    assert ana.class_limit_kg == Decimal(63) and ana.class_context == "63"
    assert ana.place == 1 and ana.status is LifterStatus.RANKED and ana.club == "Club Alpha"
    assert ana.lifts["S"].best_kg == Decimal(105) and ana.total_kg == Decimal(300)
    veteran = by_name["Emil Veteran"]
    assert veteran.sex == "M" and veteran.sex_source == "inherited"
    assert veteran.division == "M1" and veteran.class_context == "74"


def test_negative_weight_is_a_failed_attempt(tmp_path):
    ana = parsed(tmp_path).lifters[0]
    third = ana.lifts["S"].attempts[2]
    assert (third.weight_kg, third.status) == (Decimal(110), AttemptStatus.FAIL)
    assert ana.lifts["S"].attempts[0].status is AttemptStatus.GOOD


def test_guest_is_recognised_by_category_even_when_place_says_dq(tmp_path):
    meet, issues = found(tmp_path, clean_blocks())
    guest = next(x for x in meet.lifters if x.name == "Guest Person")
    assert guest.status is LifterStatus.GUEST and guest.place is None
    assert guest.class_label is None
    assert "GUEST_PLACE_PRINTED_DQ" in codes(issues)
    assert not [i for i in issues if i.severity is not Severity.INFO]


def test_dq_with_a_class_is_disqualified(tmp_path):
    blocks = [section("Men"), klass(83.0),
              lifter("Dan Disqualified", 82.0, [200, 210, -220], [100, -110, -110],
                     [200, 210, 220], place="DQ", sex="M", category=83.0, bests=(210, 100, 220),
                     total=None, points=None, team=None)]
    lifter_ = parsed(tmp_path, blocks).lifters[0]
    assert lifter_.status is LifterStatus.DISQUALIFIED and lifter_.place is None
    assert lifter_.status is not LifterStatus.GUEST and lifter_.class_label == "83"


def test_open_ended_class(tmp_path):
    blocks = [section("Men"), klass("120+"),
              lifter("Big Man", 130.0, [250, 260, 270], [150, 160, 170], [250, 260, 270],
                     category="120+", sex="M")]
    big = parsed(tmp_path, blocks).lifters[0]
    assert big.class_label == "120+" and big.class_limit_kg is None
    assert big.class_floor_kg == Decimal(120)


def test_equipped_block_has_no_class_context(tmp_path):
    blocks = [section("Men"), section("Champion of champions equipped powerlifting "),
              lifter("Equip One", 109.0, [300, 320, 330], [200, 210, 220], [300, 310, 320],
                     category=120.0, sex="M", equipment="equipped")]
    x = parsed(tmp_path, blocks).lifters[0]
    assert x.equipment == "equipped" and x.class_context is None and x.class_label == "120"
    assert x.sex == "M" and x.sex_source == "inherited"


def test_unreadable_row_is_reported_and_skipped(tmp_path):
    blocks = clean_blocks()
    blocks[2][4] = "many"  # bodyweight of the first lifter
    meet = parsed(tmp_path, blocks)
    assert len(meet.lifters) == 6
    assert any(i.code == "ROW_UNPARSEABLE" and i.severity is Severity.ERROR for i in meet.issues)


def test_missing_header_row_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="header"):
        parsed(tmp_path, header=False)


@pytest.mark.parametrize(("text", "expected"), [
    ("Strength Squad  12+7+12‎ =31", ("Strength Squad", [12, 7, 12], 31)),
    ("NSA =  12+12+12+5+2+1+12=66", ("NSA", [12, 12, 12, 5, 2, 1, 12], 66)),
    ("Flex - 12+12+6+4+9+12=55", ("Flex", [12, 12, 6, 4, 9, 12], 55)),
    ("Marek 13 = 8+8+6+6‎ = 28", ("Marek 13", [8, 8, 6, 6], 28)),
    ("CSKA-89  9+8+9+12=38", ("CSKA-89", [9, 8, 9, 12], 38)),
    ("Olympia Morava = 9", ("Olympia Morava", [9], 9)),
    ("Marek 13 = 0", ("Marek 13", [0], 0)),
    ("Lokomotiv Olymp 12", ("Lokomotiv Olymp", [12], None)),
    ("Power Deadlift  - 0", ("Power Deadlift", [0], None)),
    ("Strength Squad  12+7+‎ = 19", ("Strength Squad", [12, 7], 19)),
])
def test_team_text_variants(text, expected):
    assert parse_team_text(text) == expected


def test_team_text_without_numbers_is_not_a_team_row():
    assert parse_team_text("Just text") is None


# -- validation ------------------------------------------------------------------------------


def test_clean_fixture_has_no_warnings_or_errors(tmp_path):
    _, issues = found(tmp_path, clean_blocks())
    assert [i for i in issues if i.severity is not Severity.INFO] == []


def test_best_must_be_the_heaviest_good_attempt(tmp_path):
    blocks = clean_blocks()
    blocks[2][9] = 100  # squat best of Anna: attempts 100, 105, -110
    _, issues = found(tmp_path, blocks)
    assert "BEST_NOT_MAX_GOOD" in codes(issues)


def test_total_must_be_the_sum_of_bests(tmp_path):
    blocks = clean_blocks()
    blocks[2][18] = 999
    _, issues = found(tmp_path, blocks)
    assert "TOTAL_MISMATCH" in codes(issues)


def test_points_are_checked_against_ipf_gl(tmp_path):
    blocks = clean_blocks()
    blocks[2][19] = 80.0
    hit = [i for i in found(tmp_path, blocks)[1] if i.code == "POINTS_MISMATCH"]
    assert hit and hit[0].severity is Severity.ERROR


def test_ranked_lifter_without_points(tmp_path):
    blocks = clean_blocks()
    blocks[2][19] = None
    assert "POINTS_MISSING" in codes(found(tmp_path, blocks)[1])


def test_points_that_fit_the_other_sex_flag_the_section(tmp_path):
    blocks = [section("Women "), klass(83.0),
              lifter("Wrong Section", 80.0, [190, 200, 210], [130, 135, 140], [220, 230, 240],
                     category=83.0, sex="M")]
    assert "SEX_MISMATCH" in codes(found(tmp_path, blocks)[1])


def test_attempt_rules(tmp_path):
    blocks = [section("Men"), klass(83.0),
              lifter("Irregular One", 80.0, [190, 200.5, 210], [130, 125, 140], [220, 220, -230],
                     category=83.0, sex="M"),
              ]
    blocks[2][11] = None  # bench attempt 2 empty although attempt 3 has a weight
    blocks[2][10] = 130
    issues = codes(found(tmp_path, blocks)[1])
    assert {"ATTEMPT_NOT_PLATE_INCREMENT", "ATTEMPT_GAP",
            "ATTEMPT_NOT_INCREASED_AFTER_GOOD_LIFT"} <= issues


def test_attempt_that_goes_down(tmp_path):
    blocks = [section("Men"), klass(83.0),
              lifter("Irregular Two", 80.0, [200, 190, 210], [130, 135, 140], [220, 230, 240],
                     category=83.0, sex="M")]
    assert "ATTEMPT_WEIGHT_DECREASES" in codes(found(tmp_path, blocks)[1])


def test_bodyweight_above_and_below_the_class(tmp_path):
    blocks = [section("Men"), klass(74.0),
              lifter("Heavy One", 75.0, [190, 200, 210], [130, 135, 140], [220, 230, 240],
                     place=1, category=74.0, sex="M"),
              klass(83.0),
              lifter("Light One", 70.0, [190, 200, 210], [130, 135, 140], [220, 230, 240],
                     place=1, category=83.0, sex="M")]
    issues = codes(found(tmp_path, blocks)[1])
    assert {"BODYWEIGHT_OUTSIDE_CLASS", "BODYWEIGHT_BELOW_CLASS"} <= issues


def test_guest_is_exempt_from_class_checks(tmp_path):
    issues = codes(found(tmp_path, clean_blocks())[1])  # the guest weighs 90 in a 74 block
    assert "BODYWEIGHT_OUTSIDE_CLASS" not in issues


def test_class_cell_that_differs_from_the_class_row(tmp_path):
    blocks = [section("Men"), klass(74.0),
              lifter("Wrong Class", 73.0, [190, 200, 210], [130, 135, 140], [220, 230, 240],
                     category=83.0, sex="M")]
    assert "CLASS_CELL_DIFFERS_FROM_HEADING" in codes(found(tmp_path, blocks)[1])


def test_places_must_run_without_gaps(tmp_path):
    blocks = clean_blocks()
    blocks[3][0] = 3
    assert "PLACE_SEQUENCE_BROKEN" in codes(found(tmp_path, blocks)[1])


def test_higher_total_must_not_be_placed_lower(tmp_path):
    blocks = clean_blocks()
    blocks[2][0], blocks[3][0] = 2, 1  # Anna (300 kg) now behind Bella (285 kg)
    assert "PLACE_ORDER_INCONSISTENT" in codes(found(tmp_path, blocks)[1])


def test_equal_totals_are_ordered_by_the_lighter_lifter(tmp_path):
    def row(name, bw, place):
        return lifter(name, bw, [200, 210, 220], [130, 135, 140], [220, 230, 240],
                      place=place, category=83.0, sex="M")

    ok = [section("Men"), klass(83.0), row("Light", 80.0, 1), row("Heavy", 82.0, 2)]
    bad = [section("Men"), klass(83.0), row("Light", 80.0, 2), row("Heavy", 82.0, 1)]
    assert "PLACE_ORDER_INCONSISTENT" not in codes(found(tmp_path, ok)[1])
    assert "PLACE_ORDER_INCONSISTENT" in codes(found(tmp_path, bad)[1])


def test_equipped_block_is_ranked_across_classes_by_points(tmp_path):
    def row(name, bw, cls, place, total_lift):
        return lifter(name, bw, [total_lift, total_lift + 10, total_lift + 20],
                      [150, 160, 170], [250, 260, 270], place=place, category=cls,
                      sex="M", equipment="equipped")

    head = [section("Men"), section("Champion of champions equipped powerlifting ")]
    ok = head + [row("Equip One", 109.0, 120.0, 1, 300), row("Equip Two", 90.0, 93.0, 2, 200)]
    bad = head + [row("Equip One", 109.0, 120.0, 2, 300), row("Equip Two", 90.0, 93.0, 1, 200)]
    issues_ok = found(tmp_path, ok)[1]
    assert not [i for i in issues_ok if i.severity is not Severity.INFO]
    assert "PLACE_ORDER_INCONSISTENT" in codes(found(tmp_path, bad)[1])


def test_same_lifter_twice_in_one_block(tmp_path):
    blocks = clean_blocks()
    blocks.insert(4, [*blocks[3]])
    assert "DUPLICATE_LIFTER_IN_MEET" in codes(found(tmp_path, blocks)[1])


def test_team_points_follow_the_place_scale(tmp_path):
    blocks = clean_blocks()
    blocks[3][20] = 12  # second place with the first-place score
    assert "TEAM_POINTS_NOT_BY_SCALE" in codes(found(tmp_path, blocks)[1])


# -- derived tables --------------------------------------------------------------------------


def _team_tail(*rows):
    return [section("Team ranking"), *rows]


def test_team_table_that_matches_the_rows(tmp_path):
    tail = _team_tail([1, "Club Alpha = 12+12+12+9 = 45", *([None] * 20)],
                      [2, "Club Beta = 9+12 = 21", *([None] * 20)])
    meet, issues = found(tmp_path, clean_blocks(), tail=tail)
    assert [t.club for t in meet.team_rows] == ["Club Alpha", "Club Beta"]
    assert "TEAM_SUM_MISMATCH" not in codes(issues) and "TEAM_POINTS_MISMATCH" not in codes(issues)


def test_team_table_errors_are_reported(tmp_path):
    tail = _team_tail([1, "Club Alpha = 12+12 = 25", *([None] * 20)],
                      [2, "Club Gamma = 9", *([None] * 20)])
    issues = codes(found(tmp_path, clean_blocks(), tail=tail)[1])
    assert {"TEAM_SUM_MISMATCH", "TEAM_POINTS_MISMATCH", "TEAM_CLUB_UNKNOWN"} <= issues


def test_best_lifters_table(tmp_path):
    good = [section("Champion of champions "), section("Women"),
            [None, "Anna First", 60.0, "Club Alpha", *([None] * 18)]]
    meet, issues = found(tmp_path, clean_blocks(), tail=good)
    assert meet.best_lifters[0].name == "Anna First"
    assert "BEST_LIFTERS_MISMATCH" not in codes(issues)
    wrong = [section("Champion of champions "), section("Women"),
             [None, "Bella Second", 60.0, "Club Beta", *([None] * 18)]]
    assert "BEST_LIFTERS_MISMATCH" in codes(found(tmp_path, clean_blocks(), tail=wrong)[1])


def test_women_equipped_points_are_checked(tmp_path):
    def blocks(points):
        return [section("Women "),
                section("Champion of champions equipped powerlifting "),
                lifter("Equip Woman", 62.0, [150, 160, 170], [90, 95, 100], [170, 180, 190],
                       category=63.0, sex="F", equipment="equipped", points=points)]

    ok = found(tmp_path, blocks("auto"))[1]
    assert not {"POINTS_MISMATCH", "POINTS_NOT_CHECKED", "SEX_MISMATCH"} & codes(ok)
    assert "POINTS_MISMATCH" in codes(found(tmp_path, blocks(50.0))[1])
