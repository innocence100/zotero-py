import json
import logging
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
    validate_item_data,
    validate_object_key,
)

router = APIRouter()
_logger = logging.getLogger("zotero")


async def _delete_item_with_children(db: AsyncSession, library: Library, item: Item):
    child_result = await db.execute(
        select(Item).where(
            and_(Item.library_id == library.id, Item.parent_key == item.key)
        )
    )
    children = child_result.scalars().all()
    for child in children:
        await _delete_item_with_children(db, library, child)
        log = SyncDeleteLog(
            library_id=library.id,
            object_type="item",
            key=child.key,
            version=library.version,
        )
        db.add(log)
        await db.delete(child)
    log = SyncDeleteLog(
        library_id=library.id,
        object_type="item",
        key=item.key,
        version=library.version,
    )
    db.add(log)
    await db.delete(item)


async def _list_items_impl(
    library_type: str,
    library_id: int,
    request: Request,
    format: Optional[str],
    since: Optional[int],
    itemKey: Optional[str],
    itemType: Optional[str],
    is_top: bool,
    is_trash: bool,
    include_trashed: bool,
    limit: Optional[int],
    start: Optional[int],
    db: AsyncSession,
    user: User,
    collection_key: Optional[str] = None,
):
    library = await get_library(db, library_type, library_id, user)

    if collection_key is not None:
        validate_object_key(collection_key)
        collection_result = await db.execute(
            select(Collection).where(
                and_(Collection.library_id == library.id, Collection.key == collection_key)
            )
        )
        collection = collection_result.scalar_one_or_none()
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

    if not check_if_modified(request, library):
        return Response(status_code=304, headers={"Last-Modified-Version": str(library.version)})

    q = select(Item).where(Item.library_id == library.id)

    if collection_key is not None:
        q = q.where(func.json_extract(Item.data_json, "$.collections").like(f'%"{collection_key}"%'))

    if since is not None:
        q = q.where(Item.version > since)

    if itemKey:
        keys = [k.strip() for k in itemKey.split(",") if k.strip()]
        q = q.where(Item.key.in_(keys))

    if itemType:
        if itemType.startswith("-"):
            excluded = [t.strip() for t in itemType[1:].split("||") if t.strip()]
            q = q.where(Item.item_type.notin_(excluded))
        else:
            types = [t.strip() for t in itemType.split("||") if t.strip()]
            q = q.where(Item.item_type.in_(types))

    if include_trashed:
        pass
    elif is_trash:
        q = q.where(Item.deleted == 1)
    else:
        q = q.where(Item.deleted == 0)

    if is_top:
        q = q.where(Item.parent_key.is_(None))

    if format == "versions":
        q2 = select(Item.key, Item.version).where(Item.library_id == library.id)
        if collection_key is not None:
            q2 = q2.where(func.json_extract(Item.data_json, "$.collections").like(f'%"{collection_key}"%'))
        if since is not None:
            q2 = q2.where(Item.version > since)
        if include_trashed:
            pass
        elif is_trash:
            q2 = q2.where(Item.deleted == 1)
        else:
            q2 = q2.where(Item.deleted == 0)
        if is_top:
            q2 = q2.where(Item.parent_key.is_(None))
        if itemKey:
            keys = [k.strip() for k in itemKey.split(",") if k.strip()]
            q2 = q2.where(Item.key.in_(keys))
        if itemType:
            if itemType.startswith("-"):
                excluded = [t.strip() for t in itemType[1:].split("||") if t.strip()]
                q2 = q2.where(Item.item_type.notin_(excluded))
            else:
                types = [t.strip() for t in itemType.split("||") if t.strip()]
                q2 = q2.where(Item.item_type.in_(types))

        result = await db.execute(q2)
        versions = {row[0]: row[1] for row in result}
        return Response(
            content=json.dumps(versions),
            media_type="application/json",
            headers={"Last-Modified-Version": str(library.version)},
        )

    if format == "keys":
        q_keys = select(Item.key).where(Item.library_id == library.id)
        if collection_key is not None:
            q_keys = q_keys.where(func.json_extract(Item.data_json, "$.collections").like(f'%"{collection_key}"%'))
        if since is not None:
            q_keys = q_keys.where(Item.version > since)
        if not include_trashed:
            q_keys = q_keys.where(Item.deleted == (1 if is_trash else 0))
        if is_top:
            q_keys = q_keys.where(Item.parent_key.is_(None))
        if itemKey:
            keys = [k.strip() for k in itemKey.split(",") if k.strip()]
            q_keys = q_keys.where(Item.key.in_(keys))
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

    q = q.order_by(Item.date_added.desc())
    result = await db.execute(q)
    items = result.scalars().all()

    response_data = []
    for item in items:
        d = item.data
        d["key"] = item.key
        d["version"] = item.version
        response_data.append({
            "key": item.key,
            "version": item.version,
            "data": d,
            "meta": {},
            "links": {
                "self": {
                    "href": f"https://api.zotero.org/{library_type}s/{library_id}/items/{item.key}",
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


@router.get("/{library_type}s/{library_id}/items")
async def list_items(
    library_type: str,
    library_id: int,
    request: Request,
    format: Optional[str] = Query(None),
    since: Optional[int] = Query(None),
    itemKey: Optional[str] = Query(None),
    itemType: Optional[str] = Query(None),
    top: Optional[str] = Query(None),
    trash: Optional[str] = Query(None),
    includeTrashed: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    start: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _list_items_impl(
        library_type, library_id, request, format, since, itemKey, itemType,
        top is not None, trash is not None, bool(includeTrashed), limit, start, db, user,
    )


@router.get("/{library_type}s/{library_id}/items/top")
async def list_top_items(
    library_type: str,
    library_id: int,
    request: Request,
    format: Optional[str] = Query(None),
    since: Optional[int] = Query(None),
    itemKey: Optional[str] = Query(None),
    itemType: Optional[str] = Query(None),
    includeTrashed: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    start: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _list_items_impl(
        library_type, library_id, request, format, since, itemKey, itemType,
        True, False, bool(includeTrashed), limit, start, db, user,
    )


@router.get("/{library_type}s/{library_id}/items/trash")
async def list_trash_items(
    library_type: str,
    library_id: int,
    request: Request,
    format: Optional[str] = Query(None),
    since: Optional[int] = Query(None),
    itemKey: Optional[str] = Query(None),
    itemType: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    start: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _list_items_impl(
        library_type, library_id, request, format, since, itemKey, itemType,
        False, True, False, limit, start, db, user,
    )


@router.post("/{library_type}s/{library_id}/items")
async def create_items(
    library_type: str,
    library_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)
    check_if_unmodified(request, library)

    body = await request.body()
    _logger.debug("ITEMS BATCH body size=%d", len(body))
    try:
        data_list = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if isinstance(data_list, dict):
        data_list = [data_list]

    _logger.info("ITEMS BATCH count=%d", len(data_list))

    for idx in range(len(data_list)):
        d = data_list[idx]
        if "data" in d and isinstance(d["data"], dict):
            inner = d["data"]
            inner.setdefault("key", d.get("key"))
            inner.setdefault("version", d.get("version"))
            data_list[idx] = inner
            _logger.debug("ITEMS BATCH[%d] unwrap data wrapper key=%s", idx, inner.get("key"))
        else:
            _logger.debug("ITEMS BATCH[%d] no data wrapper keys=%s", idx, list(d.keys())[:10])

    successful = {}
    unchanged = {}
    failed = {}

    for i, item_data in enumerate(data_list):
        try:
            key = item_data.get("key") or generate_key()
            item_type = item_data.get("itemType", "")

            existing_result = await db.execute(
                select(Item).where(
                    and_(Item.library_id == library.id, Item.key == key)
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                check_batch_object_write_version(existing, item_data)
                existing_data = existing.data.copy()
                existing_data["key"] = existing.key
                existing_data["version"] = existing.version
                # Merge incoming fields; preserve existing fields not included in update
                existing_data.update(item_data)
                if existing_data.get("itemType"):
                    item_type = existing_data["itemType"]
                else:
                    # Should never happen for synced items, but guard just in case
                    _logger.error(
                        "ITEMS BATCH[%d] no itemType after merge key=%s",
                        i, key
                    )
                    raise HTTPException(status_code=400, detail="itemType is required")
                # Compare after stripping injected keys
                existing_data.pop("key", None)
                existing_data.pop("version", None)
                # Re-fetch for comparison
                cmp_existing = existing.data.copy()
                cmp_existing.pop("key", None)
                cmp_existing.pop("version", None)
                if cmp_existing == existing_data:
                    unchanged[str(i)] = key
                    _logger.debug("ITEMS BATCH[%d] unchanged key=%s", i, key)
                    continue
                # Restore for persistence
                existing_data["key"] = existing.key
                item_data_merged = existing_data
                is_deleted = 1 if item_data_merged.get("deleted") else 0
                existing.data_json = json.dumps(item_data_merged, ensure_ascii=False)
                existing.item_type = item_type
                existing.parent_key = item_data_merged.get("parentItem")
                existing.deleted = is_deleted
                await bump_version(db, library)
                existing.version = library.version
                existing.date_modified = datetime.now(timezone.utc)
                item_data_merged["version"] = existing.version
                successful[str(i)] = {
                    "key": existing.key,
                    "version": existing.version,
                    "data": item_data_merged,
                }
                _logger.debug("ITEMS BATCH[%d] updated key=%s version=%s", i, key, existing.version)
            else:
                if not item_type:
                    _logger.error(
                        "ITEMS BATCH[%d] missing itemType key=%s available_keys=%s data=%s",
                        i, key, list(item_data.keys())[:20], json.dumps(item_data, ensure_ascii=False)[:500]
                    )
                    raise ValueError("itemType is required")
                validate_item_data(item_data)
                check_batch_object_write_version(None, item_data)
                item_data["key"] = key
                is_deleted = 1 if item_data.get("deleted") else 0
                new_item = Item(
                    library_id=library.id,
                    key=key,
                    item_type=item_type,
                    data_json=json.dumps(item_data, ensure_ascii=False),
                    parent_key=item_data.get("parentItem"),
                    deleted=is_deleted,
                )
                await bump_version(db, library)
                new_item.version = library.version
                db.add(new_item)
                item_data["version"] = new_item.version
                successful[str(i)] = {
                    "key": new_item.key,
                    "version": new_item.version,
                    "data": item_data,
                }
                _logger.debug("ITEMS BATCH[%d] created key=%s version=%s", i, key, new_item.version)
        except HTTPException as e:
            _logger.error("ITEMS BATCH[%d] HTTPException key=%s code=%s detail=%s", i, item_data.get("key", key), e.status_code, e.detail)
            failed[str(i)] = {"key": item_data.get("key", key), "code": e.status_code, "message": e.detail}
        except Exception as e:
            _logger.error("ITEMS BATCH[%d] Exception key=%s error=%s", i, item_data.get("key", key), str(e))
            failed[str(i)] = {"key": item_data.get("key", key), "code": 400, "message": str(e)}

    if failed:
        _logger.error("ITEMS BATCH failed count=%d successful=%d unchanged=%d", len(failed), len(successful), len(unchanged))

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


@router.get("/{library_type}s/{library_id}/items/{item_key}")
async def get_item(
    library_type: str,
    library_id: int,
    item_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(item_key)
    library = await get_library(db, library_type, library_id, user)

    if not check_if_modified(request, library):
        return Response(status_code=304, headers={"Last-Modified-Version": str(library.version)})

    result = await db.execute(
        select(Item).where(and_(Item.library_id == library.id, Item.key == item_key))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    d = item.data
    d["key"] = item.key
    d["version"] = item.version

    response_data = {
        "key": item.key,
        "version": item.version,
        "data": d,
        "meta": {},
        "links": {
            "self": {
                "href": f"https://api.zotero.org/{library_type}s/{library_id}/items/{item.key}",
                "type": "application/json",
            }
        },
    }
    return Response(
        content=json.dumps(response_data, ensure_ascii=False),
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.put("/{library_type}s/{library_id}/items/{item_key}")
async def update_item(
    library_type: str,
    library_id: int,
    item_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(item_key)
    library = await get_library(db, library_type, library_id, user)

    result = await db.execute(
        select(Item).where(and_(Item.library_id == library.id, Item.key == item_key))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    body = await request.body()
    item_data = json.loads(body)

    if "data" in item_data and isinstance(item_data["data"], dict):
        inner = item_data["data"]
        inner.setdefault("key", item_data.get("key"))
        inner.setdefault("version", item_data.get("version"))
        item_data = inner

    _logger.debug("PUT item %s/%s itemType=%s keys=%s", library_type, item_key, item_data.get("itemType"), list(item_data.keys())[:15])
    check_object_write_version(request, item, item_data)

    existing_data = item.data.copy()
    existing_data.update(item_data)
    item.data_json = json.dumps(existing_data, ensure_ascii=False)
    item.item_type = existing_data.get("itemType", item.item_type)
    item.parent_key = existing_data.get("parentItem")
    if "deleted" in item_data:
        item.deleted = 1 if item_data.get("deleted") else 0
    item.date_modified = datetime.now(timezone.utc)
    await bump_version(db, library)
    item.version = library.version

    await db.flush()

    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.patch("/{library_type}s/{library_id}/items/{item_key}")
async def patch_item(
    library_type: str,
    library_id: int,
    item_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(item_key)
    library = await get_library(db, library_type, library_id, user)

    result = await db.execute(
        select(Item).where(and_(Item.library_id == library.id, Item.key == item_key))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    body = await request.body()
    patch_data = json.loads(body)
    if "data" in patch_data and isinstance(patch_data["data"], dict):
        inner = patch_data["data"]
        inner.setdefault("key", patch_data.get("key"))
        inner.setdefault("version", patch_data.get("version"))
        patch_data = inner

    check_object_write_version(request, item, patch_data)

    item_data = item.data
    item_data.update(patch_data)
    item.data_json = json.dumps(item_data, ensure_ascii=False)
    item.item_type = item_data.get("itemType", item.item_type)
    item.parent_key = item_data.get("parentItem")
    item.deleted = 1 if item_data.get("deleted") else 0
    item.date_modified = datetime.now(timezone.utc)
    await bump_version(db, library)
    item.version = library.version
    await db.flush()

    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.delete("/{library_type}s/{library_id}/items/{item_key}")
async def delete_item(
    library_type: str,
    library_id: int,
    item_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    validate_object_key(item_key)
    library = await get_library(db, library_type, library_id, user)

    result = await db.execute(
        select(Item).where(and_(Item.library_id == library.id, Item.key == item_key))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    check_object_write_version(request, item)

    await bump_version(db, library)

    await _delete_item_with_children(db, library, item)
    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.delete("/{library_type}s/{library_id}/items")
async def delete_items(
    library_type: str,
    library_id: int,
    request: Request,
    itemKey: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not itemKey:
        raise HTTPException(status_code=400, detail="itemKey required")

    library = await get_library(db, library_type, library_id, user)
    check_if_unmodified(request, library)

    keys = [k.strip() for k in itemKey.split(",") if k.strip()]

    for key in keys:
        result = await db.execute(
            select(Item).where(and_(Item.library_id == library.id, Item.key == key))
        )
        item = result.scalar_one_or_none()
        if item:
            await bump_version(db, library)
            await _delete_item_with_children(db, library, item)

    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.get("/{library_type}s/{library_id}/collections/{collection_key}/items")
async def list_collection_items(
    library_type: str,
    library_id: int,
    collection_key: str,
    request: Request,
    format: Optional[str] = Query(None),
    since: Optional[int] = Query(None),
    itemKey: Optional[str] = Query(None),
    itemType: Optional[str] = Query(None),
    includeTrashed: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    start: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _list_items_impl(
        library_type, library_id, request, format, since, itemKey, itemType,
        False, False, bool(includeTrashed), limit, start, db, user,
        collection_key=collection_key,
    )


@router.get("/{library_type}s/{library_id}/collections/{collection_key}/items/top")
async def list_collection_top_items(
    library_type: str,
    library_id: int,
    collection_key: str,
    request: Request,
    format: Optional[str] = Query(None),
    since: Optional[int] = Query(None),
    itemKey: Optional[str] = Query(None),
    itemType: Optional[str] = Query(None),
    includeTrashed: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    start: Optional[int] = Query(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _list_items_impl(
        library_type, library_id, request, format, since, itemKey, itemType,
        True, False, bool(includeTrashed), limit, start, db, user,
        collection_key=collection_key,
    )
