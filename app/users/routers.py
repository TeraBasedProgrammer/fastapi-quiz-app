from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException
# from fastapi_pagination import Page, paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_async_session
from .schemas import UserSchema, UserCreate, DeleteUserResponse, UserUpdateRequest
from .services import UserRepository

user_router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}}
)


@user_router.get("/", response_model=List[UserSchema])
async def get_users(session: AsyncSession = Depends(get_async_session)):
    crud = UserRepository(session)
    return await crud.get_users()


@user_router.get("/{user_id}", response_model=Union[UserSchema, None])
async def get_user_by_id(user_id: int, session: AsyncSession = Depends(get_async_session)):
    crud = UserRepository(session)
    info = await crud.get_user_by_id(user_id)
    if not info:
        raise HTTPException(404, {"error": "User not found"})
    return info


@user_router.post("/", response_model=UserSchema)
async def create_user(user: UserCreate, session: AsyncSession = Depends(get_async_session)):
    crud = UserRepository(session)
    user_existing_object = await crud.get_user_by_email(user.email)
    if user_existing_object: 
        raise HTTPException(400, detail= {"error": "User with this email already exists"})
    return await crud.create_user(user)


@user_router.patch("/{user_id}/update", response_model=Union[UserSchema, None])
async def update_user(user_id: int, body: UserUpdateRequest, session: AsyncSession = Depends(get_async_session)) -> UserSchema:
    crud = UserRepository(session)
    updated_user_params = body.model_dump(exclude_none=True)
    if updated_user_params == {}:
        raise HTTPException(
            status_code=400,
            detail="At least one parameter should be provided for user update query",
        )
    try:
        user_for_update = await crud.get_user_by_id(user_id)
        if not user_for_update:
            raise HTTPException(
                status_code=404, detail="User not found"
            )
        return await crud.update_user(user_id, body)
    except IntegrityError:
        raise HTTPException(400, detail= {"error": "User with this email already exists"})


@user_router.delete("/{user_id}/delete", response_model=Union[DeleteUserResponse, None])
async def delete_user(user_id: int, session: AsyncSession = Depends(get_async_session)) -> DeleteUserResponse:
    crud = UserRepository(session)
    user_for_deletion = await crud.get_user_by_id(user_id)
    if not user_for_deletion:
        raise HTTPException(
            status_code=404, detail=f"User not found"
        )
    deleted_user_id = await crud.delete_user(user_id)
    return DeleteUserResponse(deleted_user_id=deleted_user_id)
