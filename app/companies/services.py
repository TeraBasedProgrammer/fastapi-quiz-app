import logging
from typing import Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload

from app.auth.handlers import AuthHandler
from app.companies.models import Company

from .schemas import CompanyCreate, CompanySchema

logger = logging.getLogger("main_logger")


class CompanyRepository:
    """Data Access Layer for operating company info"""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.auth = AuthHandler()


    async def get_companies(self) -> List[Company]:
        result = await self.db_session.execute(select(Company).options(joinedload(Company.users)))
        return result.unique().scalars().all()
    
    
    async def get_company_by_id(self, company_id) -> Optional[Company]:
        logger.debug(f"Received company id: '{company_id}'")
        data = await self.db_session.execute(select(Company).options(joinedload(Company.users)).where(Company.id == company_id))
        result = data.unique().scalar_one_or_none()
        if result:
            logger.debug(f"Retrieved company by id '{company_id}': {result.title}")
        return result 


    async def get_company_by_title(self, title: str) -> Optional[Company]:
        logger.debug(f"Received company name: '{title}'")
        data = await self.db_session.execute(select(Company).options(joinedload(Company.users)).where(Company.title == title))
        result = data.unique().scalar_one_or_none()
        if result:
            logger.debug(f"Retrieved company by name '{title}': '{result.id}'")
        return result


    async def create_company(self, company_data: CompanyCreate) -> Company:
        logger.debug(f"Received new company data: {company_data}")
        new_company = Company(
           **company_data.model_dump() 
        )
        new_company.users = []
        self.db_session.add(new_company)
        await self.db_session.commit()
        logger.debug(f"Successfully inserted new company instance into the database")
        return new_company
