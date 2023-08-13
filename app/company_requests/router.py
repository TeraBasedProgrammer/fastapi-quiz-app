import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth.handlers import AuthHandler
from app.companies.models import RoleEnum
from app.companies.services import CompanyRepository
from app.database import get_async_session
from app.users.services import UserRepository, error_handler
from app.utils import get_current_user_id

from .services import CompanyRequestsRepository

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()



request_router = APIRouter(
    prefix="/requests",
    tags=["Company membership requests"],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

invitation_router = APIRouter(
    prefix="/invitations",
    tags=["Company membership invitations"],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)


@invitation_router.post("/{invitation_id}/accept", response_model=Optional[Dict[str, str]])
async def accept_invitation(invitation_id: int,
                            session: AsyncSession = Depends(get_async_session),
                            auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Accepting invitation \"{invitation_id}\"")

    # Initialize services
    request_crud = CompanyRequestsRepository(session)

    # Get invitation
    invitation = await request_crud.get_request_by_id(invitation_id)
    if not invitation:
        logger.warning(f"Company invitation \"{invitation_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Invitation is not found"))
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    if current_user_id != invitation.receiver_id:
        logger.warning(f"Permission error: User \"{current_user_id}\" is not the receiver of the invitation \"{invitation_id}\"")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

    # Accept the invitation 
    await request_crud.accept_company_request(invitation, is_invitation=True)
    logger.info(f"Successfully accepted ivnitation \"{invitation_id}\"")
    return {"response": "Invitation was successfully accepted"}


@invitation_router.delete("/{invitation_id}/cancel", response_model=Optional[Dict[str, str]])
async def cancel_invitation(invitation_id: int,
                            session: AsyncSession = Depends(get_async_session),
                            auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Canceling ivnitation \"{invitation_id}\"")

    # Initialize services repositories
    request_crud = CompanyRequestsRepository(session)
    company_crud = CompanyRepository(session)

    # Get invitation
    invitation = await request_crud.get_request_by_id(invitation_id)
    if not invitation:
        logger.warning(f"Company invitation \"{invitation_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Invitation is not found"))
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Check if user has permission to cancel the invitation
    if not (await company_crud.user_has_role(current_user_id, invitation.company_id, RoleEnum.Admin) or
            await company_crud.user_has_role(current_user_id, invitation.company_id, RoleEnum.Owner)): 
        logger.warning(f"Permission error: User \"{current_user_id}\" doesn't have permission to cancel invitation \"{invitation_id}\"")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

    # Cancel the invitation 
    await request_crud.delete_company_request(invitation_id)
    logger.info(f"Successfully canceled ivnitation {invitation_id}")
    return {"response": "Invitation was successfully canceled"}


@invitation_router.delete("/{invitation_id}/decline", response_model=Optional[Dict[str, str]])
async def decline_invitation(invitation_id: int,
                            session: AsyncSession = Depends(get_async_session),
                            auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Declinng invitation \"{invitation_id}\"")

    # Initialize services 
    request_crud = CompanyRequestsRepository(session)

    # Get invitation
    invitation = await request_crud.get_request_by_id(invitation_id)
    if not invitation:
        logger.warning(f"Company invitation \"{invitation_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Invitation is not found"))
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    if current_user_id != invitation.receiver_id:
        logger.warning(f"Permission error: User \"{current_user_id}\" is not the receiver of the invitation \"{invitation_id}\"")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

    # Decline the invitation 
    await request_crud.delete_company_request(invitation.id)
    logger.info(f"Successfully declined ivnitation \"{invitation_id}\"")
    return {"response": "Invitation was successfully declined"}


