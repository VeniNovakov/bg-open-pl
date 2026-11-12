"""The points formulas. Pinned values were also computed separately in 40-digit arithmetic, so a
wrong coefficient or a changed rounding shows up here and not in a published ranking."""

from decimal import Decimal

import pytest

from bgopl.points import ipf_gl_points, wilks_factor, wilks_factor_female

D = Decimal


@pytest.mark.parametrize(
    ("sex", "equipment", "bodyweight", "total", "expected"),
    [
        ("M", "classic", "83", "700", "96.8986"),
        ("F", "classic", "63", "400", "87.5133"),
        ("M", "equipped", "93", "900", "97.6028"),
        ("F", "equipped", "57", "450", "86.256"),
    ],
)
def test_ipf_gl_pinned_values(sex, equipment, bodyweight, total, expected):
    assert ipf_gl_points(sex, equipment, D(bodyweight), D(total)) == D(expected)


def test_ipf_gl_is_a_decimal_with_at_most_four_places():
    result = ipf_gl_points("M", "classic", D("83.3"), D("612.5"))
    assert isinstance(result, Decimal)
    assert result == round(result, 4)


def test_ipf_gl_is_proportional_to_the_total():
    one = ipf_gl_points("M", "classic", D("83"), D("300"))
    two = ipf_gl_points("M", "classic", D("83"), D("600"))
    assert abs(two - 2 * one) < D("0.001")  # only rounding differs


def test_ipf_gl_zero_total_scores_zero():
    assert ipf_gl_points("F", "classic", D("63"), D("0")) == D("0")


@pytest.mark.parametrize("sex", ["M", "F"])
def test_ipf_gl_heavier_lifter_gets_fewer_points_for_the_same_total(sex):
    light = ipf_gl_points(sex, "classic", D("60"), D("400"))
    heavy = ipf_gl_points(sex, "classic", D("100"), D("400"))
    assert light > heavy


@pytest.mark.parametrize(
    ("sex", "equipment"),
    [("X", "classic"), (None, "classic"), ("M", "wraps"), ("M", None), ("F", "")],
)
def test_ipf_gl_unknown_combination_is_none(sex, equipment):
    assert ipf_gl_points(sex, equipment, D("70"), D("500")) is None


def test_equipped_scores_differ_from_classic():
    assert (ipf_gl_points("M", "equipped", D("83"), D("700"))
            != ipf_gl_points("M", "classic", D("83"), D("700")))


# -- Wilks (2001), used to cross-check the "WF" column of older protocols ---------------------

def test_wilks_pinned_values():
    assert wilks_factor(D("83"), "M") == D("0.667499")
    assert wilks_factor(D("60"), "F") == D("1.114887")
    assert wilks_factor_female(D("60")) == D("1.114887")


@pytest.mark.parametrize(("sex", "low", "high"), [("F", "26.5", "154.6"), ("M", "39.9", "202")])
def test_wilks_outside_the_valid_bodyweight_range_is_none(sex, low, high):
    assert wilks_factor(D(low), sex) is None
    assert wilks_factor(D(high), sex) is None


@pytest.mark.parametrize("sex", ["F", "M"])
def test_wilks_factor_falls_as_bodyweight_rises(sex):
    assert wilks_factor(D("60"), sex) > wilks_factor(D("90"), sex)


@pytest.mark.parametrize("sex", [None, "X", ""])
def test_wilks_unknown_sex_is_none_not_a_crash(sex):
    assert wilks_factor(D("80"), sex) is None
