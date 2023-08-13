import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth.handlers import AuthHandler
from app.companies.services import CompanyRepository
from app.database import get_async_session
from app.users.schemas import DeletedInstanceResponse
from app.users.services import error_handler
from app.utils import get_current_user_id

from .schemas import (AnswearCreateSchema, AnswearSchema, AnswearUpdateSchema,
                      QuestionBaseSchema, QuestionSchema, QuestionUpdateSchema,
                      QuizzBaseSchema, QuizzSchema, QuizzUpdateSchema)
from .services import QuizzRepository

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

quizz_router = APIRouter(
    prefix="/quizzes",
    tags=["Quizzes"],
    responses={404: {"description": "Not found"}}
)


@quizz_router.get("/{quizz_id}", response_model=Optional[QuizzSchema])
async def get_quizz(quizz_id: int,
                    session: AsyncSession = Depends(get_async_session),
                    auth=Depends(auth_handler.auth_wrapper)):
    # Initialize services
    quizz_crud = QuizzRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)
 
    request_quizz = await quizz_crud.get_quizz_by_id(quizz_id=quizz_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_quizz:
        logger.warning(f"Quizz \"{quizz_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested quizz is not found"))

    return request_quizz


@quizz_router.post("/", response_model=Optional[QuizzSchema])
async def create_quizz(quizz_data: QuizzBaseSchema,
                       session: AsyncSession = Depends(get_async_session),
                       auth=Depends(auth_handler.auth_wrapper)) -> Optional[QuizzSchema]:
    logger.info(f"Creating new Quizz instance")

    # Initialize services
    quizz_crud = QuizzRepository(session)
    company_crud = CompanyRepository(session)

    # Validate if given company exists
    company_id = quizz_data.company_id
    company = await company_crud.get_company_by_id(company_id, auth["email"], admin_only=True)
    if not company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Company with id {company_id} is not found"))
    try:
        new_quizz = await quizz_crud.create_quizz(quizz_data)
        logger.info(f"New quizz instance has been successfully created")
        return new_quizz
    except IntegrityError:
        logger.warning(f"Validation error: Company \"{company_id}\" already has quizz with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"Company {company_id} already has quizz with provided title"))


@quizz_router.post("/questions/", response_model=QuestionSchema)
async def create_question(question_data: QuestionBaseSchema,
                          session: AsyncSession = Depends(get_async_session),
                          auth=Depends(auth_handler.auth_wrapper)) -> QuestionSchema:
    # Initialize services
    quizz_crud = QuizzRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Validate if requested instances exist
    request_quizz = await quizz_crud.get_quizz_by_id(quizz_id=question_data.quizz_id, current_user_id=current_user_id, 
                                                     admin_access_only=True)
    if not request_quizz:
        logger.warning(f"Quizz \"{question_data.quizz_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Quizz with id {question_data.quizz_id} is not found"))
    
    try:
        new_question = await quizz_crud.create_question(question_data=question_data)
        logger.info(f"New question instance has been successfully created")
        return new_question
    except IntegrityError:
        logger.warning(f"Validation error: Quizz \"{question_data.quizz_id}\" already has question with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Quizz {question_data.quizz_id} already has question with provided title"))


@quizz_router.post("/answears/", response_model=Optional[AnswearSchema])
async def create_answear(answear_data: AnswearCreateSchema,
                         session: AsyncSession = Depends(get_async_session),
                         auth=Depends(auth_handler.auth_wrapper)) -> Optional[AnswearSchema]:
    # Initialize services
    quizz_crud = QuizzRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Validate if requested instances exist
    request_question = await quizz_crud.get_question_by_id(question_id=answear_data.question_id, current_user_id=current_user_id, 
                                                           admin_access_only=True)
    if not request_question:
        logger.warning(f"Question \"{answear_data.question_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Question with id {answear_data.question_id} is not found"))
    
    question_id = request_question.id
    try:
        new_answear = await quizz_crud.create_answear(answear_data=answear_data)
        logger.info(f"New answear instance has been successfully created")
        return new_answear
    except IntegrityError:
        logger.warning(f"Validation error: Question \"{question_id}\" already has answear with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Question {question_id} already has answear with provided title"))
    
                            
