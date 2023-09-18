import asyncio
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, Optional

import httpx
import pytest
from py_dotenv import read_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.config import settings
from app.database import Base, get_async_session
from app.main import app

DB_TABLES: Dict[str, Optional[str]] = {
    "users": "users_id_seq",
    "companies": "companies_id_seq",
    "company_user": None,
    "company_request": "company_request_id_seq",
    "quizzes": "quizzes_id_seq",
    "questions": "questions_id_seq",
    "answers": "answers_id_seq",
}

# Activate venv
read_dotenv(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))

TEST_DATABASE_URL: str = settings.test_database_url


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, Any]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session', autouse=True)
async def prepare_database() -> None:
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
async def async_session_test() -> AsyncSession:
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield async_session


@pytest.fixture(scope="function", autouse=True)
async def clean_tables(async_session_test):
    """Clean data in all tables before running test function"""
    async with async_session_test() as session:
        async with session.begin():
            for table_for_cleaning, id_seq in DB_TABLES.items():
                await session.execute(text(f"DELETE FROM {table_for_cleaning};"))
                if id_seq:
                    await session.execute(text(f"ALTER SEQUENCE {id_seq} RESTART WITH 1;"))


async def _get_test_async_session() -> AsyncGenerator[AsyncSession, Any]:
    try:
        # create async engine for interaction with test database
        test_engine = create_async_engine(
            TEST_DATABASE_URL, future=True, echo=True
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
