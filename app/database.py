from typing import AsyncGenerator

import redis.asyncio as rd
from sqlalchemy.ext.asyncio import (AsyncAttrs, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import DeclarativeBase

from .config import settings

redis = rd.from_url(settings.redis_url, decode_responses=True, encoding="utf-8", db=0)

class Base(AsyncAttrs, DeclarativeBase):
    pass

engine = create_async_engine(settings.database_url, echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
