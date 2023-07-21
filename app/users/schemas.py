import re
import logging

from fastapi import HTTPException
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic import EmailStr
from pydantic import validator
from typing import Optional


logger = logging.getLogger("main_logger")


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str]

    @validator("name")
    def validate_name(cls, value):
        if not value: 
            return value
        if not re.compile(r"^[a-zA-Z\- ]+$").match(value):
            logger.warning(f"Validation error: 'name' field contains restricted characters")
            raise HTTPException(
                status_code=400, detail="Name should contain only english letters"
            )
        return value


class UserSchema(UserBase):
    id: int
    registered_at: datetime
    auth0_registered: Optional[bool] 

    class Config:
        from_attributes = True


class UserUpdateRequest(UserBase):
    name: Optional[str] = None
    email: Optional[EmailStr] = None        # if value is not None:
        #     raise HTTPException(
        #         status_code=400, detail="You can't change the email"
        #     )
    password: Optional[str] = None
    
    @validator("password")
    def validate_name(cls, value):
        if not re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$").match(value):
            raise HTTPException(
                status_code=400, detail="Password should contain at least eight characters, at least one letter and one number"
            )
        return value

    @validator("email")
    def validate_name(cls, value):
        if value is not None:
            raise HTTPException(
                status_code=400, detail="You can't change the email"
            )
        return value


class DeleteUserResponse(BaseModel):
    deleted_user_id: int
