import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.schemas import UserFullSchema
from app.users.services import UserRepository, error_handler

from .handlers import AuthHandler
from .schemas import UserLogin, UserSignUp

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

auth_router = APIRouter(
    tags=["Auth"],
    responses={404: {"description": "Not found"}}
)


@auth_router.post("/signup", response_model=Optional[UserFullSchema], status_code=201, response_model_exclude={"role"})
async def signup(user: UserSignUp, session: AsyncSession = Depends(get_async_session)) -> Optional[UserFullSchema]:
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
async def login(user: UserLogin, session: AsyncSession = Depends(get_async_session)) -> Optional[Dict[str, str]]:
    logger.info(f"Login attemp with email {user.email}")

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


@auth_router.get("/me", response_model=Optional[UserFullSchema], response_model_exclude={"role"})
async def get_current_user(session: AsyncSession = Depends(get_async_session),
                           auth=Depends(auth_handler.auth_wrapper)) -> Optional[UserFullSchema]:
    logger.info(f"Accessing current user info")
    crud = UserRepository(session)

    current_user = await crud.get_user_by_email(auth['email'])
    logger.info(f"Successfully returned current user ({auth['email']}) info")
    return current_user