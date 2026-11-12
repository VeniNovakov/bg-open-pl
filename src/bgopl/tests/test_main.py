from helpers_standard import clean_blocks, section, write_standard

from bgopl.main import main


def test_main_prints_every_lifter(tmp_path, capsys):
    path = write_standard(tmp_path / "s.xlsx", clean_blocks())
    assert main([str(path)]) == 0
    out = capsys.readouterr().out
    for name in ("Anna First", "Bella Second", "Victor First", "George Second", "Daniel Third",
                 "Emil Veteran", "Guest Person"):
        assert name in out
    assert "7 lifters: 6 ranked, 1 guest, 0 disqualified" in out
    assert "-- Women | Open | 63 kg | classic --" in out and "guest" in out


def test_main_filters_by_status(tmp_path, capsys):
    path = write_standard(tmp_path / "s.xlsx", clean_blocks())
    main([str(path), "--status", "guest"])
    out = capsys.readouterr().out
    assert "Guest Person" in out and "Anna First" not in out


def test_main_lists_findings_and_fails_on_errors(tmp_path, capsys):
    blocks = clean_blocks()
    blocks[2][18] = 999  # wrong total
    path = write_standard(tmp_path / "s.xlsx", blocks)
    assert main([str(path), "--issues"]) == 1
    assert "TOTAL_MISMATCH" in capsys.readouterr().out


def test_main_reports_an_unreadable_file(tmp_path, capsys):
    path = write_standard(tmp_path / "s.xlsx", [section("Men")], header=False)
    assert main([str(path)]) == 2
    assert "header" in capsys.readouterr().err


def test_main_handles_a_file_with_no_lifters(tmp_path, capsys):
    path = write_standard(tmp_path / "s.xlsx", [section("Men")])
    assert main([str(path)]) == 0
    assert "0 lifters" in capsys.readouterr().out


def test_groups_by_weight_class_and_sorts_by_total(tmp_path, capsys):
    path = write_standard(tmp_path / "s.xlsx", clean_blocks())
    main([str(path)])
    out = capsys.readouterr().out
    headers = [line for line in out.splitlines() if line.startswith("-- ")]
    assert headers == [
        "-- Women | Open | 63 kg | classic --",
        "-- Men | Open | 74 kg | classic --",
        "-- Men | Open | 83 kg | classic --",
        "-- Men | M1 | 74 kg | classic --",
        "-- Men | guest lifters --",
    ]
    men83 = out.split("-- Men | Open | 83 kg | classic --")[1].split("--")[0]
    assert men83.index("George Second") < men83.index("Daniel Third")  # higher total first


def test_class_group_is_sorted_by_total_not_by_place(tmp_path, capsys):
    blocks = clean_blocks()
    blocks[2][0], blocks[3][0] = 2, 1  # places swapped: Anna 300 kg listed as 2nd
    path = write_standard(tmp_path / "s.xlsx", blocks)
    main([str(path)])
    women = capsys.readouterr().out.split("-- Women | Open | 63 kg | classic --")[1].split("--")[0]
    assert women.index("Anna First") < women.index("Bella Second")


def test_file_order_keeps_the_sheet_order(tmp_path, capsys):
    path = write_standard(tmp_path / "s.xlsx", clean_blocks())
    main([str(path), "--file-order"])
    out = capsys.readouterr().out
    assert "-- Women (classic) --" in out and "-- Veterans - M1 (classic) --" in out
    assert out.index("Anna First") < out.index("Victor First") < out.index("Emil Veteran")
