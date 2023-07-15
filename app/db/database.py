from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


from app.core.config import settings


engine = create_async_engine(settings.database_url, echo=True)

AsyncSessionFactory = async_sessionmaker(engine, autoflush=False, expire_on_commit=False, class_=AsyncSession)

# Dependency
async def get_session() -> AsyncGenerator:
    async with AsyncSessionFactory() as session:
        yield session

        
class Base(AsyncAttrs, DeclarativeBase):
    pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
