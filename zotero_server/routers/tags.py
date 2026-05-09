import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import Item, Library, SyncDeleteLog, User
from ..db import get_db
from ..library import bump_version, check_if_unmodified, get_library

router = APIRouter()


@router.get("/{library_type}s/{library_id}/tags")
async def list_tags(
    library_type: str,
    library_id: int,
    format: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    q = select(Item.data_json).where(
        and_(Item.library_id == library.id, Item.deleted == 0)
    )
    result = await db.execute(q)
    items = result.scalars().all()

    tags_set = set()
    for data_json in items:
        try:
            data = json.loads(data_json)
            for tag in data.get("tags", []):
                tag_name = tag.get("tag", "") if isinstance(tag, dict) else tag
                if tag_name:
                    tags_set.add(tag_name)
        except (json.JSONDecodeError, TypeError):
            pass

    tags = sorted(tags_set)
    if format == "versions":
        return Response(
            content=json.dumps({t: library.version for t in tags}),
            media_type="application/json",
            headers={"Last-Modified-Version": str(library.version)},
        )

    if format == "keys":
        return Response(
            content="\n".join(tags) + ("\n" if tags else ""),
            media_type="text/plain",
            headers={"Last-Modified-Version": str(library.version)},
        )

    tag_list = [{"tag": t} for t in tags]
    return Response(
        content=json.dumps(tag_list, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Last-Modified-Version": str(library.version),
            "Total-Results": str(len(tags)),
        },
    )


@router.delete("/{library_type}s/{library_id}/tags")
async def delete_tags(
    library_type: str,
    library_id: int,
    request: Request,
    tags: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not tags:
        raise HTTPException(status_code=400, detail="tags parameter required")

    library = await get_library(db, library_type, library_id, user)
    check_if_unmodified(request, library)

    tag_names = [t.strip() for t in tags.split("||") if t.strip()]
    if not tag_names:
        raise HTTPException(status_code=400, detail="No tag names provided")

    remove_set = set(tag_names)

    q = select(Item).where(
        and_(Item.library_id == library.id, Item.deleted == 0)
    )
    result = await db.execute(q)
    items = result.scalars().all()

    changed_items = []
    for item in items:
        item_data = item.data
        original_tags = item_data.get("tags", [])
        new_tags = [
            t for t in original_tags
            if (t.get("tag", "") if isinstance(t, dict) else t) not in remove_set
        ]
        if len(new_tags) != len(original_tags):
            item_data["tags"] = new_tags
            item.data_json = json.dumps(item_data, ensure_ascii=False)
            changed_items.append(item)

    if changed_items:
        await bump_version(db, library)
        for item in changed_items:
            item.version = library.version
        for tag_name in tag_names:
            log = SyncDeleteLog(
                library_id=library.id,
                object_type="tag",
                key=tag_name,
                version=library.version,
            )
            db.add(log)

    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )
