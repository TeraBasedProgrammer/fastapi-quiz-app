from datetime import datetime
from typing import Any, Awaitable, Callable

import pytest
from auth.handlers import AuthHandler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.users.models import User

DEFAULT_USER_DATA = {
    "id": 1,
    "email": "test@email.com",
    "name": "ilya",
    "password": "password123"
}

@pytest.fixture
async def get_user_by_id(async_session_test: AsyncSession) -> Callable[[str], Awaitable[list]]:
    async def get_user_by_id(user_id: str) -> list:
        async with async_session_test() as session:
            result = await session.execute(select(User).options(joinedload(User.companies)).where(User.id == user_id))
            user = result.unique().scalar_one_or_none()
            return [user] if user else []
    return get_user_by_id


@pytest.fixture(scope='function')
async def create_raw_user(async_session_test: AsyncSession) -> Callable[[str, str, str], Awaitable[None]]:
    async def create_raw_user(email: str, name: str, password: str) -> None:
        auth = AuthHandler()
        hashed_password = await auth.get_password_hash(password)

        async with async_session_test() as session:
            user = User(
                email=email,
                password=hashed_password,
                name=name,
                registered_at=datetime.utcnow(),
                auth0_registered=False)
            session.add(user)
            await session.commit()

    return create_raw_user


@pytest.fixture(scope="function")
async def create_user_instance(create_raw_user) -> Callable[[str, str, str], Awaitable[dict[str, Any]]]:
    async def create_user_instance(email: str = DEFAULT_USER_DATA["email"],
                                   name: str = DEFAULT_USER_DATA["name"],
                                   password: str = DEFAULT_USER_DATA["password"]) -> dict[str, Any]:
        await create_raw_user(email=email, name=name, password=password)
        return {
            "email": email,
            "name": name,
            "password": password
        }

    return create_user_instance