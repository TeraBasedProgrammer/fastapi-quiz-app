import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette import status

from app.auth.handlers import AuthHandler
from app.auth.schemas import UserSignUp, UserSignUpAuth0
from app.companies.models import CompanyUser, Company
from app.quizzes.models import Quiz
from app.quizzes_workflow.models import Attemp
from app.users.models import User
from app.utils import (create_model_instance, delete_model_instance,
                       update_model_instance)

from .schemas import UserSchema, UserUpdateRequest, UpdateUserScore

logger = logging.getLogger("main_logger")


class UserRepository:
    """Data Access Layer for operating user info"""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.auth = AuthHandler()


    async def create_user(self, user_data: UserSignUp, auth0: bool = False) -> Dict[str, Any]:
        logger.debug(f"Received data:\nnew_user_data -> {user_data}")
        new_user = await create_model_instance(self.db_session, User, user_data)

        new_user.password = await self.auth.get_password_hash(new_user.password)
        new_user.companies = []
        logger.debug(f"Enctypted the password: \"{new_user.password[:10]}...\"")

        if auth0:
            new_user.auth0_registered = True

        await self.db_session.commit()
        logger.debug(f"Successfully inserted new user instance into the database")
        return {"id": new_user.id, "email": new_user.email}


    async def get_users(self) -> List[User]:
        result = await self.db_session.execute(select(User).options(joinedload(User.companies)))
        return result.unique().scalars().all()
    

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        logger.debug(f"Received data:\nuser_id -> \"{user_id}\"")
        data = await self.db_session.execute(select(User).options(joinedload(User.companies)).where(User.id == user_id))
        result = data.unique().scalar_one_or_none()
        if result:
            logger.debug(f"Retrieved user by id \"{user_id}\": \"{result.email}\"")
        return result
        

    async def get_user_by_email(self, email: EmailStr) -> Optional[User]:
        logger.debug(f"Received data:\nuser_email -> \"{email}\"")
        data = await self.db_session.execute(select(User).options(joinedload(User.companies)).where(User.email == email))
        result = data.unique().scalar_one_or_none()
        if result:
            logger.debug(f"Retrieved user by email \"{email}\": \"{result.id}\"")
        return result

    async def update_user(self, user_id: int, user_data:UserUpdateRequest) -> Optional[UserSchema]:
        logger.debug(f"Received data:\nuser_data -> {user_data}")
        updated_user = await update_model_instance(self.db_session, User, user_id, user_data)
        
        logger.debug(f"Successfully updatetd user instance \"{user_id}\"")
        return updated_user


    async def delete_user(self, user_id: int) -> Optional[int]:
        logger.debug(f"Received data:\nuser_id -> \"{user_id}\"")
        result = await delete_model_instance(self.db_session, User, user_id)

        logger.debug(f"Successfully deleted user \"{result}\" from the database")
        return result


    async def error_or_create(self, user_email: str) -> None:
        """Verifies that user with provided email wasn't registered using login 
           and password before and creates new one if wasn't"""
        logger.info("Verifying user registration type")
        user_existing_object = await self.get_user_by_email(user_email)
        if not user_existing_object:
            logger.info("User with provided email hasn't been registered yet, creating new instance")
            new_user = await self.create_user(user_data=UserSignUpAuth0(email=user_email, password=f"pass{datetime.now().strftime('%Y%m%d%H%M%S')}", auth0_registered=True))
            return new_user
        if user_existing_object.auth0_registered:
            logger.info("User with provided email has been registered using Auth0, pass")
            return
        if not user_existing_object.auth0_registered:
            logger.warning("Error: user with provided email has been registered using logging-password way")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("User with is email has already been registered. Try to register with another email"))

    async def set_global_score(self, user_id: int) -> None:
        logger.debug(f"Received data:\nuser_id -> \"{user_id}\"")
        query = await self.db_session.execute(
            select(Attemp)
            .where(Attemp.user_id == user_id)
        )
        attemps = query.scalars().unique().all() 
        questions_count = sum([attemp.quiz.questions_count for attemp in attemps])
        results_count = sum([attemp.result for attemp in attemps])

        avg_score = results_count / questions_count
        await update_model_instance(
            self.db_session, 
            User, 
            user_id, 
            UpdateUserScore(overall_avg_score=avg_score)
        )

    async def set_company_score(
        self, 
        user_id: int, 
        company_id: int
    ) -> None:
        logger.debug(f"Received data:\nuser_id -> \"{user_id}\"")
        query = await self.db_session.execute(
            select(Attemp)
            .where(
                (Attemp.user_id == user_id) &
                (Attemp.quiz_id == Quiz.id) &
                (Company.id == Quiz.company_id)
            )
        )
        attemps = query.scalars().unique().all() 
        questions_count = sum([attemp.quiz.questions_count for attemp in attemps])
        results_count = sum([attemp.result for attemp in attemps])

        avg_score = results_count / questions_count

        # Update CompanyUser instance
        query = (
            update(CompanyUser)
            .where((CompanyUser.user_id == user_id)
                    & (CompanyUser.company_id == company_id))
            .values({"average_score": avg_score})
        )
        await self.db_session.execute(query)
        await self.db_session.commit()
        

def error_handler(message: str) -> Dict[str, str]:
    return {"error": message}