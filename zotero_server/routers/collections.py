import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import Collection, Item, Library, SyncDeleteLog, User, generate_key
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


async def _validate_collection_parent(db: AsyncSession, library_id: int, coll_key: str, parent_key: str | None):
    if not parent_key or parent_key in ("false", "False", "0"):
        return
    validate_object_key(parent_key)
    if parent_key == coll_key:
        raise HTTPException(status_code=400, detail="Collection cannot be its own parent")
    visited = {coll_key}
    current = parent_key
    depth = 0
    while current and depth < 100:
        if current in visited:
            raise HTTPException(status_code=400, detail="Circular collection hierarchy")
        visited.add(current)
        result = await db.execute(
            select(Collection).where(
                and_(Collection.library_id == library_id, Collection.key == current)
            )
        )
        parent_coll = result.scalar_one_or_none()
        if not parent_coll:
            break
        current = parent_coll.parent_key
        depth += 1

router = APIRouter()


def _validate_collection_data(coll_data: dict):
    key = coll_data.get("key")
    if key:
        validate_object_key(key)
    name = coll_data.get("name")
    if not isinstance(name, str) or not name:
        raise HTTPException(status_code=400, detail="Collection name is required")


@router.get("/{library_type}s/{library_id}/collections")
async def list_collections(
    library_type: str,
    library_id: int,
    request: Request,
    format: Optional[str] = Query(None),
    since: Optional[int] = Query(None),
    collectionKey: Optional[str] = Query(None),
    top: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    start: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    if not check_if_modified(request, library):
        return Response(status_code=304, headers={"Last-Modified-Version": str(library.version)})

    q = select(Collection).where(
        and_(Collection.library_id == library.id, Collection.deleted == 0)
    )

    if since is not None:
        q = q.where(Collection.version > since)
    if collectionKey:
        keys = [k.strip() for k in collectionKey.split(",") if k.strip()]
        q = q.where(Collection.key.in_(keys))
    if top is not None:
        q = q.where(Collection.parent_key.is_(None))

    if format == "versions":
        q2 = select(Collection.key, Collection.version).where(
            and_(Collection.library_id == library.id, Collection.deleted == 0)
        )
        if since is not None:
            q2 = q2.where(Collection.version > since)
        if collectionKey:
            keys = [k.strip() for k in collectionKey.split(",") if k.strip()]
            q2 = q2.where(Collection.key.in_(keys))
        if top is not None:
            q2 = q2.where(Collection.parent_key.is_(None))
        result = await db.execute(q2)
        versions = {row[0]: row[1] for row in result}
        return Response(
            content=json.dumps(versions),
            media_type="application/json",
            headers={"Last-Modified-Version": str(library.version)},
        )

    if format == "keys":
        q_keys = select(Collection.key).where(
            and_(Collection.library_id == library.id, Collection.deleted == 0)
        )
        if since is not None:
            q_keys = q_keys.where(Collection.version > since)
        if collectionKey:
            keys = [k.strip() for k in collectionKey.split(",") if k.strip()]
            q_keys = q_keys.where(Collection.key.in_(keys))
        if top is not None:
            q_keys = q_keys.where(Collection.parent_key.is_(None))
        result = await db.execute(q_keys)
        keys = [row[0] for row in result]
        return Response(
            content="\n".join(keys) + ("\n" if keys else ""),
            media_type="text/plain",
            headers={"Last-Modified-Version": str(library.version)},
        )

    total_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(total_q)
    total = total_result.scalar()

    if limit is not None:
        q = q.offset(start).limit(limit)

    result = await db.execute(q.order_by(Collection.name))
    collections = result.scalars().all()

    response_data = []
    for coll in collections:
        d = coll.data
        d["key"] = coll.key
        d["version"] = coll.version
        response_data.append({
            "key": coll.key,
            "version": coll.version,
            "data": d,
            "meta": {},
            "links": {
                "self": {
                    "href": f"https://api.zotero.org/{library_type}s/{library_id}/collections/{coll.key}",
                    "type": "application/json",
                }
            },
        })

    return Response(
        content=json.dumps(response_data, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Last-Modified-Version": str(library.version),
            "Total-Results": str(total),
        },
    )


@router.post("/{library_type}s/{library_id}/collections")
async def create_collections(
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

    for i, coll_data in enumerate(data_list):
        try:
            key = coll_data.get("key") or generate_key()
            coll_data["key"] = key
            _validate_collection_data(coll_data)
            name = coll_data.get("name", "")

            existing_result = await db.execute(
                select(Collection).where(
                    and_(Collection.library_id == library.id, Collection.key == key)
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                check_batch_object_write_version(existing, coll_data)
                existing_data = existing.data
                existing_data["key"] = existing.key
                existing_data["version"] = existing.version
                if existing_data == coll_data:
                    unchanged[str(i)] = key
                    continue
                parent_key = coll_data.get("parentCollection")
                await _validate_collection_parent(db, library.id, existing.key, parent_key)
                existing.data_json = json.dumps(coll_data, ensure_ascii=False)
                existing.name = name
                existing.parent_key = coll_data.get("parentCollection")
                await bump_version(db, library)
                existing.version = library.version
                coll_data["key"] = existing.key
                coll_data["version"] = existing.version
                successful[str(i)] = {
                    "key": existing.key,
                    "version": existing.version,
                    "data": coll_data,
                }
            else:
                check_batch_object_write_version(None, coll_data)
                new_coll = Collection(
                    library_id=library.id,
                    key=key,
                    name=name,
                    parent_key=coll_data.get("parentCollection"),
                    data_json=json.dumps(coll_data, ensure_ascii=False),
                )
                await _validate_collection_parent(db, library.id, key, new_coll.parent_key)
                await bump_version(db, library)
                new_coll.version = library.version
                db.add(new_coll)
                coll_data["key"] = new_coll.key
                coll_data["version"] = new_coll.version
                successful[str(i)] = {
                    "key": new_coll.key,
                    "version": new_coll.version,
                    "data": coll_data,
                }
        except HTTPException as e:
            failed[str(i)] = {"key": coll_data.get("key", key), "code": e.status_code, "message": e.detail}
        except Exception as e:
            failed[str(i)] = {"key": coll_data.get("key", key), "code": 400, "message": str(e)}

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


@router.get("/{library_type}s/{library_id}/collections/{coll_key}")
async def get_collection(
    library_type: str,
    library_id: int,
    coll_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(coll_key)
    library = await get_library(db, library_type, library_id, user)

    if not check_if_modified(request, library):
        return Response(status_code=304, headers={"Last-Modified-Version": str(library.version)})

    result = await db.execute(
        select(Collection).where(
            and_(Collection.library_id == library.id, Collection.key == coll_key)
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    d = coll.data
    d["key"] = coll.key
    d["version"] = coll.version

    return Response(
        content=json.dumps({
            "key": coll.key,
            "version": coll.version,
            "data": d,
            "meta": {},
        }, ensure_ascii=False),
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.put("/{library_type}s/{library_id}/collections/{coll_key}")
async def update_collection(
    library_type: str,
    library_id: int,
    coll_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(coll_key)
    library = await get_library(db, library_type, library_id, user)

    result = await db.execute(
        select(Collection).where(
            and_(Collection.library_id == library.id, Collection.key == coll_key)
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    body = await request.body()
    coll_data = json.loads(body)

    if "data" in coll_data and isinstance(coll_data["data"], dict):
        inner = coll_data["data"]
        inner.setdefault("key", coll_data.get("key"))
        inner.setdefault("version", coll_data.get("version"))
        coll_data = inner

    check_object_write_version(request, coll, coll_data)
    _validate_collection_data(coll_data)

    parent_key = coll_data.get("parentCollection")
    await _validate_collection_parent(db, library.id, coll.key, parent_key)

    coll.data_json = json.dumps(coll_data, ensure_ascii=False)
    coll.name = coll_data.get("name", coll.name)
    coll.parent_key = parent_key
    await bump_version(db, library)
    coll.version = library.version

    await db.flush()

    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.patch("/{library_type}s/{library_id}/collections/{coll_key}")
async def patch_collection(
    library_type: str,
    library_id: int,
    coll_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(coll_key)
    library = await get_library(db, library_type, library_id, user)

    result = await db.execute(
        select(Collection).where(
            and_(Collection.library_id == library.id, Collection.key == coll_key)
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    body = await request.body()
    patch_data = json.loads(body)
    if "data" in patch_data and isinstance(patch_data["data"], dict):
        inner = patch_data["data"]
        inner.setdefault("key", patch_data.get("key"))
        inner.setdefault("version", patch_data.get("version"))
        patch_data = inner

    check_object_write_version(request, coll, patch_data)

    coll_data = coll.data
    coll_data.update(patch_data)
    _validate_collection_data(coll_data)
    parent_key = coll_data.get("parentCollection")
    await _validate_collection_parent(db, library.id, coll.key, parent_key)

    coll.data_json = json.dumps(coll_data, ensure_ascii=False)
    coll.name = coll_data.get("name", coll.name)
    coll.parent_key = parent_key
    await bump_version(db, library)
    coll.version = library.version
    await db.flush()

    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.delete("/{library_type}s/{library_id}/collections/{coll_key}")
async def delete_collection(
    library_type: str,
    library_id: int,
    coll_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(coll_key)
    library = await get_library(db, library_type, library_id, user)

    result = await db.execute(
        select(Collection).where(
            and_(Collection.library_id == library.id, Collection.key == coll_key)
        )
    )
    coll = result.scalar_one_or_none()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    check_object_write_version(request, coll)

    await bump_version(db, library)

    # P0-2: Clear parent_collection reference from child collections
    child_result = await db.execute(
        select(Collection).where(
            and_(Collection.library_id == library.id, Collection.parent_key == coll_key)
        )
    )
    for child in child_result.scalars().all():
        child.parent_key = None
        child_data = child.data
        child_data["parentCollection"] = False
        child.data_json = json.dumps(child_data, ensure_ascii=False)
        child.version = library.version

    # P0-3: Remove collection key from item.collections references
    item_result = await db.execute(
        select(Item).where(
            and_(Item.library_id == library.id, Item.deleted == 0)
        )
    )
    for item in item_result.scalars().all():
        item_data = item.data
        collections_arr = item_data.get("collections", [])
        if coll_key in collections_arr:
            collections_arr.remove(coll_key)
            item_data["collections"] = collections_arr
            item.data_json = json.dumps(item_data, ensure_ascii=False)
            item.version = library.version
            item.date_modified = datetime.now(timezone.utc)

    log = SyncDeleteLog(
        library_id=library.id,
        object_type="collection",
        key=coll_key,
        version=library.version,
    )
    db.add(log)
    await db.delete(coll)
    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.delete("/{library_type}s/{library_id}/collections")
async def delete_collections(
    library_type: str,
    library_id: int,
    request: Request,
    collectionKey: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not collectionKey:
        raise HTTPException(status_code=400, detail="collectionKey required")

    library = await get_library(db, library_type, library_id, user)
    check_if_unmodified(request, library)

    keys = [k.strip() for k in collectionKey.split(",") if k.strip()]
    if not keys:
        raise HTTPException(status_code=400, detail="collectionKey required")
    for key in keys:
        validate_object_key(key)

    for key in keys:
        result = await db.execute(
            select(Collection).where(
                and_(Collection.library_id == library.id, Collection.key == key)
            )
        )
        coll = result.scalar_one_or_none()
        if not coll:
            continue
        check_object_write_version(request, coll)

        await bump_version(db, library)

        # Clear parent_collection reference from child collections
        child_result = await db.execute(
            select(Collection).where(
                and_(Collection.library_id == library.id, Collection.parent_key == key)
            )
        )
        for child in child_result.scalars().all():
            child.parent_key = None
            child_data = child.data
            child_data["parentCollection"] = False
            child.data_json = json.dumps(child_data, ensure_ascii=False)
            child.version = library.version

        # Remove collection key from item.collections references
        item_result = await db.execute(
            select(Item).where(
                and_(Item.library_id == library.id, Item.deleted == 0)
            )
        )
        for item in item_result.scalars().all():
            item_data = item.data
            collections_arr = item_data.get("collections", [])
            if key in collections_arr:
                collections_arr.remove(key)
                item_data["collections"] = collections_arr
                item.data_json = json.dumps(item_data, ensure_ascii=False)
                item.version = library.version
                item.date_modified = datetime.now(timezone.utc)

        log = SyncDeleteLog(
            library_id=library.id,
            object_type="collection",
            key=key,
            version=library.version,
        )
        db.add(log)
        await db.delete(coll)

    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )
