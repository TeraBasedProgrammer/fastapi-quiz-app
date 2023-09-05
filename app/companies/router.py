import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, Params, paginate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth.handlers import AuthHandler
from app.company_requests.schemas import (CompanyInvitationSchema,
                                          CompanyRequestSchema)
from app.company_requests.services import CompanyRequestsRepository
from app.database import get_async_session
from app.quizzes.schemas import QuizSchema
from app.quizzes.services import QuizRepository
from app.schemas import CompanyFullSchema
from app.users.schemas import DeletedInstanceResponse, UserSchema
from app.users.services import UserRepository, error_handler
from app.utils import get_current_user_id

from .models import RoleEnum
from .schemas import CompanyCreate, CompanyUpdate
from .services import CompanyRepository
from .utils import filter_companies_response

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

company_router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
    responses={404: {"description": "Not found"}}
)


@company_router.get("/", response_model=Page[CompanyFullSchema], response_model_exclude_none=True)
async def get_all_companies(session: AsyncSession = Depends(get_async_session),
                    params: Params = Depends(),
                    auth=Depends(auth_handler.auth_wrapper)) -> Page[CompanyFullSchema]:
    logger.info("Getting all companies from the database")
    company_crud = CompanyRepository(session)
    result = await company_crud.get_companies() 
    logger.info("All companies have been successfully retrieved")

    response = [await CompanyFullSchema.from_model(c) for c in await filter_companies_response(result)]
    return paginate(response, params)


@company_router.get("/{company_id}/", response_model=Optional[CompanyFullSchema], response_model_exclude_none=True)
async def get_company(company_id: int, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[CompanyFullSchema]:
    logger.info(f"Retrieving Company instance by id \"{company_id}\"")

    # Intialize services
    company_crud = CompanyRepository(session)

    company = await company_crud.get_company_by_id(company_id, auth["email"])
    if not company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, error_handler("Company is not found"))

    logger.info(f"Successfully retrieved Company instance \"{company}\"")
    return await CompanyFullSchema.from_model(company, single_company_request=True)


@company_router.get("/{company_id}/quizzes/", response_model=Page[QuizSchema])
async def get_quizzes(company_id: int,
                      params: Params = Depends(),
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Page[QuizSchema]:
    # Initialize services
    quiz_crud = QuizRepository(session)
    company_crud = CompanyRepository(session)

    # Validate if requested instances exist
    request_company = await company_crud.get_company_by_id(company_id, auth["email"], admin_only=True)
    if not request_company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))

    return paginate(await quiz_crud.get_company_quizzes(company_id=company_id), params)


@company_router.get("/{company_id}/requests/", response_model=Optional[List[CompanyRequestSchema]], response_model_exclude_none=True)
async def get_received_requests(company_id: int, 
                       session: AsyncSession = Depends(get_async_session),
                       auth=Depends(auth_handler.auth_wrapper)) -> Optional[List[CompanyRequestSchema]]:
    logger.info(f"Retrieving requests list of the company \"{company_id}\"")

    # Initialize services
    request_crud = CompanyRequestsRepository(session)
    company_crud = CompanyRepository(session)
    
    company = await company_crud.get_company_by_id(company_id, auth["email"], admin_only=True)
    if not company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))

    res = await request_crud.get_received_requests(company_id=company.id)
    logger.info(f"Successfully retrieved requests list of the company \"{company}\"")
    return res


@company_router.get("/{company_id}/invitations/", response_model=Optional[List[CompanyInvitationSchema]], response_model_exclude_none=True)
async def get_sent_invitations(company_id: int, 
                       session: AsyncSession = Depends(get_async_session),
                       auth=Depends(auth_handler.auth_wrapper)) -> Optional[List[CompanyInvitationSchema]]:
    logger.info(f"Retrieving sent invitations list of the company \"{company_id}\"")
    
    # Initialize services
    request_crud = CompanyRequestsRepository(session)
    company_crud = CompanyRepository(session)
    
    company = await company_crud.get_company_by_id(company_id, auth["email"], admin_only=True)
    if not company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))

    res = await request_crud.get_sent_requests(company_id=company.id)
    logger.info(f"Successfully retrieved sent invitations list of the company \"{company}\"")
    return res


@company_router.get("/{company_id}/admins/", response_model=List[UserSchema], response_model_exclude_none=True)
async def get_company_admin_list(company_id: int,
                                 session: AsyncSession = Depends(get_async_session),
                                 auth=Depends(auth_handler.auth_wrapper)) -> List[UserSchema]:
    logger.info(f"Retrieving company admins list of the company \"{company_id}\"")

    # Initialize services
    company_crud = CompanyRepository(session)

    request_company = await company_crud.get_company_by_id(company_id, auth["email"], admin_only=True)
    if not request_company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))
    
    admins = await company_crud.get_admins(company_id=company_id)
    logger.info(f"Successfully retreived company admins list of the company \"{request_company}\"")
    return admins


