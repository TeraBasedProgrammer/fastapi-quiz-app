import logging
import re
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from .models import RoleEnum

logger = logging.getLogger("main_logger")


class CompanyBase(BaseModel):
    title: str
    description: str

    @field_validator("title")
    def validate_company_title(cls, value):
        if len(value) > 100:
            logger.warning(f"Validation error: 'title' field contains too many characters")
        if not re.compile(r"^[a-zA-Z\-. ]+$").match(value):
            logger.warning(f"Validation error: 'title' field contains restricted characters")
            raise HTTPException(
                status_code=400, detail="Title should contain only english letters and special characters (.-)"
            )
            
        return value

class CompanySchema(CompanyBase):
    id: int = Field(alias="company_id")
    created_at: datetime
    role: Optional[RoleEnum] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class CompanyCreate(CompanyBase):
    is_hidden: bool


