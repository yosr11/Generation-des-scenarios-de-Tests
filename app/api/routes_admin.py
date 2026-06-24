from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.postgres import get_db
from app.services.auth_service import create_user

router = APIRouter(prefix="/admin", tags=["Admin"])


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "tester"


class CreateUserResponse(BaseModel):
    email: EmailStr
    role: str


@router.post("/users", response_model=CreateUserResponse)
async def admin_create_user(
    body: CreateUserRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not getattr(current_user, "role", None) or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create users")

    result = await create_user(db, body.email, body.password, body.role)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unable to create user"))

    return CreateUserResponse(email=body.email, role=body.role)
