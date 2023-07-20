import asyncio
import os
from pathlib import Path
from typing import Any
from typing import AsyncGenerator

import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from py_dotenv import read_dotenv

from app.main import app
from app.config import settings
from app.database import get_async_session, Base

# Activate venv
read_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))

DATABASE_URL = settings.test_database_url


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def async_session_test():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield async_session


@pytest.fixture(scope='session', autouse=True)
async def prepare_database():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _get_test_async_session():
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
        