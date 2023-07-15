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


class UserSchema(UserBase):
    id: int
    registered_at: datetime

    class Config:
        from_attributes = True


class SignInRequest(BaseModel):
    email: str
    password: str


class UsersListResponse(BaseModel):
    users: List[UserSchema]


class UserDetailResponse(BaseModel):
    user: UserSchema