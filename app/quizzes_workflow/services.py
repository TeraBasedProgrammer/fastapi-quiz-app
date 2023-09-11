import logging
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

from .models import Attemp
from .schemas import CreateAttemp, AttempResult
from .utils import attemp_is_completed

logger = logging.getLogger("main_logger")


class AttempRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create_attemp(
        self, quiz_id: int, user_id: int, quiz_completion_time: int
    ) -> Attemp:
        logger.debug(
            f"Received data:\nquiz_id -> {quiz_id}\nuser_id -> {user_id}\nquiz_completion_time -> {quiz_completion_time}"
        )
        attemp = await create_model_instance(
            self.db_session,
            Attemp,
            CreateAttemp(quiz_id=quiz_id, user_id=user_id),
        )
        attemp.end_time = attemp.start_time + timedelta(minutes=quiz_completion_time)

        await self.db_session.commit()

        logger.debug(f"Successfully inserted new attemp instance into the database")
        return attemp

    async def user_has_attemps(self, quiz_id: int, user_id: int) -> bool:
        logger.debug(f"Received data:\nquiz_id -> {quiz_id}\nuser_id -> {user_id}")

        used_attemps = await self.db_session.execute(
            select(func.count(Attemp.id)).where(
                (Attemp.user_id == user_id) & (Attemp.quiz_id == quiz_id)
            )
        )

        if used_attemps.scalar() >= 2:
            return False
        return True

    async def get_attemp_by_id(
        self, 
        attemp_id: int, 
        current_user_id: int, 
        validate_user: bool = False
    ) -> Optional[Attemp]:
        logger.debug(f"Received data:\nattemp_id -> {attemp_id}")
        query = await self.db_session.execute(
            select(Attemp).where(Attemp.id == attemp_id)
        )
        result = query.unique().scalar_one_or_none()

        # Validate if user can access the attemp
        if result and validate_user:
            if result.user_id != current_user_id:
                logger.warning(f"Permission error: User \"{current_user_id}\" is not the performer of the attemp \"{attemp_id}\"")
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))

        return result

    async def save_answer(
        self, attemp_id: int, quiz_id: int, question_id: int, answer_id: int
    ) -> None:
        logger.debug(
            f"Received data:\nattemp_id -> {attemp_id}\nquiz_id -> {quiz_id}\nquestion_id -> {question_id}\nanswer_id -> {answer_id}"
        )
        logger.info(f'Saving user answer for quiz "{quiz_id}" in redis for 48 hours ')
        key = f"{attemp_id}:{quiz_id}:{question_id}"
        await redis.set(key, answer_id, ex=172800)

        logger.info("Answer for was successfully saved")

    async def has_started_attemp(self, user_id: int, quiz_id: int) -> bool:
        logger.debug(f"Received data:\nquiz_id -> {quiz_id}\nuser_id -> {user_id}")
        result = await self.db_session.execute(
            select(Attemp).where(
                (Attemp.user_id == user_id) & (Attemp.quiz_id == quiz_id)
            )
        )
        
        attemp = result.scalar()
        if not attemp:
            logger.info(f"User \"{user_id}\" doesn't have ongoing attemps with quiz \"{quiz_id}\"")
            return False
        
        if not await attemp_is_completed(attemp, datetime.utcnow()):
            logger.info(f"User \"{user_id}\" has an ongoing attemp with quiz \"{quiz_id}\"")
            return True
        
        logger.info(f"User \"{user_id}\" doesn't have ongoing attemps with quiz \"{quiz_id}\"")
        return False

    async def calculate_attemp_result(
        self,
        attemp: Attemp,
        timestamp: datetime,
    ) -> str:
        logger.debug(f"Received data:\nattemp -> {attemp}\ntimestamp -> {timestamp}")  

        spent_time: timedelta = timestamp - attemp.start_time
        spent_time_str = (datetime(2010, 1, 1, 0, 0, 0) + spent_time).strftime("%M:%S")

        # Get all keys from redis related to the given attemp
        answers_keys = await redis.keys(f"{attemp.id}*")
        answers_values = await redis.mget(answers_keys)

        # Retrieve answers from database
        query = await self.db_session.execute(
            select(Answer)
            .where(Answer.id.in_(answers_values))
        )
        answers_instances = query.scalar()

        # Count correct answers
        result = 0
        if answers_instances:
            for answer in answers_instances:
                if answer.is_correct:
                    result += 1

        await update_model_instance(
            self.db_session, 
            Attemp, attemp.id, 
            AttempResult(spent_time=spent_time_str, result=result),
        )        

        return f"{result}/{attemp.quiz.questions_count}"

        

