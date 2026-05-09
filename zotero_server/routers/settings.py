import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import Library, Setting, SyncDeleteLog, User
from ..db import get_db
from ..library import (
    bump_version,
    check_if_modified,
    check_if_unmodified,
    check_object_write_version,
    get_library,
)

router = APIRouter()


@router.get("/{library_type}s/{library_id}/settings")
async def list_settings(
    library_type: str,
    library_id: int,
    request: Request,
    since: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    if not check_if_modified(request, library):
        return Response(status_code=304, headers={"Last-Modified-Version": str(library.version)})

    q = select(Setting).where(Setting.library_id == library.id)
    if since is not None:
        q = q.where(Setting.version > since)

    result = await db.execute(q)
    settings = result.scalars().all()

    response_data = {}
    for s in settings:
        response_data[s.name] = {"value": s.value, "version": s.version}

    return Response(
        content=json.dumps(response_data, ensure_ascii=False),
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.post("/{library_type}s/{library_id}/settings")
async def update_settings(
    library_type: str,
    library_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)
    check_if_unmodified(request, library)

    body = await request.body()
    settings_data = json.loads(body)

    for name, raw_value in settings_data.items():
        if isinstance(raw_value, dict) and "value" in raw_value:
            value = raw_value["value"]
        else:
            value = raw_value
        result = await db.execute(
            select(Setting).where(
                and_(Setting.library_id == library.id, Setting.name == name)
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value_json = json.dumps(value, ensure_ascii=False)
            await bump_version(db, library)
            setting.version = library.version
        else:
            new_setting = Setting(
                library_id=library.id,
                name=name,
                value_json=json.dumps(value, ensure_ascii=False),
            )
            await bump_version(db, library)
            new_setting.version = library.version
            db.add(new_setting)

    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.delete("/{library_type}s/{library_id}/settings")
async def delete_settings(
    library_type: str,
    library_id: int,
    request: Request,
    settingKey: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not settingKey:
        raise HTTPException(status_code=400, detail="settingKey required")

    library = await get_library(db, library_type, library_id, user)
    check_if_unmodified(request, library)

    keys = [k.strip() for k in settingKey.split(",") if k.strip()]
    for name in keys:
        result = await db.execute(
            select(Setting).where(
                and_(Setting.library_id == library.id, Setting.name == name)
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            await bump_version(db, library)
            log = SyncDeleteLog(
                library_id=library.id,
                object_type="setting",
                key=name,
                version=library.version,
            )
            db.add(log)
            await db.delete(setting)

    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.get("/{library_type}s/{library_id}/settings/{setting_name}")
async def get_setting(
    library_type: str,
    library_id: int,
    setting_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    result = await db.execute(
        select(Setting).where(
            and_(Setting.library_id == library.id, Setting.name == setting_name)
        )
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    return Response(
        content=json.dumps({"value": setting.value, "version": setting.version}, ensure_ascii=False),
        media_type="application/json",
        headers={"Last-Modified-Version": str(library.version)},
    )


@router.put("/{library_type}s/{library_id}/settings/{setting_name}")
async def put_setting(
    library_type: str,
    library_id: int,
    setting_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    body = await request.body()
    raw_value = json.loads(body)
    value = raw_value.get("value", raw_value) if isinstance(raw_value, dict) else raw_value

    result = await db.execute(
        select(Setting).where(
            and_(Setting.library_id == library.id, Setting.name == setting_name)
        )
    )
    setting = result.scalar_one_or_none()

    if setting:
        check_object_write_version(request, setting, raw_value)
    else:
        check_object_write_version(request, None, raw_value)

    await bump_version(db, library)

    if setting:
        setting.value_json = json.dumps(value, ensure_ascii=False)
        setting.version = library.version
    else:
        setting = Setting(
            library_id=library.id,
            name=setting_name,
            value_json=json.dumps(value, ensure_ascii=False),
            version=library.version,
        )
        db.add(setting)

    await db.flush()

    return Response(status_code=204, headers={"Last-Modified-Version": str(library.version)})


@router.delete("/{library_type}s/{library_id}/settings/{setting_name}")
async def delete_setting(
    library_type: str,
    library_id: int,
    setting_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    library = await get_library(db, library_type, library_id, user)

    result = await db.execute(
        select(Setting).where(
            and_(Setting.library_id == library.id, Setting.name == setting_name)
        )
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    check_object_write_version(request, setting)

    await bump_version(db, library)

    log = SyncDeleteLog(
        library_id=library.id,
        object_type="setting",
        key=setting_name,
        version=library.version,
    )
    db.add(log)
    await db.delete(setting)
    await db.flush()

    return Response(
        status_code=204,
        headers={"Last-Modified-Version": str(library.version)},
    )