@company_router.post("/", response_model=Optional[Dict[str, Any]], status_code=201, response_model_exclude_none=True)
async def create_company(company: CompanyCreate, 
                         session: AsyncSession = Depends(get_async_session),
                         auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Creating new Company instance")
    company_crud = CompanyRepository(session)
    company_existing_object = await company_crud.get_company_by_title(company.title)
    if company_existing_object: 
        logger.warning(f"Validation error: Company with name \"{company.title}\" already exists")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("Company with this name already exists"))
    result = await company_crud.create_company(company, auth['email'])
    logger.info(f"New company instance has been successfully created")
    return result


@company_router.post("/{company_id}/invite/{user_id}/", 
                     response_model=Optional[Dict[str, str]],
                     status_code=status.HTTP_201_CREATED)
async def invite_user(company_id: int, 
                      user_id: int,
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Inviting user \"{user_id}\" to the company \"{company_id}\"")

    # Initialize services 
    request_crud = CompanyRequestsRepository(session)
    company_crud = CompanyRepository(session)
    user_crud = UserRepository(session)

    # Validate if requested instances exist
    request_company = await company_crud.get_company_by_id(company_id, auth["email"], admin_only=True)
    if not request_company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))
    
    request_user = await user_crud.get_user_by_id(user_id)
    if not request_user:
        logger.warning(f"User \"{user_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested user is not found"))
 
    # Validate if user is already a member of the requested company
    if await company_crud.check_user_membership(user_id, company_id):
        logger.warning(f"Requested user \"{request_user}\" is already a member for the requested company \"{request_company}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("Requested user is already a member of the company"))

    # Validate if company haven't received a request from the requested user yet
    if await request_crud.check_existing_request(company_id=company_id, sender_id=user_id):
        logger.warning(f"Permission error: User \"{user_id}\" have already sent a request to the company \"{company_id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"User {user_id} have already sent a request to the company {company_id}"))
    
    # Send invitation
    await request_crud.send_company_request(company=request_company, sender_id=None, receiver_id=user_id)
    logger.info(f"Successfully invited user \"{request_user}\" to the company \"{request_company}\"")
    return {"response": "Invitation was successfully sent"}


@company_router.post("/{company_id}/set-admin/{user_id}/", response_model=Optional[Dict[str, Any]])
async def give_admin_role(company_id: int, 
                          user_id: int,
                          session: AsyncSession = Depends(get_async_session),
                          auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, Any]]:
    logger.info(f"Setting the admin role for the user \"{user_id}\" in the company \"{company_id}\"")

    # Initialize services 
    user_crud = UserRepository(session)
    company_crud = CompanyRepository(session)

    company = await company_crud.get_company_by_id(company_id, auth["email"], owner_only=True)
    if not company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Check if requested user is not yourself
    if user_id == current_user_id:
        logger.warning(f"Validation error: User \"{current_user_id}\" requested itself")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("You can't change your own role"))

    request_user = await user_crud.get_user_by_id(user_id)
    if not request_user:
        logger.warning(f"User \"{user_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested user is not found"))
    
    # Check if requested user is the member of the company
    if not await company_crud.check_user_membership(user_id, company_id):
        logger.warning(f"User \"{request_user}\" is not the member of the company \"{company}\"") 
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"User {request_user.email} is not the member of the company {company.title}"))

    # Check if user isn't already an admin
    if await company_crud.user_has_role(user_id=user_id, company_id=company_id, role=RoleEnum.Admin):
        logger.warning(f"User \"{request_user}\" is already an admin in the company \"{company}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"User {request_user.email} is already an admin in the company {company.title}"))
    
    # Set admin
    await company_crud.set_role(user_id=user_id, company_id=company_id, role=RoleEnum.Admin)
    logger.info(f"User \"{user_id}\" was successfuly assigned as admin")
    
    return {"response": f"User {request_user.email} was successfuly assigned as admin"}
    

@company_router.post("/{company_id}/unset-admin/{user_id}/", response_model=Optional[Dict[str, str]])
async def take_admin_role(company_id: int, 
                          user_id: int,
                          session: AsyncSession = Depends(get_async_session),
                          auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Unsetting the admin role for the user \"{user_id}\" in the company \"{company_id}\"")

    # Initialize services 
    user_crud = UserRepository(session)
    company_crud = CompanyRepository(session)

    company = await company_crud.get_company_by_id(company_id, auth["email"], owner_only=True)
    if not company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Check if requested user is not yourself
    if current_user_id == user_id:
        logger.warning(f"Validation error: User \"{current_user_id}\" requested itself")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("You can't change your own role"))

    request_user = await user_crud.get_user_by_id(user_id)
    if not request_user:
        logger.warning(f"User \"{user_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested user is not found"))
    
    # Check if requested user is the member of the company
    if not await company_crud.check_user_membership(user_id, company_id):
        logger.warning(f"User \"{request_user}\" is not the member of the company \"{company}\"") 
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"User {request_user.email} is not the member of the company {company.title}"))

    # Check if user is an admin
    if not await company_crud.user_has_role(user_id=user_id, company_id=company_id, role=RoleEnum.Admin):
        logger.warning(f"User \"{request_user}\" is not an admin in the company \"{company}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"User {request_user.email} is not an admin in the company {company.title}"))
    
    # Set admin
    await company_crud.set_role(user_id=user_id, company_id=company_id, role=RoleEnum.Member)
    logger.info(f"The admin role has been taken away from the user \"{request_user.email}\"")
    
    return {"response": f"The admin role has been taken away from the user {request_user.email}"}

@company_router.patch("/{company_id}/update/", response_model=Optional[CompanyFullSchema], response_model_exclude_none=True)
async def update_company(company_id: int, body: CompanyUpdate, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[CompanyFullSchema]:
    logger.info(f"Updating Company instance \"{company_id}\"")
    company_crud = CompanyRepository(session)
    updated_user_params = body.model_dump(exclude_none=True)
    if updated_user_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("At least one valid parameter (title, description, is_hidden) should be provided for user update query"))
    try: 
        company_for_update = await company_crud.get_company_by_id(company_id, auth["email"], owner_only=True)
        if not company_for_update:
            logger.warning(f"Company \"{company_id}\" is not found")
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Company is not found"))
         
        logger.info(f"Company \"{company_for_update}\" have been successfully updated")
        return await CompanyFullSchema.from_model(await company_crud.update_company(company_id, body))
    except IntegrityError:
        logger.warning(f"Validation error: Company with provided title already exists")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("Company with this title already exists"))


