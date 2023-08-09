from sqlalchemy.ext.asyncio import AsyncSession

# Global business logic instance (should be used only to avoid circular imports in other files)

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