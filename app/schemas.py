from typing import List, Optional

from .companies.schemas import CompanySchema
from .users.schemas import UserSchema


class UserFullSchema(UserSchema):
    companies: Optional[List[CompanySchema]] = []
     
    @classmethod
    def from_model(cls, user_model):
        return cls(
            id=user_model.id,
            name=user_model.name,
            email=user_model.email,
            registered_at=user_model.registered_at,
            auth0_registered=user_model.auth0_registered,
            companies=[
                CompanySchema(
                    id=company.companies.id,
                    title=company.companies.title,
                    description=company.companies.description,
                    created_at=company.companies.created_at,
                    role=company.role,
                )
                for company in user_model.companies
            ]
        )

    class Config:
        from_attributes = True


class CompanyFullSchema(CompanySchema):
    users: Optional[List[UserSchema]] = []

    @classmethod
    def from_model(cls, company_model):
        return cls(
            id=company_model.id,
            title=company_model.title,
            description=company_model.description,
            created_at=company_model.created_at,
            users=[
                UserSchema(
                    id=user.users.id,
                    name=user.users.name,
                    email=user.users.email,
                    registered_at=user.users.registered_at,
                    auth0_registered=user.users.auth0_registered,
                    role=user.role
                )
                for user in company_model.users
            ]
        )
    