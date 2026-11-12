import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from urllib.parse import quote

from fastapi.testclient import TestClient
from helpers_standard import clean_blocks, klass, lifter, section, write_standard

from bgopl.web.app import create_app


@pytest.fixture
def data_dir(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    write_standard(folder / "a.xlsx", clean_blocks())
    (folder / "broken.xlsx").write_bytes(b"this is not a spreadsheet")
    return folder


@pytest.fixture
def client(data_dir):
    return TestClient(create_app(data_dir))


SLUG = "2026-01-01"


def test_root_redirects_to_the_docs_when_there_is_no_build(client, tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("BGOPL_FRONTEND_DIR", str(empty))
    r = TestClient(create_app(tmp_path / "data2")).get("/", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/docs"




def test_unknown_meet_and_lifter_are_404(client):
    assert client.get("/api/meets/1999-01-01").status_code == 404
    assert client.get("/api/meets/1999-01-01/findings").status_code == 404
    assert client.get("/api/athletes/M/Nobody").status_code == 404






def test_rankings_are_ordered_by_points_and_filterable(client):
    men = client.get("/api/rankings?sex=M").json()
    points = [row["lifter"]["points"] for row in men]
    assert points == sorted(points, reverse=True) and men[0]["rank"] == 1
    assert {row["lifter"]["sex"] for row in men} == {"M"}
    vets = client.get("/api/rankings?division=M1").json()
    assert [row["lifter"]["name"] for row in vets] == ["Emil Veteran"]
    assert client.get("/api/rankings?sex=F").status_code == 200


def test_rankings_filter_by_weight_class(client):
    everyone = client.get("/api/rankings").json()
    classes = client.get("/api/rankings/classes").json()
    assert classes and classes == sorted(classes, key=lambda c: (float(c.rstrip("+")), c.endswith("+")))
    for label in classes:
        rows = client.get("/api/rankings", params={"weight_class": label}).json()
        assert rows and {r["lifter"]["weight_class"] for r in rows} == {label}
        assert len(rows) <= len(everyone)
    assert client.get("/api/rankings?weight_class=999").json() == []


def test_rankings_leave_out_guests_and_validate_parameters(client):
    names = [row["lifter"]["name"] for row in client.get("/api/rankings").json()]
    assert "Guest Person" not in names
    assert client.get("/api/rankings?sex=X").status_code == 422
    assert client.get("/api/rankings?limit=0").status_code == 422


def test_api_meet_shape(client):
    summary = client.get("/api/meets").json()
    assert summary[0]["slug"] == SLUG and summary[0]["lifters"] == 7
    meet = client.get(f"/api/meets/{SLUG}").json()
    headers = [c["header"] for c in meet["classes"]]
    assert headers[0] == "Women | Open | 63 kg | classic"
    ana = meet["classes"][0]["lifters"][0]
    assert ana["name"] == "Anna First" and ana["total_kg"] == 300.0
    assert ana["squat"]["attempts"][2] == {"weight_kg": 110.0, "result": "fail"}
    assert any(x["status"] == "guest" and x["name"] == "Guest Person"
               for c in meet["classes"] for x in c["lifters"])
    assert client.get(f"/api/meets/{SLUG}/findings").status_code == 200


def test_api_athlete(client):
    rows = client.get(f"/api/athletes/M/{quote('Victor First')}").json()
    assert rows[0]["club"] == "Club Alpha" and rows[0]["meet"] == SLUG


def test_suppressed_lifters_disappear_everywhere(data_dir, tmp_path):
    hide = tmp_path / "hide.txt"
    hide.write_text("# removal requests\nM|Victor First\nBella Second\n", encoding="utf-8")
    c = TestClient(create_app(data_dir, hide))
    assert c.get(f"/api/athletes/M/{quote('Victor First')}").status_code == 404
    assert c.get(f"/api/athletes/F/{quote('Bella Second')}").status_code == 404
    meet = c.get(f"/api/meets/{SLUG}").text
    assert "Victor First" not in meet and "Bella Second" not in meet and "Anna First" in meet
    names = [r["lifter"]["name"] for r in c.get("/api/rankings").json()]
    assert "Victor First" not in names
    assert c.get("/api/meets").json()[0]["lifters"] == 5
    findings = c.get(f"/api/meets/{SLUG}/findings").text
    assert "Victor First" not in findings


def test_same_date_gets_a_second_slug(data_dir):
    write_standard(data_dir / "b.xlsx", clean_blocks())
    c = TestClient(create_app(data_dir))
    assert {m["slug"] for m in c.get("/api/meets").json()} == {SLUG, f"{SLUG}-2"}


def test_best_result_across_meets_counts_once(data_dir):
    blocks = [section("Women "), klass(63.0),
              lifter("Anna First", 60.0, [110, 115, 120], [70, 75, 80], [130, 135, 140],
                     place=1, category=63.0)]
    write_standard(data_dir / "later.xlsx", blocks, date="2026-03-01")
    c = TestClient(create_app(data_dir))
    rows = [r for r in c.get("/api/rankings?sex=F").json() if r["lifter"]["name"] == "Anna First"]
    assert len(rows) == 1 and rows[0]["lifter"]["meet"] == "2026-03-01"
    appearances = c.get(f"/api/athletes/F/{quote('Anna First')}").json()
    assert [a["meet"] for a in appearances] == ["2026-03-01", SLUG]


def test_missing_data_folder_is_reported_not_fatal(tmp_path):
    c = TestClient(create_app(tmp_path / "nope"))
    assert c.get("/api/meets").json() == []
    assert c.get("/api/info").json()["unreadable_files"] == 1






def test_info_endpoint(client):
    r = client.get("/api/info")
    assert r.status_code == 200
    assert r.json() == {"contact": "(contact address not set)", "meets": 1, "unreadable_files": 1}


def test_angular_build_is_served_under_app_with_fallback(data_dir, tmp_path, monkeypatch):
    build = tmp_path / "browser"
    build.mkdir()
    (build / "index.html").write_text("<app-root>spa</app-root>")
    (build / "main.js").write_text("console.log(1)")
    monkeypatch.setenv("BGOPL_FRONTEND_DIR", str(build))
    spa = TestClient(create_app(data_dir))
    assert "spa" in spa.get("/app/").text
    assert "console.log" in spa.get("/app/main.js").text
    assert "spa" in spa.get("/app/athletes/M/Somebody").text  # an Angular route, reloaded
    assert spa.get("/api/meets").json()[0]["slug"] == SLUG  # the API is untouched
    root = spa.get("/", follow_redirects=False)
    assert root.status_code == 307 and root.headers["location"] == "/app/"


def test_no_app_mount_without_a_build(data_dir, tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("BGOPL_FRONTEND_DIR", str(empty))
    assert TestClient(create_app(data_dir)).get("/app/").status_code == 404


def test_spa_missing_asset_is_404_but_routes_fall_back(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<app-root></app-root>")
    (tmp_path / "main-AAA.js").write_text("//ok")
    monkeypatch.setenv("BGOPL_FRONTEND_DIR", str(tmp_path))
    client = TestClient(create_app(tmp_path))
    assert client.get("/app/meets/some-meet").text == "<app-root></app-root>"
    assert client.get("/app/main-AAA.js").status_code == 200
    assert client.get("/app/chunk-STALE.js").status_code == 404
    assert client.get("/app/").headers["cache-control"] == "no-cache"
