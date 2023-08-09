import logging

from pydantic import BaseModel, Field

from app.companies.schemas import CompanySchema
from app.users.schemas import UserSchema

logger = logging.getLogger("main_logger")


class UserInvitationSchema(BaseModel):
    """Pydantic schema for serializing request (invitation) object, received by user"""
    invitation_id: int
    company: CompanySchema

    class Config:
       from_dict = True 

class CompanyInvitationSchema(BaseModel):
    """Pydantic schema for serializing request (invitation) object, sent by company"""
    invitation_id: int
    user: UserSchema

    class Config:
       from_dict = True


class UserRequestSchema(BaseModel):
    """Pydantic schema for serializing request object, sent by user"""
    request_id: int
    company: CompanySchema

    class Config:
       from_dict = True

class CompanyRequestSchema(BaseModel):
    """Pydantic schema for serializing request object, received by company"""
    request_id: int
    user: UserSchema

    class Config:
       from_dict = True 
