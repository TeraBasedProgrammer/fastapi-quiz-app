import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth.handlers import AuthHandler
from app.companies.services import CompanyRepository
from app.database import get_async_session
from app.quizzes_workflow.schemas import AttemptReturn
from app.quizzes_workflow.services import AttemptRepository
from app.users.schemas import DeletedInstanceResponse
from app.users.services import error_handler
from app.utils import get_current_user_id

from .schemas import (AnswerCreateSchema, AnswerSchema, AnswerUpdateSchema,
                      QuestionBaseSchema, QuestionSchema, QuestionUpdateSchema,
                      QuizBaseSchema, QuizSchema, QuizUpdateSchema)
from .services import QuizRepository
from .utils import set_question_status, set_quiz_status

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

quiz_router = APIRouter(
    prefix="/quizzes",
    tags=["Quizzes"],
    responses={404: {"description": "Not found"}}
)


@quiz_router.get("/{quiz_id}/", response_model=Optional[QuizSchema])
async def get_quiz(quiz_id: int,
                    session: AsyncSession = Depends(get_async_session),
                    auth=Depends(auth_handler.auth_wrapper)):
    # Initialize services
    quiz_crud = QuizRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    request_quiz = await quiz_crud.get_quiz_by_id(quiz_id=quiz_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_quiz:
        logger.warning(f"Quiz \"{quiz_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested quiz is not found"))

    return request_quiz


@quiz_router.post("/", response_model=Optional[QuizSchema])
async def create_quiz(quiz_data: QuizBaseSchema,
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[QuizSchema]:
    logger.info(f"Creating new Quiz instance")

    # Initialize services
    quiz_crud = QuizRepository(session)
    company_crud = CompanyRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    # Validate if given company exists
    company_id = quiz_data.company_id
    company = await company_crud.get_company_by_id(company_id, current_user_id, admin_only=True)
    if not company:
        logger.warning(f"Company \"{company_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Company with id {company_id} is not found"))
    try:
        new_quiz = await quiz_crud.create_quiz(quiz_data)
        logger.info(f"New quiz instance has been successfully created")
        return new_quiz
    except IntegrityError:
        logger.warning(f"Validation error: Company \"{company_id}\" already has quiz with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"Company {company_id} already has quiz with provided title"))


@quiz_router.post("/questions/", response_model=QuestionSchema)
async def create_question(question_data: QuestionBaseSchema,
                          request: Request,
                          session: AsyncSession = Depends(get_async_session),
                          auth=Depends(auth_handler.auth_wrapper)) -> QuestionSchema:
    # Initialize services
    quiz_crud = QuizRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    # Validate if requested instances exist
    request_quiz = await quiz_crud.get_quiz_by_id(quiz_id=question_data.quiz_id, current_user_id=current_user_id, 
                                                     admin_access_only=True)
    if not request_quiz:
        logger.warning(f"Quiz \"{question_data.quiz_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Quiz with id {question_data.quiz_id} is not found"))
    
    try:
        new_question = await quiz_crud.create_question(question_data=question_data)
        logger.info(f"New question instance has been successfully created")
        return new_question
    except IntegrityError:
        logger.warning(f"Validation error: Quiz \"{question_data.quiz_id}\" already has question with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Quiz {question_data.quiz_id} already has question with provided title"))


@quiz_router.post("/answers/", response_model=Optional[AnswerSchema])
async def create_answer(answer_data: AnswerCreateSchema,
                        background_tasks: BackgroundTasks,
                        session: AsyncSession = Depends(get_async_session),
                        auth=Depends(auth_handler.auth_wrapper),) -> Optional[AnswerSchema]:
    # Initialize services
    quiz_crud = QuizRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Validate if requested instances exist
    request_question = await quiz_crud.get_question_by_id(question_id=answer_data.question_id, current_user_id=current_user_id, 
                                                           admin_access_only=True)
    if not request_question:
        logger.warning(f"Question \"{answer_data.question_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Question with id {answer_data.question_id} is not found"))
    
    question_id = request_question.id
    try:
        # Make previous correct answer uncorrect before setting up a new one
        create_data = answer_data.model_dump()
        if create_data["is_correct"]:
            await quiz_crud.unset_correct_answer(question=request_question)

        new_answer = await quiz_crud.create_answer(answer_data=answer_data)
        logger.info(f"New answer instance has been successfully created")
        await session.commit()

        # Set related question (quiz) status
        background_tasks.add_task(set_question_status, session=session, question_id=question_id)
        background_tasks.add_task(set_quiz_status, session=session, quiz_id=new_answer.question.quiz_id)

        return new_answer
    except IntegrityError:
        logger.warning(f"Validation error: Question \"{question_id}\" already has answer with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Question {question_id} already has answer with provided title"))


