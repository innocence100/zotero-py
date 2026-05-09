import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import Library, SyncDeleteLog, User
from ..db import get_db
from ..library import get_library

router = APIRouter()


@router.get("/{library_type}s/{library_id}/deleted")
async def get_deleted(
    library_type: str,
    library_id: int,
    since: int = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    q = select(SyncDeleteLog).where(
        and_(
            SyncDeleteLog.library_id == library.id,
            SyncDeleteLog.version > since,
        )
    )
    result = await db.execute(q)
    logs = result.scalars().all()

    type_map = {
        "item": "items",
        "collection": "collections",
        "search": "searches",
        "tag": "tags",
        "setting": "settings",
    }
    deleted = {
        "collections": [],
        "items": [],
        "searches": [],
        "tags": [],
        "settings": [],
    }
    for log in logs:
        plural = type_map.get(log.object_type)
        if plural and plural in deleted:
            deleted[plural].append(log.key)

    return Response(
        content=json.dumps(deleted),
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )
