from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import api_error
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> Sequence[User]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    existing = await get_user_by_email(db, payload.email)
    if existing is not None:
        raise api_error(
            status_code=409,
            code="user_email_taken",
            message="A user with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession, user_id: int, payload: UserUpdate
) -> User | None:
    user = await get_user(db, user_id)
    if user is None:
        return None

    data = payload.model_dump(exclude_unset=True)

    if "email" in data and data["email"] != user.email:
        if await get_user_by_email(db, data["email"]) is not None:
            raise api_error(
                status_code=409,
                code="user_email_taken",
                message="A user with this email already exists.",
            )
        user.email = data["email"]

    if "full_name" in data:
        user.full_name = data["full_name"]

    if "is_active" in data:
        user.is_active = data["is_active"]

    if "password" in data and data["password"] is not None:
        user.hashed_password = hash_password(data["password"])

    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    user = await get_user(db, user_id)
    if user is None:
        return False
    await db.delete(user)
    await db.commit()
    return True
