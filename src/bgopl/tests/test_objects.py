from helpers_standard import clean_blocks, write_standard

import bgopl
from bgopl.models import Lifter, StandardMeet


def meet(tmp_path):
    return bgopl.read_results(write_standard(tmp_path / "s.xlsx", clean_blocks()))


def test_read_results_returns_objects(tmp_path):
    m = meet(tmp_path)
    assert isinstance(m, StandardMeet) and len(m) == 7
    assert all(isinstance(x, Lifter) for x in m)
    assert [x.name for x in m][:2] == ["Anna First", "Bella Second"]


def test_read_results_can_skip_validation(tmp_path):
    path = write_standard(tmp_path / "s.xlsx", clean_blocks())
    assert not any(i.code == "SUMMARY" for i in bgopl.read_results(path, validate=False).issues)
    assert any(i.code == "SUMMARY" for i in bgopl.read_results(path).issues)


def test_each_lifter_prints_on_its_own(tmp_path):
    ana = meet(tmp_path).find("anna")[0]
    line = str(ana)
    assert "Anna First" in line and "Club Alpha" in line and "total 300.0" in line
    assert "\n" not in line


def test_describe_shows_every_attempt_with_its_outcome(tmp_path):
    card = meet(tmp_path).find("Anna First")[0].describe()
    assert "Squat" in card and "110.0x" in card and "105.0ok" in card
    assert "total 300.0 kg" in card and "(Club Alpha)" in card


def test_by_class_groups_and_sorts(tmp_path):
    groups = dict(meet(tmp_path).by_class())
    men83 = groups["Men | Open | 83 kg | classic"]
    assert [x.name for x in men83] == ["George Second", "Daniel Third"]
    assert [x.name for x in groups["Men | guest lifters"]] == ["Guest Person"]


def test_find_is_case_insensitive_and_partial(tmp_path):
    m = meet(tmp_path)
    assert [x.name for x in m.find("VETERAN")] == ["Emil Veteran"]
    assert m.find("no such name") == []


def test_divisions_of_one_weight_class_stay_separate(tmp_path):
    """SJR and JR lifters of the same class were merged into one group, under the header of
    whichever came first."""
    from helpers_standard import klass, lifter, section, write_standard

    from bgopl import read_results

    blocks = [
        section("Men - SJR"), klass(83.0),
        lifter("Youth First", 80.0, [150, 160, 170], [100, 110, 120], [180, 190, 200],
               place=1, sex="M", division="SJR", category=83.0),
        section("Men - JR"), klass(83.0),
        lifter("Junior First", 81.0, [200, 210, 220], [130, 140, 150], [230, 240, 250],
               place=1, sex="M", division="JR", category=83.0),
        section("Men"), klass(83.0),
        lifter("Open First", 82.0, [210, 220, 230], [140, 150, 160], [240, 250, 260],
               place=1, sex="M", division="Open", category=83.0),
    ]
    path = write_standard(tmp_path / "divisions.xlsx", blocks)
    groups = {header: [x.name for x in members] for header, members in read_results(path).by_class()}
    assert groups == {
        "Men | Open | 83 kg | classic": ["Open First"],
        "Men | SJR | 83 kg | classic": ["Youth First"],
        "Men | JR | 83 kg | classic": ["Junior First"],
    }
    assert list(groups) == ["Men | Open | 83 kg | classic", "Men | SJR | 83 kg | classic",
                            "Men | JR | 83 kg | classic"]
