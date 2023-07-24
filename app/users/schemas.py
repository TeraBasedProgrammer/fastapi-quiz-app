import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, field_validator

logger = logging.getLogger("main_logger")


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str]

    @field_validator("name")
    def validate_user_name(cls, value):
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
    email: Optional[EmailStr] = None        
    password: Optional[str] = None
    
    @field_validator("password")
    def validate_password(cls, value):
        if not re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$").match(value):
            raise HTTPException(
                status_code=400, detail="Password should contain at least eight characters, at least one letter and one number"
            )
        return value

    @field_validator("email")
    def validate_email(cls, value):
        if value is not None:
            raise HTTPException(
                status_code=400, detail="You can't change the email"
            )
        return value


class DeleteUserResponse(BaseModel):
    deleted_user_id: int
