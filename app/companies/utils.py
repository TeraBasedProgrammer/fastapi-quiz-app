import logging

from pydantic import EmailStr
from fastapi import HTTPException

from app.companies.models import Company
from app.users.services import error_handler


logger = logging.getLogger("main_logger")


async def confirm_company_owner(company: Company, current_user_email: EmailStr) -> None:
    owner_user_authenticated = list(filter(lambda x: x.users.email == current_user_email, company.users))
    if not owner_user_authenticated:
        logger.warning(f"User {current_user_email} is not a company owner, abort")
        raise HTTPException(403, detail=error_handler("Forbidden"))