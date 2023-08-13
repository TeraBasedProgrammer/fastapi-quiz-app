import logging
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.utils import create_model_instance, update_model_instance, delete_model_instance
from app.companies.models import Company, RoleEnum
from app.companies.services import CompanyRepository
from app.users.services import error_handler

from .models import Answear, Question, Quizz
from .schemas import (AnswearCreateSchema, AnswearUpdateSchema,
                      QuestionBaseSchema, QuestionUpdateSchema,
                      QuizzBaseSchema, QuizzUpdateSchema)

logger = logging.getLogger("main_logger")


class QuizzRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def get_company_quizzes(self, company_id) -> List[Quizz]:
        query = await self.db_session.execute(
                      select(Quizz)
                      .outerjoin(Question, Question.quizz_id == Quizz.id)
                      .outerjoin(Answear, Answear.question_id == Question.id)
                      .where(Quizz.company_id == company_id))
        result = query.unique().scalars().all()
        return result 
    
    async def get_quizz_by_id(
              self, 
              quizz_id: int,
              current_user_id: int,
              admin_access_only: bool = False) -> Optional[Quizz]:
        logger.debug(f"Received data:\nquizz_id -> {quizz_id}")
        query = await self.db_session.execute(
                      select(Quizz)
                      .outerjoin(Question, Question.quizz_id == Quizz.id)
                      .outerjoin(Answear, Answear.question_id == Question.id)
                      .where(Quizz.id == quizz_id))
        result = query.unique().scalar_one_or_none()

        if result:
            if admin_access_only:
                company_crud = CompanyRepository(self.db_session)
                # Validate if user has permission to acess the quizz
                if not (await company_crud.user_has_role(current_user_id, result.company_id, RoleEnum.Admin) or
                await company_crud.user_has_role(current_user_id, result.company_id, RoleEnum.Owner)): 
                    logger.warning(f"Permission error: User \"{current_user_id}\" is not the admin / onwer in the company {result.company_id} related to the requested quizz")
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))
        return result 

    async def create_quizz(self, quizz_data: QuizzBaseSchema) -> Quizz:
        logger.debug(f"Received data:\nquizz_data -> {quizz_data}")
        new_quizz = await create_model_instance(self.db_session, Quizz, quizz_data)
        new_quizz.questions = []

        await self.db_session.commit()
 
        logger.debug(f"Successfully inserted new quizz instance into the database")
        return new_quizz
    
    async def update_quizz(self, quizz_id: int, quizz_data: QuizzUpdateSchema) -> Quizz:
        logger.debug(f"Received data:\nquizz_id -> {quizz_id}\nquizz_data -> {quizz_data}")
        updated_quizz = await update_model_instance(self.db_session, Quizz, quizz_id, quizz_data)

        logger.debug(f"Successfully updated quizz instance \"{quizz_id}\"")
        return updated_quizz

    async def delete_quizz(self, quizz_id: int) -> int:
        logger.debug(f"Received data:\nquizz_id -> \"{quizz_id}\"")
        result = await delete_model_instance(self.db_session, Quizz, quizz_id)

        logger.debug(f"Successfully deleted quizz \"{result}\" from the database")
        return result

    async def get_question_by_id(
              self, 
              question_id: int, 
              current_user_id: int, 
              admin_access_only: bool = False) -> Question:
        logger.debug(f"Received data:\nquestion_id -> {question_id}")
        query = await self.db_session.execute(
                      select(Question)
                      .where(Question.id == question_id))
        result = query.unique().scalar_one_or_none()
        
        if result:
            if admin_access_only:
                company_crud = CompanyRepository(self.db_session)

                # Validate if user has permission to acess the question
                if not (await company_crud.user_has_role(current_user_id, result.quizz.company_id, RoleEnum.Admin) or
                await company_crud.user_has_role(current_user_id, result.quizz.company_id, RoleEnum.Owner)): 
                    logger.warning(f"Permission error: User \"{current_user_id}\" is not the admin / onwer in the company {result.quizz.company_id} related to the requested question")
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))
        return result 

    async def create_question(self, question_data: QuestionBaseSchema) -> Question:
        logger.debug(f"Received data:\nquestion_data -> {question_data}")
        new_question = await create_model_instance(self.db_session, Question, question_data)
        new_question.answears = []

        await self.db_session.commit()
 
        logger.debug(f"Successfully inserted new question instance into the database")
        return new_question
    
    async def update_question(self, question_id: int, question_data: QuestionUpdateSchema) -> Question:
        logger.debug(f"Received data:\nquestion_id -> {question_id}\nquestion_data -> {question_data}")
        updated_answear = await update_model_instance(self.db_session, Question, question_id, question_data)

        logger.debug(f"Successfully updated question instance \"{question_id}\"")
        return updated_answear

    async def delete_question(self, question_id: int) -> int:
        logger.debug(f"Received data:\nquestion_id -> \"{question_id}\"")
        result = await delete_model_instance(self.db_session, Question, question_id)

        logger.debug(f"Successfully deleted question \"{result}\" from the database")
        return result

    async def get_answear_by_id(self, 
              answear_id: int, 
              current_user_id: int, 
              admin_access_only: bool = False) -> Answear:
        logger.debug(f"Received data:\nanswear_id -> {answear_id}")
        query = await self.db_session.execute(
                      select(Answear)
                      .where(Answear.id == answear_id))
        result = query.scalar_one_or_none()

        if result:
            if admin_access_only:
                company_crud = CompanyRepository(self.db_session)

                # Validate if user has permission to acess the answear
                if not (await company_crud.user_has_role(current_user_id, result.question.quizz.company_id, RoleEnum.Admin) or
                await company_crud.user_has_role(current_user_id, result.question.quizz.company_id, RoleEnum.Owner)): 
                    logger.warning(f"Permission error: User \"{current_user_id}\" is not the admin / onwer in the company {result.question.quizz.company_id} related to the requested question")
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail=error_handler("Forbidden"))
        return result 

    async def create_answear(self, answear_data: AnswearCreateSchema) -> Answear:
        logger.debug(f"Received data:\nanswear_data -> {answear_data}")
        new_answear = await create_model_instance(self.db_session, Answear, answear_data)
        
        await self.db_session.commit()
 
        logger.debug(f"Successfully inserted new answear instance into the database")
        return new_answear

    async def update_answear(self, answear_id: int, answear_data: AnswearUpdateSchema) -> Answear:
        logger.debug(f"Received data:\nanswear_id -> {answear_id}\nanswear_data -> {answear_data}")
        updated_answear = await update_model_instance(self.db_session, Answear, answear_id, answear_data)

        logger.debug(f"Successfully updated answear instance \"{answear_id}\"")
        return updated_answear

    async def delete_answear(self, answear_id: int) -> int:
        logger.debug(f"Received data:\nanswear_id -> \"{answear_id}\"")
        result = await delete_model_instance(self.db_session, Answear, answear_id)

        logger.debug(f"Successfully deleted answear \"{result}\" from the database")
        return result
