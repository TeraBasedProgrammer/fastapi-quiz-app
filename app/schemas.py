from typing import List

from .companies.schemas import CompanySchema
from .users.schemas import UserSchema


class UserFullSchema(UserSchema):
    companies: List[CompanySchema] | None = None

    class Config:
        from_attributes = True
        populate_by_name = True


class CompanyFullSchema(CompanySchema):
    users: List[UserSchema] | None  = None

    class Config:
        from_attributes = True
        populate_by_name = True

