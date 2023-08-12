from sqlalchemy.ext.asyncio import AsyncSession


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