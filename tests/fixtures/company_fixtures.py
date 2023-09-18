from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.companies.models import Company, CompanyUser, RoleEnum
from app.company_requests.models import CompanyRequest

DEFAULT_COMPANY_DATA = {
    "id": 1,
    "title": "MyCompany",
    "description": "Description",
    "is_hidden": False
}

@pytest.fixture(scope='function')
async def create_raw_company(async_session_test: AsyncSession) -> Callable[[str, str, bool], Awaitable[None]]:
    async def create_raw_company(title: str, description: str, is_hidden: bool) -> None:
        async with async_session_test() as session:
            company = Company(
                title=title,
                description=description,
                is_hidden=is_hidden,
                created_at=datetime.utcnow())
            session.add(company)
            await session.commit()
    return create_raw_company


@pytest.fixture(scope="function")
async def create_company_instance(create_raw_company) -> Callable[[str, str, bool], Awaitable[dict[str, Any]]]:
    async def create_company_instance(title: str = DEFAULT_COMPANY_DATA["title"],
                                   description: str = DEFAULT_COMPANY_DATA["description"],
                                   is_hidden: bool = DEFAULT_COMPANY_DATA["is_hidden"]) -> dict[str, Any]:
        await create_raw_company(title=title, description=description, is_hidden=is_hidden)
        return {
            "title": title,
            "description": description,
            "is_hidden": is_hidden
        }

    return create_company_instance


@pytest.fixture(scope="function")
async def create_user_company_instance(async_session_test: AsyncSession) -> Callable[[str, str, RoleEnum], Awaitable[None]]:
    async def create_user_company_instance(user_id: int = 1, company_id: int = 1, role = RoleEnum.Owner) -> None:
        async with async_session_test() as session:
            company_user = CompanyUser(
                company_id=company_id,
                user_id=user_id,
                role=role
            )
            session.add(company_user)
            await session.commit()
    return create_user_company_instance


@pytest.fixture(scope="function")
async def create_default_company_object(create_company_instance,
                                        create_user_instance,
                                        create_user_company_instance) -> Callable[[None], Awaitable[None]]:
    async def create_default_company_object() -> None:
        await create_company_instance()
        await create_user_instance()
        await create_user_company_instance()
    return create_default_company_object

@pytest.fixture(scope="function")
async def create_company_request_instance(async_session_test: AsyncSession) -> Callable[[int, Optional[int], Optional[int]], Awaitable[CompanyRequest]]:
    async def create_company_request_instance(company_id: int, 
                                            sender_id: Optional[int] = None, 
                                            receiver_id: Optional[int] = None) -> CompanyRequest:
        async with async_session_test() as session:
            new_company_request = CompanyRequest(company_id=company_id, sender_id=sender_id, receiver_id=receiver_id)
            session.add(new_company_request)
            await session.commit()
            return new_company_request
    return create_company_request_instance


@pytest.fixture(scope="function")
async def get_request_by_id(async_session_test: AsyncSession) -> Callable[[int], Awaitable[CompanyRequest]]:
    async def get_request_by_id(request_id: int) -> CompanyRequest:
        async with async_session_test() as session:
            request = await session.execute(select(CompanyRequest).where(CompanyRequest.id == request_id))
            return request.scalar_one_or_none()
    return get_request_by_id
