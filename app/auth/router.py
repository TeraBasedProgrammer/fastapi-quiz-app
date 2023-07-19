import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, Params, paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_async_session
from app.users.schemas import UserSchema
from .schemas import UserSignUp, UserLogin
from .handlers import AuthHandler
from app.users.services import UserRepository, error_handler


logger = logging.getLogger("main_logger")

auth_router = APIRouter(
    tags=["auth"],
    responses={404: {"description": "Not found"}}
)


@auth_router.post("/signup", response_model=UserSchema, status_code=201)
async def signup(user: UserSignUp, session: AsyncSession = Depends(get_async_session)):
    logger.info(f"Trying to create new User instance")
    crud = UserRepository(session)
    user_existing_object = await crud.get_user_by_email(user.email)
    if user_existing_object: 
        logger.warning(f"Validation error: User with email '{user.email}' already exists")
        raise HTTPException(400, detail=error_handler("User with this email already exists"))
    result = await crud.create_user(user)
    logger.info(f"New user instance has been successfully created")
    return result


@auth_router.post("/login")
async def login(user: UserLogin, session: AsyncSession = Depends(get_async_session)):
    logger.info(f"Login attemp with email {user.email}")
    auth_handler = AuthHandler()

    crud = UserRepository(session)
    user_existing_object = await crud.get_user_by_email(user.email)
    if not user_existing_object:
        logger.warning(f"User with email {user.email} is not registered in the system")
        raise HTTPException(400, detail=error_handler("User with this email is not registered in the system"))

    verify_password = auth_handler.verify_password(user.password, user_existing_object.password)
    if not verify_password:
        logger.warning(f"Invalid password provided")
        raise HTTPException(400, detail=error_handler("Invalid password"))

    logger.info(f"User {user.email} successfully logged in the system")
    auth_token = auth_handler.encode_token(user.email)
    return {"token": auth_token}