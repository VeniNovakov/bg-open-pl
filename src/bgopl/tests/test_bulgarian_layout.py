"""The real federation protocols are in Bulgarian. The other tests use English headings, which the
parser accepts as aliases; this file keeps the original Bulgarian layout covered."""

from __future__ import annotations

import openpyxl
from bgopl.tests.helpers_standard import clean_blocks, write_standard
from bgopl.parse_standard import parse_standard

BG_HEADER = ["Място", None, "Отбор", "Дивизия", "Лично тегло", "Категория",
             "Клек-1", "Клек-2", "Клек-3", "Най-добър клек",
             "Лег-1", "Лег-2", "Лег-3", "Най-добър лег",
             "М.тяга-1", "М.тяга-2", "М.тяга-3", "Най-добра тяга",
             "Тотал КГ", "IPF GL точки", "Точки за отбор", None]
BG_WORDS = {"Women ": "Жени ", "Men": "Мъже", "Veterans - M1": "Ветерани - М1"}


def _bulgarian(tmp_path):
    english = write_standard(tmp_path / "en.xlsx", clean_blocks())
    wb = openpyxl.load_workbook(english)
    ws = wb.active
    for row in ws.iter_rows():
        values = [c.value for c in row]
        if values[0] == "Place":
            for cell, text in zip(row, BG_HEADER, strict=False):
                cell.value = text
        elif isinstance(values[1], str) and values[1] in BG_WORDS and values[0] is None:
            row[1].value = BG_WORDS[values[1]]
    ws["A1"] = "Тестово първенство по силов трибой град София 01-02 януари 2026г."
    path = tmp_path / "bg.xlsx"
    wb.save(path)
    return english, path


def test_bulgarian_headings_parse_exactly_like_the_english_ones(tmp_path):
    english, bulgarian = _bulgarian(tmp_path)
    en, bg = parse_standard(english), parse_standard(bulgarian)
    assert bg.city == "София" and en.city == "Sofia"
    key = lambda m: [(x.name, x.sex, x.division, x.class_label, x.total_kg, x.points,
                      x.status, x.place) for x in m.lifters]
    assert key(bg) == key(en) and len(bg.lifters) == 7
