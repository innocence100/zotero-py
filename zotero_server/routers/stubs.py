import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import User
from ..db import get_db
from ..library import get_library

router = APIRouter()


@router.get("/{library_type}s/{library_id}/fulltext")
async def list_fulltext(
    library_type: str,
    library_id: int,
    since: int = Query(0),
    format: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)
    return Response(
        content="{}",
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.post("/{library_type}s/{library_id}/fulltext")
async def set_fulltext(
    library_type: str,
    library_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)
    body = await request.body()
    data = json.loads(body) if body else []
    if isinstance(data, dict):
        data = [data]
    successful = {}
    unchanged = {}
    failed = {}
    for i, _ in enumerate(data):
        successful[str(i)] = {"key": data[i].get("key", ""), "version": library.version}
    result = {"successful": successful, "unchanged": unchanged, "failed": failed}
    return Response(
        content=json.dumps(result),
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.get("/{library_type}s/{library_id}/items/{item_key}/fulltext")
async def get_item_fulltext(
    library_type: str,
    library_id: int,
    item_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return Response(status_code=404)


@router.post("/{library_type}s/{library_id}/items/{item_key}/fulltext")
async def set_item_fulltext(
    library_type: str,
    library_id: int,
    item_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)
    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.get("/{library_type}s/{library_id}/laststoragesync")
async def last_storage_sync(
    library_type: str,
    library_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)
    return Response(
        content="{}",
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.post("/{library_type}s/{library_id}/laststoragesync")
async def set_last_storage_sync(
    library_type: str,
    library_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)
    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.get("/{library_type}s/{library_id}/items/{item_key}/file")
async def get_item_file(
    library_type: str,
    library_id: int,
    item_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return Response(status_code=404)


@router.post("/{library_type}s/{library_id}/items/{item_key}/file")
async def upload_item_file(
    library_type: str,
    library_id: int,
    item_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)
    return Response(status_code=404, headers={"Last-Modified-Version": str(library.version)})


@router.get("/retractions/list")
async def retractions_list():
    return Response(
        content=json.dumps([]),
        media_type="application/json",
    )
