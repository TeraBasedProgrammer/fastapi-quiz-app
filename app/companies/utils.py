import logging
from typing import Optional

from starlette import status
from fastapi import HTTPException
from pydantic import EmailStr

from app.companies.models import Company
from app.users.services import error_handler

from .models import Company, RoleEnum

logger = logging.getLogger("main_logger")


async def confirm_company_owner_or_admin(company: Company, current_user_email: EmailStr) -> None:   
    owner_user_authenticated = list(filter(lambda x: x.users.email == current_user_email and (x.role == RoleEnum.Owner or x.role == RoleEnum.Admin), company.users))
    if not owner_user_authenticated:
        logger.warning(f"User {current_user_email} is not a company owner, abort")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))


async def filter_companies_response(response: list[Company]) -> list[Company]:
    return(list(filter(lambda x: x.is_hidden == False, response)))
