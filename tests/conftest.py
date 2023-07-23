import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Awaitable

import pytest
import httpx
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from py_dotenv import read_dotenv

from app.main import app
from app.config import settings
from app.database import get_async_session, Base
from auth.handlers import AuthHandler

# Activate venv
read_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))

DATABASE_URL: str = settings.test_database_url


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, Any]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def async_session_test() -> AsyncGenerator[AsyncSession, Any]:
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield async_session


@pytest.fixture(scope='function', autouse=True)
async def prepare_database() -> None:
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _get_test_async_session() -> AsyncGenerator[AsyncSession, Any]:
    try:
        # create async engine for interaction with test database
        test_engine = create_async_engine(
            DATABASE_URL, future=True, echo=True
        )

        # create async session for the interaction with test database
        test_async_session = async_sessionmaker(
            test_engine, expire_on_commit=False, class_=AsyncSession
        )
        async with test_async_session() as session:
            yield session
    finally:
        pass


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[httpx.AsyncClient, Any]:
    app.dependency_overrides[get_async_session] = _get_test_async_session
    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="session")
async def asyncpg_pool() -> AsyncGenerator[asyncpg.pool.Pool, Any]:
    pool = await asyncpg.create_pool(
        "".join(DATABASE_URL.split("+asyncpg"))
    )
    yield pool
    await pool.close() 


@pytest.fixture
async def get_user_by_id(asyncpg_pool) -> Awaitable[list]:
    async def get_user_by_id(user_id: str) -> list:
        async with asyncpg_pool.acquire() as connection:
            return await connection.fetch(
                "SELECT * FROM users WHERE id = %s;" % user_id
            )

    return get_user_by_id  
    

@pytest.fixture(scope='function')
async def create_raw_user(asyncpg_pool) -> Awaitable[None]:
    async def create_raw_user(email: str = "test@email.com", 
                              name: str = "ilya",
                              password: str = "password123") -> None:
        auth = AuthHandler()
        hashed_password = auth.get_password_hash(password)
        async with asyncpg_pool.acquire() as connection:
            return await connection.execute(
                "INSERT INTO users (email, name, password, registered_at, auth0_registered) VALUES ('%s', '%s', '%s', '%s', '%s')" 
                 % (email, name, hashed_password, datetime.utcnow(), False)
            )

    return create_raw_user
        