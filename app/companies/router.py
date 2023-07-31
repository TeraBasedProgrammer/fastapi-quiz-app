import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, Params, paginate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.handlers import AuthHandler
from app.database import get_async_session
from app.schemas import CompanyFullSchema
from app.users.schemas import DeletedInstanceResponse
from app.users.services import error_handler

from .schemas import CompanyCreate, CompanyUpdate
from .services import CompanyRepository
from .utils import confirm_company_owner, filter_companies_response

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

    response = [CompanyFullSchema.from_model(c) for c in await filter_companies_response(result)]
    return paginate(response, params)


# Fix response validation error
@company_router.get("/{company_id}", response_model=Optional[CompanyFullSchema], response_model_exclude_none=True)
async def get_company(company_id: int, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[CompanyFullSchema]:
    logger.info(f"Trying to get Company instance by id '{company_id}'")
    company_crud = CompanyRepository(session)
    info = await company_crud.get_company_by_id(company_id, auth["email"])
    if not info:
        logger.warning(f"Company '{company_id}' is not found")
        raise HTTPException(404, error_handler("Company is not found"))
    logger.info(f"Successfully retrieved Company instance '{company_id}'")
    return CompanyFullSchema.from_model(info, public_request=False)


@company_router.post("/", response_model=Optional[Dict[str, Any]], status_code=201, response_model_exclude_none=True)
async def create_company(company: CompanyCreate, 
                         session: AsyncSession = Depends(get_async_session),
                         auth=Depends(auth_handler.auth_wrapper)) -> Optional[Dict[str, str]]:
    logger.info(f"Trying to create new Company instance")
    company_crud = CompanyRepository(session)
    company_existing_object = await company_crud.get_company_by_title(company.title)
    if company_existing_object: 
        logger.warning(f"Validation error: Company with name '{company.title}' already exists")
        raise HTTPException(400, detail=error_handler("Company with this name already exists"))
    result = await company_crud.create_company(company, auth['email'])
    logger.info(f"New company instance has been successfully created")
    return result


@company_router.patch("/{company_id}/update", response_model=Optional[CompanyFullSchema], response_model_exclude_none=True)
async def update_company(company_id: int, body: CompanyUpdate, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[CompanyFullSchema]:
    logger.info(f"Trying to update Company instance '{company_id}'")
    company_crud = CompanyRepository(session)
    updated_user_params = body.model_dump(exclude_none=True)
    if updated_user_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(
            status_code=400,
            detail=error_handler("At least one parameter should be provided for user update query"),
        )
    try: 
        company_for_update = await company_crud.get_company_by_id(company_id, auth["email"])
        if not company_for_update:
            logger.warning(f"Company '{company_id}' is not found")
            raise HTTPException(
                status_code=404, detail=error_handler("Company is not found")
            )
        
        # Check persmissions
        await confirm_company_owner(company_for_update, auth['email'])
        
        logger.info(f"Company {company_id} have been successfully updated")
        return CompanyFullSchema.from_model(await company_crud.update_company(company_id, body))
    except IntegrityError:
        logger.warning(f"Validation error: Company with provided title already exists")
        raise HTTPException(400, detail=error_handler("Company with this title already exists"))


@company_router.delete("/{company_id}/delete", response_model=Optional[DeletedInstanceResponse], response_model_exclude_none=True)
async def delete_company(company_id: int, 
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    logger.info(f"Trying to delete Company instance '{company_id}'")
    company_crud = CompanyRepository(session)

    # Check if company exists
    company_for_deletion = await company_crud.get_company_by_id(company_id, auth["email"])
    if not company_for_deletion:
        logger.warning(f"Company '{company_id}' is not found")
        raise HTTPException(
            status_code=404, detail=error_handler("Company is not found")
        )
    
    # Check persmissions
    await confirm_company_owner(company_for_deletion, auth['email'])

    deleted_company_id = await company_crud.delete_company(company_id)
    logger.info(f"Company {company_id} has been successfully deleted from the database")
    return DeletedInstanceResponse(deleted_instance_id=deleted_company_id)

