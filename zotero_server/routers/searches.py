import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import Library, Search, SyncDeleteLog, User, generate_key
from ..db import get_db
from ..library import (
    bump_version,
    check_batch_object_write_version,
    check_if_modified,
    check_if_unmodified,
    check_object_write_version,
    get_library,
    validate_object_key,
)

router = APIRouter()


@router.get("/{library_type}s/{library_id}/searches")
async def list_searches(
    library_type: str,
    library_id: int,
    request: Request,
    format: Optional[str] = Query(None),
    since: Optional[int] = Query(None),
    searchKey: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    if not check_if_modified(request, library):
        return Response(status_code=304, headers={"Last-Modified-Version": str(library.version)})

    q = select(Search).where(
        and_(Search.library_id == library.id, Search.deleted == 0)
    )
    if since is not None:
        q = q.where(Search.version > since)

    search_keys = None
    if searchKey is not None:
        search_keys = [k.strip() for k in searchKey.split(",") if k.strip()]
        for k in search_keys:
            validate_object_key(k)
        q = q.where(Search.key.in_(search_keys))

    if format == "versions":
        q2 = select(Search.key, Search.version).where(
            and_(Search.library_id == library.id, Search.deleted == 0)
        )
        if since is not None:
            q2 = q2.where(Search.version > since)
        if search_keys is not None:
            q2 = q2.where(Search.key.in_(search_keys))
        result = await db.execute(q2)
        versions = {row[0]: row[1] for row in result}
        return Response(
            content=json.dumps(versions),
            media_type="application/json",
            headers={"Last-Modified-Version": str(library.version)},
        )

    if format == "keys":
        q_keys = select(Search.key).where(
            and_(Search.library_id == library.id, Search.deleted == 0)
        )
        if since is not None:
            q_keys = q_keys.where(Search.version > since)
        if search_keys is not None:
            q_keys = q_keys.where(Search.key.in_(search_keys))
        result = await db.execute(q_keys)
        keys = [row[0] for row in result]
        return Response(
            content="\n".join(keys) + ("\n" if keys else ""),
            media_type="text/plain",
            headers={"Last-Modified-Version": str(library.version)},
        )

    result = await db.execute(q)
    searches = result.scalars().all()

    response_data = []
    for s in searches:
        d = s.data
        d["key"] = s.key
        d["version"] = s.version
        response_data.append({
            "key": s.key,
            "version": s.version,
            "data": d,
            "meta": {},
        })

    return Response(
        content=json.dumps(response_data, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Last-Modified-Version": str(library.version),
            "Total-Results": str(len(searches)),
        },
    )


@router.post("/{library_type}s/{library_id}/searches")
async def create_searches(
    library_type: str,
    library_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    check_if_unmodified(request, library)

    body = await request.body()
    data_list = json.loads(body)
    if isinstance(data_list, dict):
        data_list = [data_list]

    for idx in range(len(data_list)):
        d = data_list[idx]
        if "data" in d and isinstance(d["data"], dict):
            inner = d["data"]
            inner.setdefault("key", d.get("key"))
            inner.setdefault("version", d.get("version"))
            data_list[idx] = inner

    successful = {}
    unchanged = {}
    failed = {}

    for i, search_data in enumerate(data_list):
        try:
            key = search_data.get("key") or generate_key()
            name = search_data.get("name", "")

            existing_result = await db.execute(
                select(Search).where(
                    and_(Search.library_id == library.id, Search.key == key)
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                check_batch_object_write_version(existing, search_data)
                existing_data = existing.data
                existing_data["key"] = existing.key
                existing_data["version"] = existing.version
                if existing_data == search_data:
                    unchanged[str(i)] = key
                    continue
                existing.data_json = json.dumps(search_data, ensure_ascii=False)
                existing.name = name
                await bump_version(db, library)
                existing.version = library.version
                search_data["key"] = existing.key
                search_data["version"] = existing.version
                successful[str(i)] = {
                    "key": existing.key,
                    "version": existing.version,
                    "data": search_data,
                }
            else:
                check_batch_object_write_version(None, search_data)
                new_search = Search(
                    library_id=library.id,
                    key=key,
                    name=name,
                    data_json=json.dumps(search_data, ensure_ascii=False),
                )
                await bump_version(db, library)
                new_search.version = library.version
                db.add(new_search)
                search_data["key"] = new_search.key
                search_data["version"] = new_search.version
                successful[str(i)] = {
                    "key": new_search.key,
                    "version": new_search.version,
                    "data": search_data,
                }
        except HTTPException as e:
            failed[str(i)] = {"key": search_data.get("key", key), "code": e.status_code, "message": e.detail}
        except Exception as e:
            failed[str(i)] = {"key": search_data.get("key", key), "code": 400, "message": str(e)}

    await db.flush()

    result = {
        "successful": successful,
        "unchanged": unchanged,
        "failed": failed,
    }
    return Response(
        content=json.dumps(result, ensure_ascii=False),
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.get("/{library_type}s/{library_id}/searches/{search_key}")
async def get_search(
    library_type: str,
    library_id: int,
    search_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(search_key)
    library = await get_library(db, library_type, library_id, user)

    if not check_if_modified(request, library):
        return Response(status_code=304, headers={"Last-Modified-Version": str(library.version)})
    result = await db.execute(
        select(Search).where(
            and_(Search.library_id == library.id, Search.key == search_key)
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    d = search.data
    d["key"] = search.key
    d["version"] = search.version
    return Response(
        content=json.dumps({"key": search.key, "version": search.version, "data": d, "meta": {}}, ensure_ascii=False),
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.put("/{library_type}s/{library_id}/searches/{search_key}")
async def update_search(
    library_type: str,
    library_id: int,
    search_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(search_key)
    library = await get_library(db, library_type, library_id, user)
    result = await db.execute(
        select(Search).where(
            and_(Search.library_id == library.id, Search.key == search_key)
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    body = await request.body()
    search_data = json.loads(body)
    if "data" in search_data and isinstance(search_data["data"], dict):
        inner = search_data["data"]
        inner.setdefault("key", search_data.get("key"))
        inner.setdefault("version", search_data.get("version"))
        search_data = inner

    check_object_write_version(request, search, search_data)

    search.data_json = json.dumps(search_data, ensure_ascii=False)
    search.name = search_data.get("name", search.name)
    await bump_version(db, library)
    search.version = library.version
    await db.flush()
    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.patch("/{library_type}s/{library_id}/searches/{search_key}")
async def patch_search(
    library_type: str,
    library_id: int,
    search_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(search_key)
    library = await get_library(db, library_type, library_id, user)
    result = await db.execute(
        select(Search).where(
            and_(Search.library_id == library.id, Search.key == search_key)
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    body = await request.body()
    patch_data = json.loads(body)
    if "data" in patch_data and isinstance(patch_data["data"], dict):
        inner = patch_data["data"]
        inner.setdefault("key", patch_data.get("key"))
        inner.setdefault("version", patch_data.get("version"))
        patch_data = inner

    check_object_write_version(request, search, patch_data)

    search_data = search.data
    search_data.update(patch_data)
    search.data_json = json.dumps(search_data, ensure_ascii=False)
    search.name = search_data.get("name", search.name)
    await bump_version(db, library)
    search.version = library.version
    await db.flush()
    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.delete("/{library_type}s/{library_id}/searches/{search_key}")
async def delete_search(
    library_type: str,
    library_id: int,
    search_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(search_key)
    library = await get_library(db, library_type, library_id, user)

    check_if_unmodified(request, library)

    result = await db.execute(
        select(Search).where(
            and_(Search.library_id == library.id, Search.key == search_key)
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    check_object_write_version(request, search)

    await bump_version(db, library)

    log = SyncDeleteLog(
        library_id=library.id,
        object_type="search",
        key=search_key,
        version=library.version,
    )
    db.add(log)
    await db.delete(search)
    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.delete("/{library_type}s/{library_id}/searches")
async def delete_searches(
    library_type: str,
    library_id: int,
    request: Request,
    searchKey: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not searchKey:
        raise HTTPException(status_code=400, detail="searchKey required")

    library = await get_library(db, library_type, library_id, user)
    check_if_unmodified(request, library)

    keys = [k.strip() for k in searchKey.split(",") if k.strip()]
    if not keys:
        raise HTTPException(status_code=400, detail="searchKey required")
    for key in keys:
        validate_object_key(key)

    for key in keys:
        result = await db.execute(
            select(Search).where(
                and_(Search.library_id == library.id, Search.key == key)
            )
        )
        search = result.scalar_one_or_none()
        if search:
            check_object_write_version(request, search)
            await bump_version(db, library)
            log = SyncDeleteLog(
                library_id=library.id,
                object_type="search",
                key=key,
                version=library.version,
            )
            db.add(log)
            await db.delete(search)

    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )
