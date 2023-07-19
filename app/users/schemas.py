import re
import logging

from fastapi import HTTPException
from datetime import datetime
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import constr
from pydantic import validator
from typing import List, Optional, TypeVar, Generic


logger = logging.getLogger("main_logger")

T = TypeVar('T')


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str]

    @validator("name")
    def validate_name(cls, value):
        if not re.compile(r"^[a-zA-Z\- ]+$").match(value):
            logger.warning(f"Validation error: 'name' field contains restricted characters")
            raise HTTPException(
                status_code=400, detail="Name should contain only english letters"
            )
        return value


class UserSchema(UserBase):
    id: int
    registered_at: datetime

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str

    @validator("password")
    def validate_password(cls, value):
        if not re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$").match(value):
            logger.warning(f"Validation error: password doesn't match the pattern")
            raise HTTPException(
                status_code=400, detail="Password should contain at least eight characters, at least one letter and one number"
            )
        return value


class UserUpdateRequest(UserBase):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

    @validator("password")
    def validate_name(cls, value):
        if not re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$").match(value):
            raise HTTPException(
                status_code=400, detail="Password should contain at least eight characters, at least one letter and one number"
            )
        return value


class UserLogin(BaseModel):
    email: str
    password: str


class DeleteUserResponse(BaseModel):
    deleted_user_id: int
