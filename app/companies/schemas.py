import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, field_validator

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
    id: int
    created_at: datetime


class CompanyCreate(CompanyBase):
    is_hidden: bool