@request_router.post("/send/{company_id}", response_model=Optional[Dict[str, str]])
async def request_company_membership(company_id: int,
                                     session: AsyncSession = Depends(get_async_session),
                                     auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Sending membership request to the company \"{company_id}\"")

    # Initialize services 
    request_crud = CompanyRequestsRepository(session)
    company_crud = CompanyRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Validate if requested company exists
    request_company = await company_crud.get_company_by_id(company_id, auth["email"])
    if not request_company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))

    # Validate if user is already a member of the requested company
    if await company_crud.check_user_membership(current_user_id, company_id):
        logger.warning(f"Current user is already a member fo the requested company \"{company_id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("You are already a member of this company"))

    # Validate if user haven't received an invitation from the requested company yet
    if await request_crud.check_existing_request(company_id=company_id, receiver_id=current_user_id):
        logger.warning(f"Permission error: User \"{current_user_id}\" have already received invitation to the company \"{company_id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"You have already received invitation to the company {company_id}"))

    # Send request
    await request_crud.send_company_request(company=request_company, sender_id=current_user_id, receiver_id=None)
    logger.info(f"Successfully sent membership request to the company \"{company_id}\"")
    return {"response": "Membership request was successfully sent"}


@request_router.post("/{request_id}/accept", response_model=Optional[Dict[str, str]])
async def accept_request(request_id: int,
                            session: AsyncSession = Depends(get_async_session),
                            auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Accepting membership request \"{request_id}\"")

    # Initialize services 
    request_crud = CompanyRequestsRepository(session)
    user_crud = UserRepository(session)
    company_crud = CompanyRepository(session)

    # Get request
    request = await request_crud.get_request_by_id(request_id)
    if not request:
        logger.warning(f"Company request \"{request_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Membership request is not found"))
    
    # Check if current CompanyRequest instance is request
    if not request.sender_id:
        logger.warning(f"Company request \"{request_id}\" is not user request")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))
    
    # Retrieving current user id
    current_user = await user_crud.get_user_by_email(auth["email"]) if not auth.get("id") else None
    current_user_id = auth.get("id") if not current_user else current_user.id

    # Check if user has permission to accept the request
    if not (await company_crud.user_has_role(current_user_id, request.company_id, RoleEnum.Admin) or
            await company_crud.user_has_role(current_user_id, request.company_id, RoleEnum.Owner)): 
        logger.warning(f"Permission error: User \"{current_user_id}\" doesn't have permission to accept request \"{request_id}\"")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

    # Accept the invitation 
    await request_crud.accept_company_request(request, is_invitation=False)
    logger.info(f"Successfully accepted membership request \"{request_id}\"")
    return {"response": "Membership request was successfully accepted"}


@request_router.delete("/{request_id}/cancel", response_model=Optional[Dict[str, str]])
async def request_company_membership_cancel(request_id: int,
                                     session: AsyncSession = Depends(get_async_session),
                                     auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:  
    logger.info(f"Cancelling membership request \"{request_id}\"")

    # Initialize services 
    request_crud = CompanyRequestsRepository(session)

    # Get request
    request = await request_crud.get_request_by_id(request_id)
    if not request:
        logger.warning(f"Company request \"{request_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Membership request is not found"))
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    if current_user_id != request.sender_id:
        logger.warning(f"Permission error: User \"{current_user_id}\" is not the sender of the membership request \"{request_id}\"")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

    # Cancel the request
    await request_crud.delete_company_request(request_id)
    logger.info(f"Successfully canceled membership request \"{request_id}\"")
    return {"response": "Membership request was successfully canceled"}


@request_router.delete("/{request_id}/decline", response_model=Optional[Dict[str, str]])
async def decline_request(request_id: int,
                            session: AsyncSession = Depends(get_async_session),
                            auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Declining membership request \"{request_id}\"")

    # Initialize services 
    request_crud = CompanyRequestsRepository(session)
    company_crud = CompanyRepository(session)
    

    # Get request
    request = await request_crud.get_request_by_id(request_id)
    if not request:
        logger.warning(f"Company request \"{request_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Membership request is not found"))
    
    # Check if current CompanyRequest instance is request
    if not request.sender_id:
        logger.warning(f"Company request \"{request_id}\" is not user request")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Validate if user has permission to decline the request
    if not (await company_crud.user_has_role(current_user_id, request.company_id, RoleEnum.Admin) or
            await company_crud.user_has_role(current_user_id, request.company_id, RoleEnum.Owner)): 
        logger.warning(f"Permission error: User \"{current_user_id}\" doesn't have permission to decline request \"{request_id}\"")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

    # Decline the invitation 
    await request_crud.delete_company_request(request.id)
    logger.info(f"Successfully declined membership request \"{request_id}\"")
    return {"response": "Membership request was successfully declined"}
