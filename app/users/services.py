from typing import List, Union
from passlib.context import CryptContext

from sqlalchemy import and_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from app.users.models import User
from .schemas import UserSchema, UserUpdateRequest


class UserRepository:
    """Data Access Layer for operating user info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


    async def create_user(self, user_data: UserSchema) -> User:
        new_user = User(
           **user_data.model_dump() 
        )
        new_user.password = self.pwd_context.hash(new_user.password)
        self.db_session.add(new_user)
        await self.db_session.commit()
        return new_user

    async def get_users(self) -> List[User]:
        result = await self.db_session.execute(select(User))
        return result.scalars().all()
    

    async def get_user_by_id(self, user_id: int) -> Union[User, None]:
        return (await self.db_session.execute(
                select(User).where(User.id == user_id))).scalar_one_or_none()
        

    async def get_user_by_email(self, email: EmailStr) -> Union[User, None]:
        return (await self.db_session.execute(
                select(User).where(User.email == email))).scalar_one_or_none()


    async def update_user(self, user_id: int, user_data:UserUpdateRequest) -> Union[UserSchema, None]:
        query = (
            update(User)
            .where(User.id == user_id)
            .values(**user_data.model_dump())
            .returning(User)
        )
        res = await self.db_session.execute(query)
        await self.db_session.commit()
        return res.scalar_one()


    async def delete_user(self, user_id: int) -> Union[int, None]:
        query = (
            delete(User)
            .where(User.id == user_id)
            .returning(User.id)
        )
        return (await self.db_session.execute(query)).scalar_one()