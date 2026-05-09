import logging
import re

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Library, User

_logger = logging.getLogger("zotero")


async def get_library(db: AsyncSession, library_type: str, library_id: int, user: User) -> Library:
    if library_type == "user":
        if library_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        result = await db.execute(select(Library).where(Library.id == user.library_id))
    elif library_type == "group":
        raise HTTPException(status_code=403, detail="Groups not supported")
    else:
        raise HTTPException(status_code=400, detail="Invalid library type")
    lib = result.scalar_one_or_none()
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    return lib


async def bump_version(db: AsyncSession, library: Library):
    library.version += 1
    library.last_updated = datetime.now(timezone.utc)
    await db.flush()


def check_if_modified(request, library: Library) -> bool:
    if_modified = request.headers.get("If-Modified-Since-Version")
    if if_modified is not None and library.version <= int(if_modified):
        return False
    return True


def check_if_unmodified(request, library: Library):
    if_unmodified = request.headers.get("If-Unmodified-Since-Version")
    if if_unmodified is not None and int(if_unmodified) != library.version:
        raise HTTPException(status_code=412, detail="Library has been modified")


def get_write_version(request, data: dict | None = None) -> int:
    header_version = request.headers.get("If-Unmodified-Since-Version")
    data_version = None if data is None else data.get("version")

    if header_version is None and data_version is None:
        raise HTTPException(
            status_code=428,
            detail="If-Unmodified-Since-Version or JSON version must be provided",
        )

    try:
        header_version_int = int(header_version) if header_version is not None else None
        data_version_int = int(data_version) if data_version is not None else None
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid version value")

    if (
        header_version_int is not None
        and data_version_int is not None
        and header_version_int != data_version_int
    ):
        raise HTTPException(
            status_code=400,
            detail="If-Unmodified-Since-Version does not match JSON version",
        )

    return header_version_int if header_version_int is not None else data_version_int


def check_object_write_version(request, obj, data: dict | None = None) -> int:
    version = get_write_version(request, data)
    if obj is None:
        if version > 0:
            raise HTTPException(status_code=412, detail="Object does not exist")
        return version
    if obj.version > version:
        raise HTTPException(status_code=412, detail="Object has been modified")
    return version


def get_batch_write_version(data: dict) -> int | None:
    version = data.get("version")
    if version is None:
        return None
    try:
        return int(version)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid version value")


def check_batch_object_write_version(obj, data: dict) -> int:
    version = get_batch_write_version(data)
    if obj is None:
        if version not in (None, 0):
            raise HTTPException(status_code=412, detail="Object does not exist")
        return 0
    if version is None:
        raise HTTPException(status_code=428, detail="JSON version must be provided")
    if version < obj.version:
        raise HTTPException(status_code=412, detail="Object has been modified")
    if version > obj.version:
        raise HTTPException(status_code=400, detail="Submitted version is newer than remote version")
    return version


_KEY_RE = re.compile(r"^[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}$")


def validate_object_key(key: str):
    if not _KEY_RE.match(key):
        raise HTTPException(status_code=400, detail=f"Invalid object key: {key}")


def _short_dict(d: dict, max_len: int = 800) -> str:
    import json
    s = json.dumps(d, ensure_ascii=False)
    if len(s) > max_len:
        return s[:max_len] + f"...({len(s)} chars)"
    return s


def validate_item_data(item_data: dict):
    item_type = item_data.get("itemType", "")
    key = item_data.get("key", "<no-key>")
    if not item_type:
        _logger.error("VALIDATE FAIL itemType missing for key=%s data=%s", key, _short_dict(item_data))
        raise HTTPException(status_code=400, detail="itemType is required")
    _logger.debug("VALIDATE OK key=%s itemType=%s", key, item_type)
    k = item_data.get("key")
    if k:
        validate_object_key(k)
    parent = item_data.get("parentItem")
    if parent:
        validate_object_key(parent)
