import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.quizzes.models import Question, Quiz
from app.quizzes.schemas import UpdateModelStatus
from app.utils import update_model_instance
from app.quizzes.services import QuizRepository


logger = logging.getLogger("main_logger")


async def _set_quiz_status(session: AsyncSession, quiz: Quiz, status: bool) -> None:
    if not quiz.fully_created == status:
        await update_model_instance(session, Quiz, quiz.id, UpdateModelStatus(fully_created=status))


async def _set_question_status(session: AsyncSession, question: Question, status: bool) -> None:
    if not question.fully_created == status:
        await update_model_instance(session, Question, question.id, UpdateModelStatus(fully_created=status))


# Signal to detect whether to mark quiz as fully_created
async def set_quiz_status(session: AsyncSession, quiz_id: int):
    logger.info("Set_quiz_status singal was triggered")

    # Get quiz instance
    quiz_crud = QuizRepository(session)
    quiz = await quiz_crud.get_quiz_by_id(quiz_id, None)

    if len(quiz.questions) >= 2:
        for question in quiz.questions:
            if not question.fully_created:
                await _set_quiz_status(session, quiz, False)
                break
        else:
            await _set_quiz_status(session, quiz, True)
    else:
        await _set_quiz_status(session, quiz, False)

    logger.info(f"Quiz \"{quiz.id}\" fully_created status has been changed")


# Signal to detect whether to mark question as fully_created
async def set_question_status(session: AsyncSession, question_id: int):
    logger.info("Set_question_status singal was triggered")

    # Get question instance
    quiz_crud = QuizRepository(session)
    question = await quiz_crud.get_question_by_id(question_id, None)

    if len(question.answers) >= 2:
        for answer in question.answers:
            if answer.is_correct:
                await _set_question_status(session, question, True)
                break
        else:
            await _set_question_status(session, question, False)
    else:
        await _set_question_status(session, question, False)

    logger.info(f"Question \"{question.id}\" fully_created status has been changed")
