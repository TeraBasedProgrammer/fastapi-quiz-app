from typing import Awaitable, Callable, TypeAlias

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.handlers import AuthHandler

Jwt: TypeAlias = str

@pytest.fixture(scope="function")
async def create_auth_jwt(async_session_test: AsyncSession) -> Callable[[str], Awaitable[Jwt]]:
    async def create_auth_jwt(user_email: str) -> Jwt:
        async with async_session_test() as session:
            auth = AuthHandler()
            token = await auth.encode_token(user_email, session)
            return token

    return create_auth_jwt