from typing import List, Optional

from app.companies.schemas import CompanySchema
from app.users.schemas import UserSchema


class UserFullSchema(UserSchema):
    companies: Optional[List[CompanySchema]] = []
     
    @classmethod
    async def from_model(cls, user_model, public_request=True):
        """
        Wraps raw user data into pydantic-friendly model
        @param user_model: raw user object
        @param public_request: indicates whether hidden
        companies should be included into related company list or not
        """

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
                    is_hidden=company.companies.is_hidden,
                    role=company.role,
                )
                for company in user_model.companies 
                if not company.companies.is_hidden or public_request == False
            ]
        )


class CompanyFullSchema(CompanySchema):
    users: Optional[List[UserSchema]] = []

    @classmethod
    async def from_model(cls, company_model, public_request=True, single_company_request=False):
        """
        Wraps raw company data into pydantic-friendly model
        @param company_model: raw company object
        @param public_request: indicates whether hidden
        companies should be returned or not
        @param user_id: optional int param to validate whether to give access to the hidden company
        (check if user is member of the company or not)
        """

        if company_model.is_hidden and public_request and not single_company_request:
            return []
        
        return cls(
            id=company_model.id,
            title=company_model.title,
            description=company_model.description,
            created_at=company_model.created_at,
            is_hidden=company_model.is_hidden,
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
    