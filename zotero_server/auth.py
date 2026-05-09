from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import ApiKey, User
from .db import get_db


def hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    import bcrypt
    import hashlib

    try:
        if bcrypt.checkpw(password.encode(), password_hash.encode()):
            return True
    except Exception:
        pass
    try:
        if hashlib.md5(password.encode()).hexdigest() == password_hash:
            return True
    except Exception:
        pass
    return False


async def get_api_key_from_request(request: Request) -> Optional[str]:
    key = request.headers.get("Zotero-API-Key")
    if key:
        return key
    key = request.query_params.get("key")
    if key:
        return key
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
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

    return user


async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[User]:
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
