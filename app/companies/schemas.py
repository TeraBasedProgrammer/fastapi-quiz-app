import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.utils import validate_text

from .models import RoleEnum

logger = logging.getLogger("main_logger")


class CompanyBase(BaseModel):
    title: str = Field(max_length=100)
    description: str

    @field_validator("title")
    def validate_company_title(cls, value):
        return validate_text(value)
    
    
class CompanySchema(CompanyBase):
    id: int 
    created_at: datetime
    role: Optional[RoleEnum] = Field(None, nullable=True)
    average_score: Optional[Decimal] = Field(None, nullable=True)
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
    