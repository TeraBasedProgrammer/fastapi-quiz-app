import logging
from datetime import timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import redis
from app.utils import create_model_instance

from .models import Attemp
from .schemas import CreateAttemp

logger = logging.getLogger("main_logger")


class AttempRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def create_attemp(self, quiz_id: int, user_id: int, quiz_completion_time: int) -> Attemp:
        logger.debug(f"Received data:\nquiz_id -> {quiz_id}\nuser_id -> {user_id}\nquiz_completion_time -> {quiz_completion_time}")
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
            select(func.count(Attemp.id))
            .where((Attemp.user_id == user_id) & (Attemp.quiz_id == quiz_id))
        )

        if used_attemps.scalar() >= 2:
            return False
        return True
    
    async def get_attemp_by_id(self, attemp_id: int) -> Optional[Attemp]:
        logger.debug(f"Received data:\nattemp_id -> {attemp_id}")
        query = await self.db_session.execute(
                      select(Attemp)
                      .where(Attemp.id == attemp_id))
        result = query.unique().scalar_one_or_none()
        return result

    async def save_answer(
        self,
        attemp_id: int,
        quiz_id: int,
        question_id: int,
        answer_id: int
    ) -> None:
        logger.debug(f"Received data:\nattemp_id -> {attemp_id}\nquiz_id -> {quiz_id}\nquestion_id -> {question_id}\nanswer_id -> {answer_id}")
        logger.info(f"Saving user answer for quiz \"{quiz_id}\" in redis for 48 hours ")
        key = f"{attemp_id}:{quiz_id}:{question_id}"
        await redis.set(key, answer_id, ex=172800)

        logger.info("Answer for was successfully saved")