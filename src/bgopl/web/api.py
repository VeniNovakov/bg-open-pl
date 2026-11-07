from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import FastAPI, HTTPException, Query

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
from ..views import fmt_kg, group_lifters
from .store import MeetRecord, Store

def create_api(app: FastAPI, store: Store):
    def record(slug: str) -> MeetRecord:
        rec = store.meets.get(slug)
        if rec is None:
            raise HTTPException(404, f"no meet {slug!r}")
        return rec
    
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

    @app.get("/api/info", tags=["meta"])
    def api_info():
        return {"contact": "novakovvenelin@gmail.com", "meets": len(store.meets), "unreadable_files": len(store.failed)}
    