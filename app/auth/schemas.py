import re
import logging

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import validator

from app.users.schemas import UserBase

logger = logging.getLogger("main_logger")


class UserSignUp(UserBase):
    password: str

    @validator("password")
    def validate_password(cls, value):
        if not re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$").match(value):
            logger.warning(f"Validation error: password doesn't match the pattern")
            raise HTTPException(
                status_code=400, detail="Password should contain at least eight characters, at least one letter and one number"
            )
        return value


class UserLogin(BaseModel):
    email: str
    password: str

