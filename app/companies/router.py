import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, Params, paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.handlers import AuthHandler
from app.database import get_async_session
from app.schemas import CompanyFullSchema
from app.users.services import error_handler

from .schemas import CompanyCreate, CompanySchema
from .services import CompanyRepository

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

company_router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
    responses={404: {"description": "Not found"}}
)


@company_router.get("/", response_model=Page[CompanyFullSchema], response_model_exclude={"role"})
async def get_all_companies(session: AsyncSession = Depends(get_async_session),
                    params: Params = Depends()) -> Page[CompanyFullSchema]:
    logger.info("Getting all companies from the database")
    crud = CompanyRepository(session)
    result = await crud.get_companies() 
    logger.info("All companies have been successfully retrieved")
    print(result)
    return paginate(result, params)


@company_router.get("/{company_id}", response_model=Optional[CompanyFullSchema], response_model_exclude={"role"})
async def get_company(company_id: int, session: AsyncSession = Depends(get_async_session)) -> Optional[CompanyFullSchema]:
    logger.info(f"Trying to get Company instance by id '{company_id}'")
    crud = CompanyRepository(session)
    info = await crud.get_company_by_id(company_id)
    if not info:
        logger.warning(f"Company '{company_id}' is not found")
        raise HTTPException(404, error_handler("Company is not found"))
    logger.info(f"Successfully retrieved Company instance '{company_id}'")
    return info


@company_router.post("/", response_model=Optional[CompanyFullSchema], status_code=201, response_model_exclude={"role"})
async def create_company(company: CompanyCreate, 
                         session: AsyncSession = Depends(get_async_session)) -> Optional[CompanyFullSchema]:
    logger.info(f"Trying to create new Company instance")
    crud = CompanyRepository(session)
    company_existing_object = await crud.get_company_by_title(company.title)
    if company_existing_object: 
        logger.warning(f"Validation error: Company with name '{company.title}' already exists")
        raise HTTPException(400, detail=error_handler("Company with this name already exists"))
    result = await crud.create_company(company)
    logger.info(f"New company instance has been successfully created")
    return CompanyFullSchema.model_validate(result)
