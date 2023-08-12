import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.company_requests.schemas import (UserInvitationSchema,
                                          UserRequestSchema)
from app.company_requests.services import CompanyRequestsRepository
from app.database import get_async_session
from app.schemas import UserFullSchema
from app.users.services import UserRepository, error_handler
from app.utils import get_current_user_id

from .handlers import AuthHandler
from .schemas import UserLogin, UserSignUp

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

auth_router = APIRouter(
    tags=["Auth"],
    responses={404: {"description": "Not found"}}
)


@auth_router.post("/signup", response_model=Optional[Dict[str, Any]], status_code=201)
async def signup(user: UserSignUp, session: AsyncSession = Depends(get_async_session)) -> Optional[Dict[str, str]]:
    logger.info(f"Creating new User instance")
    crud = UserRepository(session)
    user_existing_object = await crud.get_user_by_email(user.email)
    if user_existing_object: 
        logger.warning(f"Validation error: User with email \"{user.email}\" already exists")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("User with this email already exists"))
    result = await crud.create_user(user)
    logger.info(f"New user instance has been successfully created")
    return result


@auth_router.post("/login")
async def login(user: UserLogin, session: AsyncSession = Depends(get_async_session)) -> Optional[Dict[str, str]]:
    logger.info(f"Login attemp with email \"{user.email}\"")

    crud = UserRepository(session)
    user_existing_object = await crud.get_user_by_email(user.email)
    if not user_existing_object:
        logger.warning(f"User with email \"{user.email}\" is not registered in the system")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("User with this email is not registered in the system"))

    verify_password = await auth_handler.verify_password(user.password, user_existing_object.password)
    if not verify_password:
        logger.warning(f"Invalid password was provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("Invalid password"))

    logger.info(f"User \"{user.email}\" successfully logged in the system")
    auth_token = await auth_handler.encode_token(user.email, session)
    return {"token": auth_token}


@auth_router.get("/me", response_model=Optional[UserFullSchema], response_model_exclude_none=True)
async def get_current_user(session: AsyncSession = Depends(get_async_session),
                           auth=Depends(auth_handler.auth_wrapper)) -> Optional[UserFullSchema]:
    logger.info(f"Accessing current user info")
    crud = UserRepository(session)

    current_user = await crud.get_user_by_email(auth['email'])

    logger.info(f"Successfully returned current user info")
    return await UserFullSchema.from_model(current_user, public_request=False)


@auth_router.get("/me/invitations", response_model=Optional[List[UserInvitationSchema]], response_model_exclude_none=True)
async def get_received_invitations(session: AsyncSession = Depends(get_async_session),
                           auth=Depends(auth_handler.auth_wrapper)) -> Optional[List[UserInvitationSchema]]:
    logger.info(f"Retrieving current user invitations list")

    # Initialize services
    request_crud = CompanyRequestsRepository(session)
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    res = await request_crud.get_received_requests(receiver_id=current_user_id)
    logger.info(f"Successfully retrieved current user invitations list")
    return res


@auth_router.get("/me/requests", response_model=Optional[List[UserRequestSchema]], response_model_exclude_none=True)
async def get_sent_requests(session: AsyncSession = Depends(get_async_session),
                           auth=Depends(auth_handler.auth_wrapper)) -> Optional[List[UserRequestSchema]]:
    logger.info(f"Retrieving current user sent requests list")
    
    # Initialize services
    request_crud = CompanyRequestsRepository(session)
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    res = await request_crud.get_sent_requests(sender_id=current_user_id)
    logger.info(f"Successfully retrieved current user sent requests list")
    return res
