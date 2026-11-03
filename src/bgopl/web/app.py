"""The web PoC: a JSON API (with generated docs at /docs) and server-rendered pages.

    BGOPL_DATA_DIR=data uvicorn bgopl.web.app:create_app --factory
    python -m bgopl.web data            # same, on http://127.0.0.1:8000

Reads every .xlsx in the data folder at start-up. Restart to pick up new files.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..models import Lifter
from ..views import fmt_kg, group_lifters
from .athlete import build_cards, history, personal_bests, sparkline
from .schemas import (
    ClassGroupOut,
    FindingOut,
    LifterOut,
    MeetOut,
    MeetSummaryOut,
    RankingRowOut,
    finding_out,
    lifter_out,
    meet_summary,
)
from .store import MeetRecord, Store

TEMPLATES = Path(__file__).parent / "templates"
SEX_CHOICES = {"F": "Women", "M": "Men"}


def athlete_url(lifter: Lifter) -> str:
    return f"/athletes/{lifter.sex or 'U'}/{quote(lifter.name)}"


def create_app(data_dir: str | Path | None = None,
               suppress_file: str | Path | None = None) -> FastAPI:
    data_dir = data_dir or os.environ.get("BGOPL_DATA_DIR", "data")
    suppress_file = suppress_file or os.environ.get("BGOPL_SUPPRESS_FILE")
    store = Store.load_dir(data_dir, suppress_file)

    app = FastAPI(title="BG Open Powerlifting (proof of concept)",
                  description="Results of Bulgarian powerlifting meets, parsed from the "
                              "federation's spreadsheets.")
    templates = Jinja2Templates(directory=str(TEMPLATES))
    templates.env.globals.update(
        fmt_kg=fmt_kg, athlete_url=athlete_url, sex_choices=SEX_CHOICES,
        contact=os.environ.get("BGOPL_CONTACT", "(contact address not set)"))

    def record(slug: str) -> MeetRecord:
        rec = store.meets.get(slug)
        if rec is None:
            raise HTTPException(404, f"no meet {slug!r}")
        return rec

    def page(request: Request, template: str, **context):
        return templates.TemplateResponse(request, template, {"store": store, **context})

    # -- pages -------------------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home(request: Request):
        meets = sorted(store.meets.values(), key=lambda r: r.slug, reverse=True)
        tops = {label: store.rankings(sex)[:5] for sex, label in SEX_CHOICES.items()}
        return page(request, "home.html", meets=meets, tops=tops)

    @app.get("/meets/{slug}", response_class=HTMLResponse, include_in_schema=False)
    def meet_page(request: Request, slug: str):
        rec = record(slug)
        return page(request, "meet.html", rec=rec, groups=group_lifters(rec.lifters))

    @app.get("/meets/{slug}/notes", response_class=HTMLResponse, include_in_schema=False)
    def notes_page(request: Request, slug: str):
        rec = record(slug)
        order = {"error": 0, "warning": 1, "info": 2}
        findings = sorted((i for i in rec.findings if i.code != "SUMMARY"),
                          key=lambda i: (order[i.severity.value], i.row or 0))
        return page(request, "notes.html", rec=rec, findings=findings)

    @app.get("/athletes/{sex}/{name}", response_class=HTMLResponse, include_in_schema=False)
    def athlete_page(request: Request, sex: str, name: str):
        results = store.athlete_results(sex, name)
        if not results:
            raise HTTPException(404, "lifter not found")
        first = results[0][1]
        trend = history(results)
        coords = sparkline([float(x.points) for _, x in trend]) if len(trend) >= 2 else []
        return page(
            request, "athlete.html", name=first.name, sex=first.sex,
            clubs=list(dict.fromkeys(x.club for _, x in results if x.club)),
            cards=build_cards(results), bests=personal_bests(results), trend=trend,
            coords=coords)

    @app.get("/rankings", response_class=HTMLResponse, include_in_schema=False)
    def rankings_page(request: Request, sex: str = "M", equipment: str = "classic",
                      division: str = ""):
        rows = store.rankings(sex or None, equipment, division or None)
        return page(request, "rankings.html", rows=rows, sex=sex, equipment=equipment,
                    division=division)

    # -- JSON API ----------------------------------------------------------------------------

    @app.get("/api/meets", response_model=list[MeetSummaryOut], tags=["meets"])
    def api_meets():
        return [meet_summary(r) for r in
                sorted(store.meets.values(), key=lambda r: r.slug, reverse=True)]

    @app.get("/api/meets/{slug}", response_model=MeetOut, tags=["meets"])
    def api_meet(slug: str):
        rec = record(slug)
        classes = [ClassGroupOut(header=h, lifters=[lifter_out(x, slug) for x in members])
                   for h, members in group_lifters(rec.lifters)]
        return MeetOut(**meet_summary(rec).model_dump(), classes=classes)

    @app.get("/api/meets/{slug}/findings", response_model=list[FindingOut], tags=["meets"])
    def api_findings(slug: str):
        return [finding_out(i) for i in record(slug).findings if i.code != "SUMMARY"]

    @app.get("/api/rankings", response_model=list[RankingRowOut], tags=["rankings"])
    def api_rankings(sex: str | None = Query(None, pattern="^[FM]$"),
                     equipment: str = Query("classic", pattern="^(classic|equipped)$"),
                     division: str | None = None, limit: int = Query(50, ge=1, le=500)):
        rows = store.rankings(sex, equipment, division)[:limit]
        return [RankingRowOut(rank=i, lifter=lifter_out(x, rec.slug))
                for i, (rec, x) in enumerate(rows, 1)]

    @app.get("/api/athletes/{sex}/{name}", response_model=list[LifterOut], tags=["athletes"])
    def api_athlete(sex: str, name: str):
        results = store.athlete_results(sex, name)
        if not results:
            raise HTTPException(404, "lifter not found")
        return [lifter_out(x, rec.slug) for rec, x in results]

    return app