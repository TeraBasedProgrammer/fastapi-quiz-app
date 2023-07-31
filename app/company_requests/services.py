import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.users.services import error_handler

from .models import CompanyRequest


class CompanyRequestsRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session


    async def send_company_request(self, company_id: int, sender_id: int, receiver_id: int) -> None:
        try:
            new_company_request = CompanyRequest(company_id=company_id, sender_id=sender_id, receiver_id=receiver_id)
            print(new_company_request.__dict__)
            self.db_session.add(new_company_request)
            await self.db_session.commit()
        except IntegrityError:
            raise HTTPException(
                status_code=403, detail=error_handler("You've already sent a company request to this user / company")
            )


    async def cancel_company_request(self, request_id: int) -> None:
        raise NotImplementedError()


    async def accept_company_request(self, request_id: int) -> None:
        raise NotImplementedError()

    
    async def decline_company_request(self, request_id: int) -> None:
        raise NotImplementedError()
    
    async def remove_user_from_company(self, user_id: int, company_id: int) -> None:
        raise NotImplementedError()