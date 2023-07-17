from datetime import datetime
from pydantic import BaseModel

from pydantic import BaseModel
from typing import List


class UserBase(BaseModel):
    email: str
    username: str


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    password: str = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserSchema(UserBase):
    id: int
    registered_at: datetime

    class Config:
        from_attributes = True


class UsersListResponse(BaseModel):
    users: List[UserSchema]