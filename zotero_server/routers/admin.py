import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import hash_password
from ..database import ApiKey, Library, User
from ..db import get_db

router = APIRouter()

ADMIN_TOKEN = None


def _get_admin_token():
    global ADMIN_TOKEN
    if ADMIN_TOKEN is None:
        import os
        ADMIN_TOKEN = os.environ.get("ZOTERO_ADMIN_TOKEN", "")
    return ADMIN_TOKEN


def _check_admin(request):
    expected = _get_admin_token()
    if not expected:
        raise HTTPException(status_code=403, detail="Admin API disabled: set ZOTERO_ADMIN_TOKEN")
    auth = request.headers.get("Authorization", "")
    token = request.query_params.get("admin_token", "")
    if auth == f"Bearer {expected}" or token == expected:
        return True
    raise HTTPException(status_code=403, detail="Admin token required")


@router.post("/admin/users")
async def create_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)

    body = await request.body()
    data = json.loads(body)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    library = Library(type="user")
    db.add(library)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Conflict creating library")

    user = User(
        username=username,
        password_hash=hash_password(password),
        library_id=library.id,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists")

    key_str = "".join(
        secrets.choice("23456789ABCDEFGHIJKLMNPQRSTUVWXYZ") for _ in range(24)
    )
    api_key = ApiKey(
        user_id=user.id,
        key=key_str,
        name="Default Key",
    )
    db.add(api_key)
    await db.flush()

    return {
        "id": user.id,
        "username": user.username,
        "library_id": user.library_id,
        "api_key": key_str,
    }


@router.get("/admin/users")
async def list_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)

    result = await db.execute(select(User))
    users = result.scalars().all()

    data = []
    for u in users:
        keys_result = await db.execute(select(ApiKey).where(ApiKey.user_id == u.id))
        keys = keys_result.scalars().all()
        data.append({
            "id": u.id,
            "username": u.username,
            "library_id": u.library_id,
            "api_keys": [{"key": k.key, "name": k.name} for k in keys],
        })

    return Response(content=json.dumps(data, ensure_ascii=False), media_type="application/json")


@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.flush()

    return {"status": "deleted"}
