import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, Params, paginate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.handlers import AuthHandler
from app.auth.services import confirm_current_user
from app.database import get_async_session
from app.schemas import UserFullSchema

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
    logger.info("Getting all user from the database")
    crud = UserRepository(session)
    result = await crud.get_users() 
    logger.info("All user have been successfully retrieved")

    response = [UserFullSchema.from_model(u) for u in result]
    return paginate(response, params)
    


@user_router.get("/{user_id}", response_model=Optional[UserFullSchema], response_model_exclude_none=True)
async def get_user(user_id: int, 
                   session: AsyncSession = Depends(get_async_session),
                   auth=Depends(auth_handler.auth_wrapper)) -> Optional[UserSchema]:
    logger.info(f"Trying to get User instance by id '{user_id}'")
    crud = UserRepository(session)
    info = await crud.get_user_by_id(user_id)
    if not info:
        logger.warning(f"User '{user_id}' is not found")
        raise HTTPException(404, error_handler("User is not found"))
    logger.info(f"Successfully retrieved User instance '{user_id}'")
    return UserFullSchema.from_model(info)


@user_router.patch("/{user_id}/update", response_model=Optional[UserFullSchema], response_model_exclude_none=True)
async def update_user(user_id: int, body: UserUpdateRequest, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[UserSchema]:
    logger.info(f"Trying to update User instance '{user_id}'")
    crud = UserRepository(session)
    updated_user_params = body.model_dump(exclude_none=True)
    if updated_user_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(
            status_code=400,
            detail=error_handler("At least one parameter should be provided for user update query"),
        )
    
    try:
        user_for_update = await crud.get_user_by_id(user_id)
        if not user_for_update:
            logger.warning(f"User '{user_id}' is not found")
            raise HTTPException(
                status_code=404, detail=error_handler("User is not found")
            )
        
        # Check persmissions
        await confirm_current_user(crud, auth['email'], user_id)
        
        logger.info(f"User {user_id} have been successfully updated")
        return UserFullSchema.from_model(await crud.update_user(user_id, body))
    except IntegrityError:
        logger.warning(f"Validation error: User with provided email already exists")
        raise HTTPException(400, detail=error_handler("User with this email already exists"))


@user_router.delete("/{user_id}/delete", response_model=Optional[DeletedInstanceResponse])
async def delete_user(user_id: int, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    logger.info(f"Trying to delete User instance '{user_id}'")
    crud = UserRepository(session)

    # Check if user exists
    user_for_deletion = await crud.get_user_by_id(user_id)
    if not user_for_deletion:
        logger.warning(f"User '{user_id}' is not found")
        raise HTTPException(
            status_code=404, detail=error_handler("User is not found")
        )
    
    # Check persmissions
    await confirm_current_user(crud, auth['email'], user_id)

    deleted_user_id = await crud.delete_user(user_id)
    logger.info(f"User {user_id} has been successfully deleted from the database")
    return DeletedInstanceResponse(deleted_instance_id=deleted_user_id)
