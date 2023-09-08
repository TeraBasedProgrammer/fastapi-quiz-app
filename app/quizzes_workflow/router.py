import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.utils import get_current_user_id
from app.auth.handlers import AuthHandler
from app.database import get_async_session
from app.quizzes.services import QuizRepository
from app.users.services import error_handler

from .services import AttempRepository
    

logger = logging.getLogger("main_logger")
auth_handler = AuthHandler()

attemp_router = APIRouter(
    prefix="/attempps", tags=["Attemps"], responses={404: {"description": "Not found"}}
)


@attemp_router.post(
    "/{attemp_id}/answer-question/{question_id}/{answer_id}/",
    response_model=Dict[str, str],
)
async def answer_question(
    attemp_id: int,
    question_id: int,
    answer_id: int,
    session: AsyncSession = Depends(get_async_session),
    auth=Depends(auth_handler.auth_wrapper),
) -> Dict[str, str]:
    logger.info(f"Answering question \"{question_id}\" on attemp \"{attemp_id}\" with answer \"{answer_id}\"")

    # Initialize services
    attemp_crud = AttempRepository(session)
    quiz_crud = QuizRepository(session)

    current_user_id = await get_current_user_id(session, auth)

    # Validate if requested instances exist and if user can access them
    request_attemp = await attemp_crud.get_attemp_by_id(attemp_id)
    if not request_attemp:
        logger.warning(f"Attemp \"{attemp_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Attemp with id {attemp_id} is not found"))
    
    if request_attemp.user_id != current_user_id:
        logger.warning(f"Permission error: User \"{current_user_id}\" is not the performer of the attemp \"{attemp_id}\"")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

    request_question = await quiz_crud.get_question_by_id(question_id=question_id, current_user_id=current_user_id, admin_access_only=True)
    if not request_question:
        logger.warning(f"Question \"{question_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Question with id {question_id} is not found"))

    if request_question.quiz_id != request_attemp.quiz_id:
        logger.warning(f"Current attemp's quiz \"{request_attemp.quiz_id}\" doesn't have question \"{request_question.id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"Quiz {request_attemp.quiz_id} doesn't have question {question_id}"))
    
    request_answer = await quiz_crud.get_answer_by_id(answer_id, current_user_id, admin_access_only=True)
    if not request_answer:
        logger.warning(f"Answer \"{answer_id}\" is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=error_handler(f"Answer with id {answer_id} is not found"))
    
    if request_answer.question_id != request_question.id:
        logger.warning(f"Current attemp's question \"{request_question.id}\" doesn't have answer \"{request_answer.id}\"")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_handler(f"Question {request_question.id} doesn't have answer {answer_id}"))

    # Add data to Redis
    await attemp_crud.save_answer(
        attemp_id=request_attemp.id, 
        quiz_id=request_attemp.quiz_id,
        question_id=question_id,
        answer_id=answer_id,
    )
    return {"response": "Answer received"}