@quizz_router.patch("/{quizz_id}/update", response_model=Optional[QuizzSchema])
async def update_quizz(quizz_id: int,
                       quizz_data: QuizzUpdateSchema,
                       session: AsyncSession = Depends(get_async_session),
                       auth=Depends(auth_handler.auth_wrapper)) -> Optional[QuizzSchema]:
    logger.info(f"Updating quizz instance \"{quizz_id}\"")

    # Initialize services
    quizz_crud = QuizzRepository(session)

    updated_quizz_params = quizz_data.model_dump(exclude_none=True)
    if updated_quizz_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("At least one parameter should be provided for quizz update"))

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)
    
    request_quizz = await quizz_crud.get_quizz_by_id(quizz_id=quizz_id, current_user_id=current_user_id, admin_access_only=True)
    try:
        updated_quizz = await quizz_crud.update_quizz(quizz_id=request_quizz.id, quizz_data=quizz_data)
        logger.info(f"Quizz instance {quizz_id} has been successfully updated")
        return updated_quizz
    except IntegrityError:
        logger.warning(f"Validation error: Company \"{request_quizz.company_id}\" already has quizz with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Company {request_quizz.company_id} already has quizz with provided title"))
    

@quizz_router.patch("/questions/{question_id}/update", response_model=Optional[QuestionSchema])
async def update_question(question_id: int,
                       question_data: QuestionUpdateSchema,
                       session: AsyncSession = Depends(get_async_session),
                       auth=Depends(auth_handler.auth_wrapper)) -> Optional[QuestionSchema]:
    logger.info(f"Updating question instance \"{question_id}\"")

    # Initialize services
    quizz_crud = QuizzRepository(session)

    updated_question_params = question_data.model_dump(exclude_none=True)
    if updated_question_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("At least one parameter should be provided for question update"))

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)
    
    question = await quizz_crud.get_question_by_id(question_id, current_user_id, admin_access_only=True)
    if not question:
        logger.warning(f"Question \"{question_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Question with id {question_id} is not found"))

    try:
        updated_question = await quizz_crud.update_question(question_id, question_data)
        logger.info(f"Question instance {question_id} has been successfully updated")
        return updated_question
    except IntegrityError:
        logger.warning(f"Validation error: Quiizz \"{question.quizz.id}\" already has question with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Quiizz {question.quizz.id} already has question with provided title"))


@quizz_router.patch("/answears/{answear_id}/update", response_model=Optional[AnswearSchema])
async def update_answear(answear_data: AnswearUpdateSchema,
                         answear_id: int,
                         session: AsyncSession = Depends(get_async_session),
                         auth=Depends(auth_handler.auth_wrapper)) -> Optional[AnswearSchema]:
    logger.info(f"Updating answear instance \"{answear_id}\"")

    # Initialize services
    quizz_crud = QuizzRepository(session)

    updated_answear_params = answear_data.model_dump(exclude_none=True)
    if updated_answear_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("At least one parameter should be provided for answear update"))

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)
    
    answear = await quizz_crud.get_answear_by_id(answear_id, current_user_id, admin_access_only=True)
    if not answear:
        logger.warning(f"Answear \"{answear_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Answear with id {answear_id} is not found"))

    try:
        updated_answear = await quizz_crud.update_answear(answear_id, answear_data)
        logger.info(f"Answear instance {answear_id} has been successfully updated")
        return updated_answear
    except IntegrityError:
        logger.warning(f"Validation error: Question \"{answear.question_id}\" already has answear with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Question {answear.question_id} already has answear with provided title"))

@quizz_router.delete("/{quizz_id}/delete", response_model=DeletedInstanceResponse)
async def delete_quizz(quizz_id: int,
                       session: AsyncSession = Depends(get_async_session),
                       auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    # Initialize services
    quizz_crud = QuizzRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)
    request_quizz = await quizz_crud.get_quizz_by_id(quizz_id=quizz_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_quizz:
        logger.warning(f"Quizz \"{quizz_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested quizz is not found"))

    deleted_quizz_id = await quizz_crud.delete_quizz(quizz_id=request_quizz.id)
    return DeletedInstanceResponse(deleted_instance_id=deleted_quizz_id)


@quizz_router.delete("/questions/{question_id}/delete", response_model=DeletedInstanceResponse)
async def delete_question(question_id: int,
                       session: AsyncSession = Depends(get_async_session),
                       auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    # Initialize services
    quizz_crud = QuizzRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    request_question = await quizz_crud.get_question_by_id(question_id=question_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_question:
        logger.warning(f"Question \"{question_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested question is not found"))

    deleted_question_id = await quizz_crud.delete_question(question_id=question_id)
    return DeletedInstanceResponse(deleted_instance_id=deleted_question_id)


@quizz_router.delete("/answears/{answear_id}/delete", response_model=DeletedInstanceResponse)
async def delete_answear(answear_id: int,
                         session: AsyncSession = Depends(get_async_session),
                         auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    # Initialize services
    quizz_crud = QuizzRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    request_answear = await quizz_crud.get_answear_by_id(answear_id=answear_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_answear:
        logger.warning(f"Answear \"{answear_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested answear is not found"))

    deleted_answear_id = await quizz_crud.delete_answear(answear_id=answear_id)
    return DeletedInstanceResponse(deleted_instance_id=deleted_answear_id)
