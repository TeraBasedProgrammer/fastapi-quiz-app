import uvicorn
from typing import List

import redis.asyncio as rd
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException
from fastapi.exceptions import ResponseValidationError 

from .db.database import get_session, init_db
from .config import settings
from .schemas.users import UserSchema, UserCreate
from .models.models import User


app = FastAPI()
redis = rd.from_url(settings.redis_url, decode_responses=True, encoding="utf-8", db=0)


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

@app.exception_handler(ResponseValidationError)
async def validation_exception_handler(request: Request, exc: ResponseValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


@app.get("/users/", response_model=list[UserSchema])
async def get_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [UserSchema(id=u.id, email=u.email, username=u.username, registered_at=str(u.registered_at)) for u in users]


@app.post("/users/", response_model=UserSchema)
async def add_user(user: UserCreate, session: AsyncSession = Depends(get_session)):
    new_user = User(username=user.username, password=user.password, email=user.email)
    session.add(new_user)
    try:
        await session.commit()
        return new_user
    except IntegrityError as ex:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"The user with username \"{user.username}\" already exists",
        )


@app.get("/test-postgres")
async def postgres_connect(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
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