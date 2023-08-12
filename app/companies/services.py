import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette import status

from app.utils import create_model_instance, update_model_instance, delete_model_instance
from app.auth.handlers import AuthHandler
from app.companies.models import Company, CompanyUser, RoleEnum
from app.users.models import User
from app.users.services import UserRepository, error_handler

from .schemas import CompanyCreate, CompanyUpdate

logger = logging.getLogger("main_logger")


class CompanyRepository:
    """Data Access Layer for operating company info"""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.auth = AuthHandler()


    async def get_companies(self) -> List[Company]:
        result = await self.db_session.execute(select(Company).options(joinedload(Company.users)))
        return result.unique().scalars().all()
        
    
    async def get_company_by_id(self, company_id: int, current_user_email: EmailStr, owner_only: bool = False, admin_only: bool = False) -> Optional[Company]:
        logger.debug(f"Received data:\ncompany_id -> \"{company_id}\"")
        data = await self.db_session.execute(select(Company).options(joinedload(Company.users)).where(Company.id == company_id))
        company = data.unique().scalar_one_or_none()
        if company:
            logger.debug(f"Retrieved company by id \"{company_id}\": \"{company}\"")

            # Check permissions
            if company.is_hidden:
                member_user = list(filter(lambda x: x.users.email == current_user_email, company.users))
                if not member_user:
                    logger.warning(f"Permission error: User \"{current_user_email}\" is not a member of the company")
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))
            if owner_only:
                owner_user = list(filter(lambda x: x.users.email == current_user_email and x.role == RoleEnum.Owner, company.users))
                if not owner_user:
                    logger.warning(f"Permission error: User \"{current_user_email}\" is not an owner of the company")
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))
            if admin_only:
                admin_user = list(filter(lambda x: x.users.email == current_user_email and (x.role == RoleEnum.Owner or x.role == RoleEnum.Admin), company.users))
                if not admin_user:
                    logger.warning(f"Permission error: User \"{current_user_email}\" is not an admin of the company")
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))
        return company 


    async def get_company_by_title(self, title: str) -> Optional[Company]:
        logger.debug(f"Received data:\n company_title -> \"{title}\"")
        data = await self.db_session.execute(select(Company).options(joinedload(Company.users)).where(Company.title == title))
        company = data.unique().scalar_one_or_none()
        if company:
            logger.debug(f"Retrieved company by name \"{title}\": \"{company}\"")
        return company


    async def create_company(self, company_data: CompanyCreate, current_user_email: EmailStr) -> Dict[str, Any]:
        logger.debug(f"Received data:\nnew company_data -> {company_data}")
        # Initialize new company object
        new_company = await create_model_instance(self.db_session, Company, company_data)
        new_company.users = []

        await self.db_session.commit()

        # Get current user
        crud = UserRepository(self.db_session)
        current_user = await crud.get_user_by_email(current_user_email)

        # Initialize new m2m object for this company and its owner
        company_user = CompanyUser(user_id=current_user.id, company_id=new_company.id, role=RoleEnum.Owner)
        self.db_session.add(company_user)
        await self.db_session.commit()
         
        logger.debug(f"Successfully inserted new company instance with owner \"{current_user_email}\" into the database")
        return {"id": new_company.id, "title": new_company.title}

    async def update_company(self, company_id: int, company_data: CompanyUpdate) -> Optional[Company]:
        logger.debug(f"Received data:\ncompany_data -> {company_data}")
        updated_company = await update_model_instance(self.db_session, Company, company_id, company_data)

        logger.debug(f"Successfully updated company instance \"{company_id}\"")
        return updated_company

    async def delete_company(self, company_id: int) -> Optional[int]:
        logger.debug(f"Received data:\ncompany_id -> \"{company_id}\"")
        result = await delete_model_instance(self.db_session, Company, company_id) 

        logger.debug(f"Successfully deleted company \"{result}\" from the database")
        return result


    async def check_user_membership(self, user_id: int, company_id: int) -> bool:
        logger.debug(f"Received data:\ncompany_id -> {company_id}\nuser_id -> {user_id}")
        result = await self.db_session.execute(select(CompanyUser).where((CompanyUser.company_id == company_id) & (CompanyUser.user_id == user_id)))
        
        data = result.scalar_one_or_none()
        if data:
            logger.debug(f"User {user_id} is a member of the company {company_id}")
            return True
        logger.debug(f"User {user_id} is not a member of the company {company_id}")
        return False
        
 
    async def user_has_role(self, user_id: int, company_id: int, role: RoleEnum) -> bool:
        logger.debug(f"Received data:\ncompany_id -> {company_id}\nuser_id -> {user_id}\nrole -> {role}")
        result = await self.db_session.execute(select(CompanyUser).where((CompanyUser.company_id == company_id) & (CompanyUser.user_id == user_id)))
        
        data = result.scalar_one_or_none()

        # If user is not the mebmer, return false
        if not data:
            return False 

        if data.role == role:
            logger.debug(f"User {user_id} is the {role.value} in the company {company_id}")
            return True
        logger.debug(f"User {user_id} is not the {role.value} in the company {company_id}")      
        return False

    async def get_admins(self, company_id: int) -> List[User]:
        logger.debug(f"Received data:\ncompany_id -> {company_id}")
        result = await self.db_session.execute(select(CompanyUser, User)
                                               .join(User, CompanyUser.user_id == User.id)
                                               .where((CompanyUser.role == RoleEnum.Admin) & (CompanyUser.company_id == company_id))
                                               .reduce_columns(CompanyUser))
        response = result.all()
        logger.debug(f"Successfully retrieved company admins list: {response}")
        return response


    async def set_role(self, company_id: int, user_id: int, role: RoleEnum) -> None:
        logger.debug(f"Received data:\ncompany_id -> {company_id}\nuser_id -> {user_id}")
        query = (
            update(CompanyUser)
            .where((CompanyUser.user_id == user_id) & (CompanyUser.company_id == company_id))
            .values({"role": role})
        )
        res = await self.db_session.execute(query)
        await self.db_session.commit()
        logger.debug(f"Successfully set admin role for user {user_id} in company {company_id}")
         