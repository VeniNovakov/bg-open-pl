from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from .store import MeetRecord, Store


def get_store(request: Request) -> Store:
    return request.app.state.store

def get_record(slug: str, store: Store = Depends(get_store)) -> MeetRecord:
    rec = store.meets.get(slug)
    if rec is None:
        raise HTTPException(404, f"no meet {slug!r}")
    return rec