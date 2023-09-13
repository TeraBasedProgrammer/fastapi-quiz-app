import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.database import redis
from app.quizzes.models import Answer
from app.users.services import error_handler
from app.utils import create_model_instance, update_model_instance

from .models import Attempt
from .schemas import AttemptResult, CreateAttempt
from .utils import attempt_is_completed

logger = logging.getLogger("main_logger")


class AttemptRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create_attempt(
        self, quiz_id: int, user_id: int, quiz_completion_time: int
    ) -> Attempt:
        logger.debug(
            f"Received data:\nquiz_id -> {quiz_id}\nuser_id -> {user_id}\nquiz_completion_time -> {quiz_completion_time}"
        )
        attempt = await create_model_instance(
            self.db_session,
            Attempt,
            CreateAttempt(
                quiz_id=quiz_id, 
                user_id=user_id, 
                start_time=datetime.utcnow()
            ),
        )
        attempt.end_time = attempt.start_time + timedelta(minutes=quiz_completion_time)

        await self.db_session.commit()

        logger.debug(f"Successfully inserted new attempt instance into the database")
        return attempt

    async def user_has_attempts(self, quiz_id: int, user_id: int) -> bool:
        logger.debug(f"Received data:\nquiz_id -> {quiz_id}\nuser_id -> {user_id}")

        used_attempts = await self.db_session.execute(
            select(func.count(Attempt.id)).where(
                (Attempt.user_id == user_id) & (Attempt.quiz_id == quiz_id)
            )
        )

        if len(used_attempts.scalars().unique().all()) >= 2:
            return False
        return True

    async def get_attempt_by_id(
        self, 
        attempt_id: int, 
        current_user_id: int, 
        validate_user: bool = False
    ) -> Optional[Attempt]:
        logger.debug(f"Received data:\nattempt_id -> {attempt_id}")
        query = await self.db_session.execute(
            select(Attempt).where(Attempt.id == attempt_id)
        )
        result = query.unique().scalar_one_or_none()

        # Validate if user can access the attempt
        if result and validate_user:
            if result.user_id != current_user_id:
                logger.warning(f"Permission error: User \"{current_user_id}\" is not the performer of the attempt \"{attempt_id}\"")
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

        return result

    async def save_answer(
        self, attempt_id: int, quiz_id: int, question_id: int, answer_id: int
    ) -> None:
        logger.debug(
            f"Received data:\nattempt_id -> {attempt_id}\nquiz_id -> {quiz_id}\nquestion_id -> {question_id}\nanswer_id -> {answer_id}"
        )
        logger.info(f'Saving user answer for quiz "{quiz_id}" in redis for 48 hours ')
        key = f"{attempt_id}:{quiz_id}:{question_id}"
        await redis.set(key, answer_id, ex=172800)

        logger.info("Answer for was successfully saved")

    async def has_started_attempt(self, user_id: int, quiz_id: int) -> bool:
        logger.debug(f"Received data:\nquiz_id -> {quiz_id}\nuser_id -> {user_id}")
        result = await self.db_session.execute(
            select(Attempt).where(
                (Attempt.user_id == user_id) & (Attempt.quiz_id == quiz_id)
            )
        )
        
        attempt = result.unique().scalar_one_or_none()
        if not attempt:
            logger.info(f"User \"{user_id}\" doesn't have ongoing attemps with quiz \"{quiz_id}\"")
            return False
        
        if not await attempt_is_completed(attempt, datetime.utcnow()):
            logger.info(f"User \"{user_id}\" has an ongoing attempt with quiz \"{quiz_id}\"")
            return True
        
        logger.info(f"User \"{user_id}\" doesn't have ongoing attempts with quiz \"{quiz_id}\"")
        return False

    async def calculate_attempt_result(
        self,
        attempt: Attempt,
        timestamp: datetime,
    ) -> str:
        logger.debug(f"Received data:\nattempt -> {attempt}\ntimestamp -> {timestamp}")  

        spent_time: timedelta = timestamp - attempt.start_time
        spent_time_str = (datetime(2010, 1, 1, 0, 0, 0) + spent_time).strftime("%M:%S")

        # Get all keys from redis related to the given attempt
        answers_keys = await redis.keys(f"{attempt.id}*")
        answers_values = [int(answer) for answer in await redis.mget(answers_keys)]

        # Retrieve answers from database
        query = await self.db_session.execute(
            select(Answer)
            .where(Answer.id.in_(answers_values))
        )
        answers_instances = query.scalars().unique().all()

        # Count correct answers
        result = 0
        if answers_instances:
            for answer in answers_instances:
                if answer.is_correct:
                    result += 1

        # Set attempt results

        await update_model_instance(
            self.db_session, 
            Attempt, attempt.id, 
            AttemptResult(spent_time=spent_time_str, result=result),
        )        

        return f"{result}/{attempt.quiz.questions_count}"
    
    async def set_attempt_result_delayed(completion_time: int) -> None:
        await asyncio.sleep(completion_time * 60 + 2)

