import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, Params, paginate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth.handlers import AuthHandler
from app.database import get_async_session
from app.schemas import UserFullSchema
from app.utils import get_current_user_id

from .schemas import DeletedInstanceResponse, UserSchema, UserUpdateRequest
from .services import UserRepository, error_handler

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

user_router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}}
)


@user_router.get("/", response_model=Page[UserFullSchema], response_model_exclude_none=True)
async def get_users(session: AsyncSession = Depends(get_async_session),
                    params: Params = Depends(),
                    auth=Depends(auth_handler.auth_wrapper)) -> Page[UserFullSchema]:
    logger.info("Retrieving all user from the database")
    user_crud = UserRepository(session)
    result = await user_crud.get_users() 
    logger.info("All user have been successfully retrieved")

    response = [await UserFullSchema.from_model(u) for u in result]
    return paginate(response, params)
    


@user_router.get("/{user_id}/", response_model=Optional[UserFullSchema], response_model_exclude_none=True)
async def get_user(user_id: int, 
                   session: AsyncSession = Depends(get_async_session),
                   auth=Depends(auth_handler.auth_wrapper)) -> Optional[UserSchema]:
    logger.info(f"Retrieving User instance by id \"{user_id}\"")
    user_crud = UserRepository(session)
    user = await user_crud.get_user_by_id(user_id)
    if not user:
        logger.warning(f"User \"{user_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, error_handler("User is not found"))
    logger.info(f"Successfully retrieved User instance \"{user}\"")
    return await UserFullSchema.from_model(user)


@user_router.patch("/{user_id}/update/", response_model=Optional[UserFullSchema], response_model_exclude_none=True)
async def update_user(user_id: int, body: UserUpdateRequest, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[UserSchema]:
    logger.info(f"Updating User instance \"{user_id}\"")
    user_crud = UserRepository(session)
    updated_user_params = body.model_dump(exclude_none=True)
    if updated_user_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("At least one parameter should be provided for user update query"))
    
    try:
        # Retrieving current user id
        current_user_id = await get_current_user_id(session, auth)

        # Validate if requested user is current user
        if user_id != current_user_id:
            logger.warning(f"Permission error: User \"{user_id}\" is not a current user")
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

        user_for_update = await user_crud.get_user_by_id(user_id)
        if not user_for_update:
            logger.warning(f"User \"{user_id}\" is not found")
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("User is not found")
            )
         
        logger.info(f"User \"{user_id}\" have been successfully updated")
        return await UserFullSchema.from_model(await user_crud.update_user(user_id, body), public_request=False)
    except IntegrityError:
        logger.warning(f"Validation error: User with provided email already exists")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("User with this email already exists"))


@user_router.delete("/{user_id}/delete/", response_model=Optional[DeletedInstanceResponse])
async def delete_user(user_id: int, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    logger.info(f"Deleting User instance \"{user_id}\"")
    user_crud = UserRepository(session)

    # Retrieving current user id
    current_user = await user_crud.get_user_by_email(auth["email"]) if not auth.get("id") else None
    current_user_id = auth.get("id") if not current_user else current_user.id

    # Validate if requested user is current user
    if user_id != current_user_id:
        logger.warning(f"Permission error: User \"{user_id}\" is not a current user")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

    # Check if user exists
    user_for_deletion = await user_crud.get_user_by_id(user_id)
    if not user_for_deletion:
        logger.warning(f"User \"{user_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("User is not found"))
    
    deleted_user_id = await user_crud.delete_user(user_id)
    logger.info(f"User \"{user_id}\" has been successfully deleted from the database")
    return DeletedInstanceResponse(deleted_instance_id=deleted_user_id)
 