import logging
from typing import List, Optional
from passlib.context import CryptContext

from sqlalchemy import and_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from app.users.models import User
from .schemas import UserSchema, UserUpdateRequest


logger = logging.getLogger("main_logger")


class UserRepository:
    """Data Access Layer for operating user info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


    async def create_user(self, user_data: UserSchema) -> User:
        logger.debug(f"Received new user data: {user_data}")
        new_user = User(
           **user_data.model_dump() 
        )
        new_user.password = self.pwd_context.hash(new_user.password)
        logger.debug(f"Enctypted the password: {new_user.password[:10]}...")
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
            .values(**user_data.model_dump())
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
        logger.debug(f"Successfully deleted user '{result}' from the database")
        return result


def error_handler(message: str):
    return {"error": message}