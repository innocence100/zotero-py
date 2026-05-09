import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_api_key_from_request, hash_password, verify_password
from ..database import ApiKey, User
from ..db import get_db

router = APIRouter()


@router.get("/keys/current")
async def get_current_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    api_key_str = await get_api_key_from_request(request)
    if not api_key_str:
        raise HTTPException(status_code=403, detail="API key required")

    result = await db.execute(select(ApiKey).where(ApiKey.key == api_key_str))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=403, detail="User not found")

    return Response(
        content=json.dumps({
            "key": api_key.key,
            "userID": user.id,
            "username": user.username,
            "displayName": user.username,
            "access": api_key.access,
        }),
        media_type="application/json",
    )


@router.delete("/keys/current")
async def delete_current_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    api_key_str = await get_api_key_from_request(request)
    if not api_key_str:
        raise HTTPException(status_code=403, detail="API key required")

    result = await db.execute(select(ApiKey).where(ApiKey.key == api_key_str))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    await db.delete(api_key)
    await db.flush()
    return Response(status_code=204)


@router.post("/keys")
async def create_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        raise HTTPException(status_code=403, detail="Username and password required")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=403, detail="Invalid username/password")

    key_str = "".join(
        secrets.choice("23456789ABCDEFGHIJKLMNPQRSTUVWXYZ") for _ in range(24)
    )

    access = data.get("access")
    api_key = ApiKey(
        user_id=user.id,
        key=key_str,
        name=data.get("name", "Automatic Zotero Client Key"),
        access_json=json.dumps(access, ensure_ascii=False) if access else None,
    )
    db.add(api_key)
    await db.flush()

    return Response(
        content=json.dumps({
            "key": key_str,
            "userID": user.id,
            "username": user.username,
            "displayName": user.username,
            "access": api_key.access,
        }),
        media_type="application/json",
        status_code=201,
    )
