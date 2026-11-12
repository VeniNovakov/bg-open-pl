"""Parser details: class and division text, title and date, and the warning for each kind of odd
cell. Built on small synthetic workbooks; each case changes one thing."""

from decimal import Decimal

import pytest
from helpers_standard import clean_blocks, klass, lifter, section, write_standard

from bgopl.models import AttemptStatus, LifterStatus, Severity
from bgopl.parse_standard import norm_division, parse_class, parse_standard

D = Decimal


def parse(tmp_path, blocks, **kwargs):
    return parse_standard(write_standard(tmp_path / "meet.xlsx", blocks, **kwargs))


def codes(meet):
    return [issue.code for issue in meet.issues]


def one_man(**over):
    args = {"place": 1, "sex": "M", "category": 74.0, **over}
    return lifter("Victor", 73.0, [200, 210, 220], [140, 145, -150], [230, 240, 250], **args)


# -- class and division text -------------------------------------------------------------------

@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        (63.0, ("63", D("63.0"), None, None)),
        ("63", ("63", D("63"), None, None)),
        ("63,5", ("63.5", D("63.5"), None, None)),  # decimal comma
        ("84+", ("84+", None, D("84"), None)),  # open-ended class: floor, no limit
        ("84 +", ("84+", None, D("84"), None)),
        ("84+ kg", ("84+", None, D("84"), None)),
        ("84+ \u043a\u0433", ("84+", None, D("84"), None)),  # "кг"
        ("120 kg", ("120", D("120"), None, None)),
        ("M1 - 69", ("69", D("69"), None, "M1")),
        ("\u041c1 - 69", ("69", D("69"), None, "M1")),  # Cyrillic М, as in the real files
        ("m2-83+", ("83+", None, D("83"), "M2")),  # Latin m, no spaces
    ],
)
def test_parse_class(cell, expected):
    assert parse_class(cell) == expected


@pytest.mark.parametrize("cell", ["abc", "", None, True])
def test_parse_class_rejects_text_that_is_not_a_class(cell):
    assert parse_class(cell) is None


@pytest.mark.parametrize(
    ("cell", "expected"),
    [("\u041c1", "M1"), ("M2", "M2"), ("Open", "Open"), ("JR", "JR"), (" Open ", "Open")],
)
def test_norm_division_turns_the_cyrillic_letter_into_latin(cell, expected):
    assert norm_division(cell) == expected


# -- title and date ----------------------------------------------------------------------------

def test_city_date_and_federation_come_from_the_first_rows(tmp_path):
    meet = parse(tmp_path, clean_blocks(), title="Cup city Svishtov 03 April 2026",
                 date="2026-04-03")
    assert (meet.city, str(meet.date), meet.federation) == ("Svishtov", "2026-04-03", "BPF")
    assert meet.sheet == "Protocol"


def test_a_missing_date_is_a_warning_not_a_failure(tmp_path):
    meet = parse(tmp_path, clean_blocks(), date=None)
    assert meet.date is None and "META_DATE_MISSING" in codes(meet)
    assert len(meet.lifters) == 7


def test_a_title_without_a_city_leaves_the_city_empty(tmp_path):
    assert parse(tmp_path, clean_blocks(), title="Cup without a place").city is None


# -- odd cells: each one becomes a finding and the file still parses ---------------------------

def test_attempt_markers_and_zeros_have_no_weight_and_are_reported(tmp_path):
    row = lifter("Anna", 60.0, [100, "x", -110], [60, 0, 65], [120, 125, 130],
                 place=1, category=63.0, bests=(100, 65, 130))
    meet = parse(tmp_path, [section("Women "), klass(63.0), row])
    squat = meet.lifters[0].lifts["S"].attempts
    assert [(a.weight_kg, a.status) for a in squat] == [
        (D("100"), AttemptStatus.GOOD), (None, AttemptStatus.UNKNOWN),
        (D("110"), AttemptStatus.FAIL)]
    assert meet.lifters[0].lifts["B"].attempts[1].weight_kg is None
    assert {"ATTEMPT_MARKER", "ATTEMPT_ZERO"} <= set(codes(meet))
    assert all(i.severity is Severity.WARNING for i in meet.issues
               if i.code in {"ATTEMPT_MARKER", "ATTEMPT_ZERO"})


def test_without_a_sex_heading_the_sex_stays_unknown(tmp_path):
    row = lifter("Anna", 60.0, [100, 105, 110], [60, 62.5, 65], [120, 125, 130],
                 place=1, category=63.0)
    meet = parse(tmp_path, [klass(63.0), row])
    assert meet.lifters[0].sex is None and meet.lifters[0].sex_source == "inherited"
    assert "SEX_INHERITED" in codes(meet)


def test_division_that_contradicts_its_section_heading_is_flagged(tmp_path):
    meet = parse(tmp_path, [section("Veterans - M1"), klass("M1 - 74"),
                            one_man(division="Open")])
    assert "DIVISION_SECTION_MISMATCH" in codes(meet)


def test_a_category_that_is_not_a_class_leaves_the_class_empty(tmp_path):
    meet = parse(tmp_path, [section("Men"), klass(74.0), one_man(category="abc")])
    assert meet.lifters[0].class_label is None
    assert "CATEGORY_UNREADABLE" in codes(meet)


@pytest.mark.parametrize("override", [{"place": "??"}, {"bw": "heavy"}])
def test_a_row_that_cannot_be_read_is_skipped_and_the_next_one_still_parses(tmp_path, override):
    bad = one_man() if "bw" not in override else lifter(
        "Victor", override["bw"], [200, 210, 220], [140, 145, -150], [230, 240, 250],
        place=1, sex="M", category=74.0, bests=(220, 145, 250), total=615, points=None)
    if "place" in override:
        bad = one_man(place=override["place"])
    good = lifter("George", 80.0, [190, 200, -210], [130, 135, 140], [220, 230, 240],
                  place=2, sex="M", category=74.0)
    meet = parse(tmp_path, [section("Men"), klass(74.0), bad, good])
    assert [x.name for x in meet.lifters] == ["George"]
    problem = next(i for i in meet.issues if i.code == "ROW_UNPARSEABLE")
    assert problem.severity is Severity.ERROR and problem.row is not None


def test_invisible_direction_marks_and_odd_spaces_are_removed_from_names(tmp_path):
    ltr_mark, rtl_mark, nbsp = chr(0x200E), chr(0x200F), chr(0xA0)
    messy = f"{ltr_mark}Anna{nbsp} First{rtl_mark}"
    row = lifter(messy, 60.0, [100, 105, 110], [60, 62.5, 65], [120, 125, 130],
                 place=1, category=63.0)
    meet = parse(tmp_path, [section("Women "), klass(63.0), row])
    assert meet.lifters[0].name == "Anna First"


def test_the_points_column_is_read_whatever_its_exact_label(tmp_path):
    meet = parse(tmp_path, clean_blocks())
    assert meet.lifters[0].points_kind.lower().startswith("ipf gl")
    assert meet.lifters[0].status is LifterStatus.RANKED
