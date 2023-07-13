import uvicorn

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis

from .db.database import get_db
from .config import settings


app = FastAPI()
redis = aioredis.from_url(settings.redis_url, decode_responses=True, encoding="utf-8", db=0)


origins = [
    "http://localhost:8000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status_code": 200, "detail": "ok", "result": "working"}

@app.get("/test-postgres")
async def postgres_connect(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"message": "Database connection successful"}
    except SQLAlchemyError as e:
        return {"message": "Database connection failed", "exception": f"{e.args[0]}"}
    

@app.get("/test-redis")
async def redis_connect():
    await redis.set("Ryan Gosling", "Literally me")
    value = await redis.get("Ryan Gosling")
    if value:
        return {"message": f"Redis works! Ryan gosling is {value}"}
    return {"error": "You are not Ryan Gosling, redis doesn't work"} 



if __name__ == '__main__':
    uvicorn.run('app.main:app', port=settings.port, reload=True)