@quiz_router.post("/{quiz_id}/attempt/start/", 
                  response_model=AttemptReturn,)
async def start_quiz_attempt(quiz_id: int,
                            session: AsyncSession = Depends(get_async_session),
                            auth=Depends(auth_handler.auth_wrapper)) -> AttemptReturn:
    logger.info(f"Starting quiz \"{quiz_id}\" attempt")

    # Initialize services
    quiz_crud = QuizRepository(session)
    attempt_crud = AttemptRepository(session)

    current_user_id = await get_current_user_id(session, auth)
 
    request_quiz = await quiz_crud.get_quiz_by_id(quiz_id=quiz_id, current_user_id=current_user_id, member_access_only=True)
    if not request_quiz:
        logger.warning(f"Quiz \"{quiz_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler("Requested quiz is not found"))
    
    # Check if requested quiz is fully created
    if not request_quiz.fully_created:
        logger.warning(f"User \"{auth['email']}\" tried to access not fully created quiz")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("This quiz is temporarily unavailable for completion"))

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    # Check if user has available attemps for this quiz
    if not await attempt_crud.user_has_attempts(quiz_id=quiz_id, user_id=current_user_id):
        logger.warning(f"User \"{auth['email']}\" has already used all availabe attempts for quiz \"{quiz_id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("You've used all available attempts for this quiz"))

    # Check if user hasn't start this attempt already
    if await attempt_crud.has_started_attempt(current_user_id, quiz_id):
        logger.warning(f"User \"{auth['email']}\" has an ongoing attempt with quiz \"{quiz_id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("You already have an ongoing attempt with this quiz"))
    
    attempt = await attempt_crud.create_attempt(quiz_id=quiz_id, user_id=current_user_id, quiz_completion_time=request_quiz.completion_time)
    return AttemptReturn(id=attempt.id, quiz=attempt.quiz)
    
                            
@quiz_router.patch("/{quiz_id}/update/", response_model=Optional[QuizSchema])
async def update_quiz(quiz_id: int,
                      quiz_data: QuizUpdateSchema,
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> Optional[QuizSchema]:
    logger.info(f"Updating quiz instance \"{quiz_id}\"")

    # Initialize services
    quiz_crud = QuizRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    updated_quiz_params = quiz_data.model_dump(exclude_none=True)
    if updated_quiz_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("At least one valid parameter (title, description) should be provided for quiz update"))
 
    request_quiz = await quiz_crud.get_quiz_by_id(quiz_id=quiz_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_quiz:
        logger.warning(f"Quiz \"{quiz_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Quiz with id {quiz_id} is not found"))
    try:
        updated_quiz = await quiz_crud.update_quiz(quiz_id=request_quiz.id, quiz_data=quiz_data)
        logger.info(f"Quiz instance {quiz_id} has been successfully updated")
        return updated_quiz
    except IntegrityError:
        logger.warning(f"Validation error: Company \"{request_quiz.company_id}\" already has quiz with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Company {request_quiz.company_id} already has quiz with provided title"))
    

@quiz_router.patch("/questions/{question_id}/update/", response_model=Optional[QuestionSchema])
async def update_question(question_id: int,
                       question_data: QuestionUpdateSchema,
                       session: AsyncSession = Depends(get_async_session),
                       auth=Depends(auth_handler.auth_wrapper)) -> Optional[QuestionSchema]:
    logger.info(f"Updating question instance \"{question_id}\"")

    # Initialize services
    quiz_crud = QuizRepository(session)

    updated_question_params = question_data.model_dump(exclude_none=True)
    if updated_question_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("At least one valid parameter (title) should be provided for question update"))

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)
    
    question = await quiz_crud.get_question_by_id(question_id, current_user_id, admin_access_only=True)
    if not question:
        logger.warning(f"Question \"{question_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Question with id {question_id} is not found"))

    try:
        updated_question = await quiz_crud.update_question(question_id, question_data)
        logger.info(f"Question instance {question_id} has been successfully updated")
        return updated_question
    except IntegrityError:
        logger.warning(f"Validation error: Quiizz \"{question.quiz.id}\" already has question with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Quiizz {question.quiz.id} already has question with provided title"))


