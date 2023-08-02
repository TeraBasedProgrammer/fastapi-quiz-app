import logging
from typing import Dict, List, Optional

from starlette import status
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.companies.models import Company, CompanyUser, RoleEnum
from app.users.models import User
from app.users.services import error_handler

from .models import CompanyRequest

logger = logging.getLogger("main_logger")


class CompanyRequestsRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session


    async def _get_company_onwer_id(self, company_id: int) -> int:
        owner_id_request = await self.db_session.execute(select(CompanyUser.user_id)
                                                 .where((CompanyUser.company_id == company_id) 
                                                        & (CompanyUser.role == RoleEnum.Owner)))
        owner_id = owner_id_request.first()[0]
        logger.debug(f"Retrieved owner id of the company {company_id}: {owner_id}")
        return owner_id


    async def send_company_request(self, company: Company, sender_id: int, receiver_id: int) -> None:
        try:
            if not receiver_id:
                receiver_id = await self._get_company_onwer_id(company.id)
            new_company_request = CompanyRequest(company_id=company.id, sender_id=sender_id, receiver_id=receiver_id)
            self.db_session.add(new_company_request)
            await self.db_session.commit()
        except IntegrityError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("You've already sent a request to this user / company"))


    async def delete_company_request(self, request_id: int) -> None:
        query = (
            delete(CompanyRequest)
            .where(CompanyRequest.id == request_id)
        )

        await self.db_session.execute(query)
        await self.db_session.commit()
        logger.debug(f"Successfully deleted company request '{request_id}' from the database")


    async def accept_company_request(self, request: CompanyRequest, is_invitation: bool) -> None:
        user_id_to_add = request.receiver_id if is_invitation else request.sender_id

        # Add user to the company
        company_user = CompanyUser(user_id=user_id_to_add, company_id=request.company_id, role=RoleEnum.Member)
        self.db_session.add(company_user)
        await self.db_session.commit()
        logger.debug(f"Successfully added user {user_id_to_add} to the company {request.company_id}")

        # Delete accepted request
        await self.delete_company_request(request.id)

 
    async def remove_user_from_company(self, company_id: int, user_id: int) -> None:
        await self.db_session.execute(
            delete(CompanyUser)
            .where((CompanyUser.company_id == company_id) 
                   & (CompanyUser.user_id == user_id)))
        
        await self.db_session.commit()
        logger.debug(f"Successfully removed user {user_id} from the company {company_id}")


    async def get_request_by_id(self, request_id: int) -> Optional[CompanyRequest]:
        result = await self.db_session.execute(select(CompanyRequest).where(CompanyRequest.id == request_id))
        return result.scalar_one_or_none()


    async def get_received_requests(self, receiver_id: int, 
                                    for_company: bool) -> List[Optional[Dict[int, Company]]] | List[Optional[Dict[int, User]]]:
        logger.debug(f"Received data:\nreceiver_id -> {receiver_id}\nfor_company -> {for_company}")

        subquery = select(CompanyUser.company_id).where(CompanyUser.user_id == receiver_id)
        if for_company:
            # Requests received by company from user
            query = await self.db_session.execute(select(CompanyRequest.id, User)
                .join(User, CompanyRequest.sender_id == User.id)
                .where((CompanyRequest.receiver_id == receiver_id) & (CompanyRequest.company_id.in_(subquery))))

            response_data = [{'request_id': item[0], 'user': item[1]} for item in query.all()]
            logger.debug(f"Successfully retrieved company requests: {response_data}")
            return response_data
        else:
            # Invitation received by user from company
            query = await self.db_session.execute(select(CompanyRequest.id, CompanyRequest.sender_id, Company)
                .join(Company, CompanyRequest.company_id == Company.id)
                .where((CompanyRequest.receiver_id == receiver_id) & (CompanyRequest.company_id.notin_(subquery))))
            
            response_data = [{'invitation_id': item[0], 'sender_id': item[1], 'company': item[2]} for item in query.all()]
            logger.debug(f"Successfully retrieved user invitations: {response_data}")
            return response_data

    async def get_sent_requests(self, sender_id: int, 
                                for_company: bool)  -> List[Optional[Dict[int, Company]]] | List[Optional[Dict[int, User]]]:
        logger.debug(f"Received data:\nsender_id -> {sender_id}\nfor_company -> {for_company}")
        subquery = select(CompanyUser.company_id).where(CompanyUser.user_id == sender_id)
        # Invitations sent by company 
        if for_company:
            query = await self.db_session.execute(select(CompanyRequest.id, User)
                .join(User, CompanyRequest.receiver_id == User.id)
                .where((CompanyRequest.sender_id == sender_id) & (CompanyRequest.company_id.in_(subquery))))

            response_data = [{'invitation_id': item[0], 'user': item[1]} for item in query.all()]
            logger.debug(f"Successfully retrieved company invitations: {response_data}")
            return response_data
        else:
            # Requests sent by user
            query = await self.db_session.execute(select(CompanyRequest.id, Company)
                .join(Company, CompanyRequest.company_id == Company.id)
                .where((CompanyRequest.sender_id == sender_id) & (CompanyRequest.company_id.notin_(subquery))))
            
            response_data = [{'request_id': item[0], 'company': item[1]} for item in query.all()]
            logger.debug(f"Successfully retrieved user requests: {response_data}")
            return response_data