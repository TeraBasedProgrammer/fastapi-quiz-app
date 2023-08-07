import logging
import re
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from starlette import status

from app.users.schemas import UserBase

logger = logging.getLogger("main_logger")


class UserSignUp(UserBase):
    password: str
    name: Optional[str] = None

    @field_validator("password")
    def validate_password(cls, value):
        if not re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$").match(value):
            logger.warning(f"Validation error: password doesn't match the pattern")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Password should contain at least eight characters, at least one letter and one number")
        return value


class UserSignUpAuth0(UserSignUp):
    auth0_registered: bool


class UserLogin(BaseModel):
    email: EmailStr
    password: str

