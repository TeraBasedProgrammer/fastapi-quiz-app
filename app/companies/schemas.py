import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from starlette import status

from .models import RoleEnum

logger = logging.getLogger("main_logger")


class CompanyBase(BaseModel):
    title: str = Field(max_length=100)
    description: str

    @field_validator("title")
    def validate_company_title(cls, value):
        if not re.compile(r"^[a-zA-Z0-9\-. ]+$").match(value):
            logger.warning(f"Validation error: 'title' field contains restricted characters")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Title may contain only english letters, numbers and special characters ('.', '-', ' ')"
            )
            
        return value

class CompanySchema(CompanyBase):
    id: int 
    created_at: datetime
    role: Optional[RoleEnum] = Field(None, nullable=True)
    is_hidden: bool
    
    class Config:
        from_attributes = True
        populate_by_name = True


class CompanyCreate(CompanyBase):
    is_hidden: bool


class CompanyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_hidden: Optional[bool] = None
    