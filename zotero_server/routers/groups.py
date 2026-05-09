import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import User
from ..db import get_db

router = APIRouter()


@router.get("/users/{user_id}/groups")
async def list_groups(
    user_id: int,
    format: str = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if format == "versions":
        return Response(
            content="{}",
            media_type="application/json",
            headers={"Last-Modified-Version": "0"},
        )

    return Response(
        content="[]",
        media_type="application/json",
        headers={"Last-Modified-Version": "0"},
    )