@company_router.delete("/{company_id}/delete/", response_model=Optional[DeletedInstanceResponse], response_model_exclude_none=True)
async def delete_company(company_id: int, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    logger.info(f"Deleting Company instance \"{company_id}\"")
    company_crud = CompanyRepository(session)

    # Check if company exists
    company_for_deletion = await company_crud.get_company_by_id(company_id, auth["email"], owner_only=True)
    if not company_for_deletion:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Company is not found"))
    
    deleted_company_id = await company_crud.delete_company(company_id)
    logger.info(f"Company \"{company_id}\" has been successfully deleted from the database")
    return DeletedInstanceResponse(deleted_instance_id=deleted_company_id)


@company_router.delete("/{company_id}/kick/{user_id}/", response_model=Optional[Dict[str, str]])
async def kick_user(company_id: int,
                    user_id: int,
                    session: AsyncSession = Depends(get_async_session),
                    auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Kicking user \"{user_id}\" from the company \"{company_id}\"")

    # Initialize services 
    request_crud = CompanyRequestsRepository(session)
    company_crud = CompanyRepository(session)
    user_crud = UserRepository(session)

    # Validate if requested instances exist
    request_company = await company_crud.get_company_by_id(company_id, auth["email"], admin_only=True)
    if not request_company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))

    request_user = await user_crud.get_user_by_id(user_id)
    if not request_user:
        logger.warning(f"User \"{user_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested user is not found"))

    # Validate if user is member of the company
    if not await company_crud.check_user_membership(user_id=user_id, company_id=company_id):
        logger.warning(f"User \"{request_user}\" is not the member of the company \"{request_company}\"") 
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"User {request_user.email} is not the member of the company {request_company.title}"))
    
    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    if user_id == current_user_id:
        logger.warning(f"Validation error: User \"{current_user_id}\" tried to kick itself from the company")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("You can't kick yourself from the company"))
    
    # Validate if user has permission to kick another user
    if await company_crud.user_has_role(current_user_id, request_company.id, RoleEnum.Admin) and \
    (not await company_crud.user_has_role(user_id, company_id, RoleEnum.Member)):
        logger.warning(f"Permission error: User \"{current_user_id}\" tried to kick admin or owner")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("You don't have permission to perform this action"))

    # Kick user
    await request_crud.remove_user_from_company(company_id=company_id, user_id=user_id)
    logger.info(f"Successfully kicked user \"{request_user}\" from the company \"{request_company}\"")
    return {"response": f"User {request_user.email} was successfully kicked from the company"}


@company_router.delete("/{company_id}/leave/", response_model=Optional[Dict[str, str]])
async def leave_company(company_id: int,
                        session: AsyncSession = Depends(get_async_session),
                        auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Leaving company \"{company_id}\"")

    # Initialize services 
    request_crud = CompanyRequestsRepository(session)
    company_crud = CompanyRepository(session)
    user_crud = UserRepository(session)

    # Validate if requested instances exist
    request_company = await company_crud.get_company_by_id(company_id, auth["email"])
    if not request_company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested company is not found"))

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Validate if user is member of the company
    if not await company_crud.check_user_membership(user_id=current_user_id, company_id=company_id):
        logger.warning(f"User \"{current_user_id}\" is not the member of the company \"{request_company}\"") 
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"User {current_user_id} is not the member of the company {company_id}"))
    
    # Validate if user isn't the owner of the company
    if await company_crud.user_has_role(user_id=current_user_id, company_id=company_id, role=RoleEnum.Owner):
        logger.warning("Validation error: Owner can't leave its company")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("Owner can't leave its company"))
     
    # Leave the company
    await request_crud.remove_user_from_company(company_id=company_id, user_id=current_user_id)
    logger.info(f"Successfully left company \"{company_id}\"")
    return {"response": f"You have successfully left company {company_id}"}