@quiz_router.patch("/answers/{answer_id}/update/", response_model=Optional[AnswerSchema])
async def update_answer(answer_data: AnswerUpdateSchema,
                        answer_id: int,
                        background_tasks: BackgroundTasks,
                        session: AsyncSession = Depends(get_async_session),
                        auth=Depends(auth_handler.auth_wrapper)) -> Optional[AnswerSchema]:
    logger.info(f"Updating answer instance \"{answer_id}\"")

    # Initialize services
    quiz_crud = QuizRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    updated_answer_params = answer_data.model_dump(exclude_none=True)
    if updated_answer_params == {}:
        logger.warning("Validation error: No parameters have been provided")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("At least one valid parameter (title, is_correct) should be provided for answer update"))
 
    answer = await quiz_crud.get_answer_by_id(answer_id, current_user_id, admin_access_only=True)
    if not answer:
        logger.warning(f"Answer \"{answer_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Answer with id {answer_id} is not found"))

    try:
        if answer.is_correct:
            logger.warning(f"User \"{auth['email']}\" tried to unset a correct answer")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"You can't unset a correct answer directly. Instead mark another answer as correct"))

        # Make previous correct answer uncorrect before setting up a new one
        if updated_answer_params.get("is_correct"):
            await quiz_crud.unset_correct_answer(question=answer.question)

        updated_answer = await quiz_crud.update_answer(answer_id, answer_data)
        logger.info(f"answer instance {answer_id} has been successfully updated")

        # Set related question (quiz) status
        background_tasks.add_task(set_question_status, session=session, question_id=answer.question_id)
        background_tasks.add_task(set_quiz_status, session=session, quiz_id=answer.question.quiz_id)

        return updated_answer
    except IntegrityError:
        logger.warning(f"Validation error: Question \"{answer.question_id}\" already has answer with provided title")
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail=error_handler(f"Question {answer.question_id} already has answer with provided title"))

@quiz_router.delete("/{quiz_id}/delete/", response_model=DeletedInstanceResponse)
async def delete_quiz(quiz_id: int,
                      session: AsyncSession = Depends(get_async_session),
                      auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    # Initialize services
    quiz_crud = QuizRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    request_quiz = await quiz_crud.get_quiz_by_id(quiz_id=quiz_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_quiz:
        logger.warning(f"Quiz \"{quiz_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Quiz with id {quiz_id} is not found"))

    deleted_quiz_id = await quiz_crud.delete_quiz(quiz_id=request_quiz.id)
    return DeletedInstanceResponse(deleted_instance_id=deleted_quiz_id)


@quiz_router.delete("/questions/{question_id}/delete/", response_model=DeletedInstanceResponse)
async def delete_question(question_id: int,
                          background_tasks: BackgroundTasks,
                          session: AsyncSession = Depends(get_async_session),
                          auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    # Initialize services
    quiz_crud = QuizRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    request_question = await quiz_crud.get_question_by_id(question_id=question_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_question:
        logger.warning(f"Question \"{question_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Question with id {question_id} is not found"))

    deleted_question_id = await quiz_crud.delete_question(question_id=question_id)
    
    # Set related quiz status
    background_tasks.add_task(set_quiz_status, session=session, quiz_id=request_question.quiz_id)

    return DeletedInstanceResponse(deleted_instance_id=deleted_question_id)


@quiz_router.delete("/answers/{answer_id}/delete/", response_model=DeletedInstanceResponse)
async def delete_answer(answer_id: int,
                         background_tasks: BackgroundTasks,
                         session: AsyncSession = Depends(get_async_session),
                         auth=Depends(auth_handler.auth_wrapper)) -> DeletedInstanceResponse:
    # Initialize services
    quiz_crud = QuizRepository(session)

    # Retrieving current user id
    current_user_id = await get_current_user_id(session, auth)

    request_answer = await quiz_crud.get_answer_by_id(answer_id=answer_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_answer:
        logger.warning(f"answer \"{answer_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Answer with id {answer_id} is not found"))

    if request_answer.is_correct:
        logger.warning(f"Permission error: User \"{current_user_id}\" tried to delete correct answear {request_answer.id}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler("You can't delete a correct answer"))

    deleted_answer_id = await quiz_crud.delete_answer(answer_id=answer_id)

    # Set related question and quiz status 
    background_tasks.add_task(set_question_status, session=session, question_id=request_answer.question_id)
    background_tasks.add_task(set_quiz_status, session=session, quiz_id=request_answer.question.quiz_id)

    return DeletedInstanceResponse(deleted_instance_id=deleted_answer_id)
