import logging
from typing import Any, Dict, List, Optional

from pydantic import EmailStr
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth.handlers import AuthHandler
from app.companies.models import Company, CompanyUser, RoleEnum
from app.users.services import UserRepository

from .schemas import CompanyCreate, CompanyUpdate
from .utils import confirm_company_owner

logger = logging.getLogger("main_logger")


class CompanyRepository:
    """Data Access Layer for operating company info"""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.auth = AuthHandler()


    async def get_companies(self) -> List[Company]:
        result = await self.db_session.execute(select(Company).options(joinedload(Company.users)))
        return result.unique().scalars().all()
        
    
    async def get_company_by_id(self, company_id: int, current_user_email: EmailStr, validation_required: bool = False) -> Optional[Company]:
        logger.debug(f"Received company id: '{company_id}'")
        data = await self.db_session.execute(select(Company).options(joinedload(Company.users)).where(Company.id == company_id))
        result = data.unique().scalar_one_or_none()
        if result:
            logger.debug(f"Retrieved company by id '{company_id}': {result.title}")

            # Check permissions (validate if user is the owner of retrieved company)
            if result.is_hidden or validation_required:
                await confirm_company_owner(result, current_user_email)

        return result 


    async def get_company_by_title(self, title: str) -> Optional[Company]:
        logger.debug(f"Received company name: '{title}'")
        data = await self.db_session.execute(select(Company).options(joinedload(Company.users)).where(Company.title == title))
        result = data.unique().scalar_one_or_none()
        if result:
            logger.debug(f"Retrieved company by name '{title}': '{result.id}'")
        return result


    async def create_company(self, company_data: CompanyCreate, current_user_email: EmailStr) -> Dict[str, Any]:
        logger.debug(f"Received new company data: {company_data}")
        # Initialize new company object
        new_company = Company(
           **company_data.model_dump() 
        )
        new_company.users = []

        # Insert new company object into the db
        self.db_session.add(new_company)
        await self.db_session.commit()

        # Get current user
        crud = UserRepository(self.db_session)
        current_user = await crud.get_user_by_email(current_user_email)

        # Initialize new m2m object for this company and its owner
        company_user = CompanyUser(user_id=current_user.id, company_id=new_company.id, role=RoleEnum.Owner)
        self.db_session.add(company_user)
        await self.db_session.commit()
         
        logger.debug(f"Successfully inserted new company instance with owner '{current_user_email}' into the database")
        return {"id": new_company.id, "title": new_company.title}

    async def update_company(self, company_id: int, company_data: CompanyUpdate) -> Optional[Company]:
        logger.debug(f"Received company data: {company_data}")
        query = (
            update(Company)
            .where(Company.id == company_id)
            .values({key: value for key, value in company_data.model_dump().items() if value is not None})
            .returning(Company)
        )
        res = await self.db_session.execute(query)
        await self.db_session.commit()
        logger.debug(f"Successfully updatetd company instance {company_id}")
        return res.scalar_one()


    async def delete_company(self, company_id: int) -> Optional[int]:
        logger.debug(f"Received company id: '{company_id}'")
        query = (
            delete(Company)
            .where(Company.id == company_id)
            .returning(Company.id)
        )

        result = (await self.db_session.execute(query)).scalar_one()
        await self.db_session.commit()
        logger.debug(f"Successfully deleted company '{result}' from the database")
        return result


    async def check_user_membership(self, user_id: int, company_id: int) -> Optional[bool]:
        logger.debug(f"Received data:\ncompany_id -> {company_id}\nuser_id -> {user_id}")
        result = await self.db_session.execute(select(CompanyUser).where((CompanyUser.company_id == company_id) & (CompanyUser.user_id == user_id)))
        
        data = result.scalar_one_or_none()
        if data:
            logger.debug(f"User {user_id} is a member of the company {company_id}")
            return True
        logger.debug(f"User {user_id} is not a member of the company {company_id}")
        

    async def user_is_owner(self, user_id: int, company_id: int) -> Optional[bool]:
        logger.debug(f"Received data:\ncompany_id -> {company_id}\nuser_id -> {user_id}")
        result = await self.db_session.execute(select(CompanyUser).where((CompanyUser.company_id == company_id) & (CompanyUser.user_id == user_id)))
        
        data = result.scalar_one_or_none()
        if data.role == RoleEnum.Owner:
            logger.debug(f"User {user_id} is the owner of the company {company_id}")
            return True
        logger.debug(f"User {user_id} is not the owner of the company {company_id}")