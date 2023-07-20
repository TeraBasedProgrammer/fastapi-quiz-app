import logging
from datetime import datetime
from typing import List, Optional
from passlib.context import CryptContext

from sqlalchemy import and_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr
from fastapi import HTTPException

from app.users.models import User
from .schemas import UserSchema, UserUpdateRequest
from app.auth.handlers import AuthHandler
from app.auth.schemas import UserSignUp


logger = logging.getLogger("main_logger")


class UserRepository:
    """Data Access Layer for operating user info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.auth = AuthHandler()


    async def create_user(self, user_data: UserSchema, auth0: bool = False) -> User:
        logger.debug(f"Received new user data: {user_data}")
        new_user = User(
           **user_data.model_dump() 
        )
        print(user_data)
        new_user.password = self.auth.get_password_hash(new_user.password)
        logger.debug(f"Enctypted the password: {new_user.password[:10]}...")
        if auth0:
            new_user.auth0_registered = True
        self.db_session.add(new_user)
        await self.db_session.commit()
        logger.debug(f"Successfully inserted new user instance into the database")
        return new_user


    async def get_users(self) -> List[User]:
        result = await self.db_session.execute(select(User))
        return result.scalars().all()
    

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        logger.debug(f"Received user id: '{user_id}'")
        result = (await self.db_session.execute(
                select(User).where(User.id == user_id))).scalar_one_or_none()
        if result:
            logger.debug(f"Retrieved user by id '{user_id}': {result.email}")
        return result
        

    async def get_user_by_email(self, email: EmailStr) -> Optional[User]:
        logger.debug(f"Received user email: '{email}'")
        result = (await self.db_session.execute(
                select(User).where(User.email == email))).scalar_one_or_none()
        if result:
            logger.debug(f"Retrieved user by email '{email}': '{result.id}'")
        return result


    async def update_user(self, user_id: int, user_data:UserUpdateRequest) -> Optional[UserSchema]:
        logger.debug(f"Received user data: {user_data}")
        query = (
            update(User)
            .where(User.id == user_id)
            .values({key: value for key, value in user_data.model_dump().items() if value is not None})
            .returning(User)
        )
        res = await self.db_session.execute(query)
        await self.db_session.commit()
        logger.debug(f"Successfully updatetd user instance {user_id}")
        return res.scalar_one()


    async def delete_user(self, user_id: int) -> Optional[int]:
        logger.debug(f"Received user id: '{user_id}'")
        query = (
            delete(User)
            .where(User.id == user_id)
            .returning(User.id)
        )

        result = (await self.db_session.execute(query)).scalar_one()
        await self.db_session.commit()
        logger.debug(f"Successfully deleted user '{result}' from the database")
        return result

    async def error_or_create(self, user_email: str) -> None:
        """Verifies that user with provided email wasn't registered using login 
           and password before and creates new one if wasn't"""
        logger.info("Verifying user registration type")
        user_existing_object = await self.get_user_by_email(user_email)
        if not user_existing_object:
            logger.info("User with provided email hasn't been registered yet, creating new instance")
            print(f"pass{datetime.utcnow()}")
            await self.create_user(user_data=UserSignUp(email=user_email, password=f"pass{datetime.now().strftime('%Y%m%d%H%M%S')}", auth0_registered=True))
            return
        if user_existing_object.auth0_registered:
            logger.info("User with provided email has been registered using Auth0, pass")
            return
        if not user_existing_object.auth0_registered:
            logger.error("Error: user with provided email has been registered using logging-password way")
            raise HTTPException(400, detail=error_handler("User with is email has already been registered. Try to register with another email"))


def error_handler(message: str):
    return {"error": message}