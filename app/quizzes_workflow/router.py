import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth.handlers import AuthHandler
from app.database import get_async_session
from app.quizzes.services import QuizRepository
from app.users.services import UserRepository, error_handler
from app.utils import get_current_user_id

from .schemas import AttemptResultResponseModel
from .services import AttemptRepository
from .utils import attempt_is_completed

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

attempt_router = APIRouter(
    prefix="/attempts", tags=["Attempts"], responses={404: {"description": "Not found"}}
)


@attempt_router.get("/{attempt_id}/answers/", response_model=AttemptResultResponseModel)
async def get_attempt_answers(
    attempt_id: int,
    session: AsyncSession = Depends(get_async_session),
    auth=Depends(auth_handler.auth_wrapper)
):
    # Initialize services
    attempt_crud = AttemptRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    request_attempt = await attempt_crud.get_attempt_by_id(
        attempt_id=attempt_id,
        current_user_id=current_user_id,
        validate_user=True,
    )

    if not request_attempt:
        logger.warning(f"Attempt \"{attempt_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Attempt with id {attempt_id} is not found"))

    # Check if attempt is completed
    if not await attempt_is_completed(request_attempt, datetime.utcnow()):
        logger.warning(f"Attemp \"{attempt_id}\" is not completed")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler(f"Forbidden"))

    answers = await attempt_crud.get_attempt_results(attempt_id)
    if not answers:
        logger.warning(f"Results for attemp \"{attempt_id}\" has expired")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Not found"))
    
    return answers
    

@attempt_router.post(
    "/{attempt_id}/answer-question/{question_id}/{answer_id}/",
    response_model=Dict[str, str],
)
async def answer_question(
    attempt_id: int,
    question_id: int,
    answer_id: int,
    session: AsyncSession = Depends(get_async_session),
    auth=Depends(auth_handler.auth_wrapper),
) -> Dict[str, str]:
    logger.info(f"Answering question \"{question_id}\" on attempt \"{attempt_id}\" with answer \"{answer_id}\"")

    # Initialize services
    attempt_crud = AttemptRepository(session)
    quiz_crud = QuizRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    # Validate if requested instances exist and if user can access them

    # Attempt
    request_attempt = await attempt_crud.get_attempt_by_id(
        attempt_id=attempt_id, 
        current_user_id=current_user_id, 
        validate_user=True
    )

    if not request_attempt:
        logger.warning(f"Attempt \"{attempt_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Attempt with id {attempt_id} is not found"))
    
    # Check if attempt is completed
    if await attempt_is_completed(request_attempt, datetime.utcnow()):
        logger.warning(f"User \"{current_user_id}\" has already completed attempt \"{attempt_id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"You've already completed this attempt"))

    # Question
    request_question = await quiz_crud.get_question_by_id(question_id=question_id, current_user_id=current_user_id, member_access_only=True)
    if not request_question:
        logger.warning(f"Question \"{question_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Question with id {question_id} is not found"))

    if request_question.quiz_id != request_attempt.quiz_id:
        logger.warning(f"Current attempt's quiz \"{request_attempt.quiz_id}\" doesn't have question \"{request_question.id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"Quiz {request_attempt.quiz_id} doesn't have question {question_id}"))
    
    # Answer
    request_answer = await quiz_crud.get_answer_by_id(answer_id, current_user_id=current_user_id, member_access_only=True)
    if not request_answer:
        logger.warning(f"Answer \"{answer_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Answer with id {answer_id} is not found"))
    
    if request_answer.question_id != request_question.id:
        logger.warning(f"Current attempt's question \"{request_question.id}\" doesn't have answer \"{request_answer.id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"Question {request_question.id} doesn't have answer {answer_id}"))

    # Add data to Redis
    await attempt_crud.save_answer(
        attempt_id=request_attempt.id, 
        quiz_id=request_attempt.quiz_id,
        question_id=question_id,
        answer_id=answer_id,
        quiz_completion_time=request_attempt.quiz.completion_time
    )
    return {"response": "Answer received"}


@attempt_router.post("/{attempt_id}/complete/", response_model=Dict[str, str])
async def complete_attempt(
    attempt_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    auth=Depends(auth_handler.auth_wrapper)
) -> Dict[str, str]:
    # Initialize services
    attempt_crud = AttemptRepository(session)
    user_crud = UserRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    request_attempt = await attempt_crud.get_attempt_by_id(
        attempt_id=attempt_id,
        current_user_id=current_user_id,
        validate_user=True,
    )

    if not request_attempt:
        logger.warning(f"Attempt \"{attempt_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Attempt with id {attempt_id} is not found"))
    
    # Check if attempt is already completed
    if await attempt_is_completed(request_attempt, datetime.utcnow()):
        logger.warning(f"User \"{current_user_id}\" has already completed attempt \"{attempt_id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"You've already completed this attempt"))

    result = await attempt_crud.calculate_attempt_result(attempt=request_attempt, timestamp=datetime.utcnow())

    # Update user ratings
    background_tasks.add_task(user_crud.set_global_score, user_id=request_attempt.user_id)
    background_tasks.add_task(
        user_crud.set_company_score, 
        user_id=request_attempt.user_id, 
        company_id=request_attempt.quiz.company_id,
    )

    return {"result": f"{result}"} 