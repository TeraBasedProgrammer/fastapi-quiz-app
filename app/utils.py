from typing import Type, Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete

from .database import Base


async def get_global_user_crud(session: AsyncSession):
    # Local import to avoid circular import
    from app.users.services import UserRepository
    return UserRepository(session)


async def get_global_company_crud(session: AsyncSession):
    # Local import to avoid circular import
    from app.companies.services import CompanyRepository
    return CompanyRepository(session)


async def get_global_company_request_crud(session: AsyncSession):
    # Local import to avoid circular import
    from app.company_requests.services import CompanyRequestsRepository
    return CompanyRequestsRepository(session)


async def get_current_user_id(session: AsyncSession, auth) -> int:
    user_crud = await get_global_user_crud(session)

    current_user = await user_crud.get_user_by_email(auth["email"]) if not auth.get("id") else None
    current_user_id = auth.get("id") if not current_user else current_user.id
    return current_user_id


async def create_model_instance(session: AsyncSession, model: Base, model_data: Type[BaseModel]) -> Type[Base]:
    new_model = model(
        **model_data.model_dump() 
    )

    # Insert new company object into the db (without commiting)
    session.add(new_model)
    return new_model


async def update_model_instance(
          session: AsyncSession, 
          model: Base, 
          instance_id: int, 
          model_data: Type[BaseModel]) -> Type[Base]:
    query = (
        update(model)
        .where(model.id == instance_id)
        .values({key: value for key, value in model_data.model_dump().items() if value is not None})
        .returning(model)
    )
    res = await session.execute(query)
    await session.commit()
    return res.scalar_one()


async def delete_model_instance(session: AsyncSession, model: Base, instance_id: int) -> int:
    query = (
        delete(model)
        .where(model.id == instance_id)
        .returning(model.id)
    )

    result = (await session.execute(query)).scalar_one()
    await session.commit()
    return result
    