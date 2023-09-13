import logging
from typing import List, Optional

from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.companies.models import RoleEnum
from app.companies.services import CompanyRepository
from app.users.services import error_handler
from app.utils import (create_model_instance, delete_model_instance,
                       update_model_instance)

from .models import Answer, Question, Quiz
from .schemas import (AnswerCreateSchema, AnswerUpdateSchema,
                      QuestionBaseSchema, QuestionUpdateSchema, QuizBaseSchema,
                      QuizUpdateSchema)

logger = logging.getLogger("main_logger")


class QuizRepository:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def get_company_quizzes(self, company_id) -> List[Quiz]:
        query = await self.db_session.execute(
                      select(Quiz)
                      .where(Quiz.company_id == company_id))
        result = query.unique().scalars().all()
        return result 
    
    async def get_quiz_by_id(
              self, 
              quiz_id: int,
              current_user_id: int,
              member_access_only: bool = False,
              admin_access_only: bool = False) -> Optional[Quiz]:
        logger.debug(f"Received data:\nquiz_id -> {quiz_id}")
        query = await self.db_session.execute(
                      select(Quiz)
                      .outerjoin(Question, Question.quiz_id == Quiz.id)
                      .outerjoin(Answer, Answer.question_id == Question.id)
                      .where(Quiz.id == quiz_id))
        result = query.unique().scalar_one_or_none()

        if result:
            if member_access_only:
                company_crud = CompanyRepository(self.db_session)
                await company_crud.get_company_by_id(result.company_id, current_user_id, member_only=True)
                
            if admin_access_only:
                company_crud = CompanyRepository(self.db_session)
                await company_crud.get_company_by_id(result.company_id, current_user_id, admin_only=True)
                
        return result 

    async def create_quiz(self, quiz_data: QuizBaseSchema) -> Quiz:
        logger.debug(f"Received data:\nquiz_data -> {quiz_data}")
        new_quiz = await create_model_instance(self.db_session, Quiz, quiz_data)
        new_quiz.questions = []

        await self.db_session.commit()
 
        logger.debug(f"Successfully inserted new quiz instance into the database")
        return new_quiz
    
    async def update_quiz(self, quiz_id: int, quiz_data: QuizUpdateSchema) -> Quiz:
        logger.debug(f"Received data:\nquiz_id -> {quiz_id}\nquiz_data -> {quiz_data}")
        updated_quiz = await update_model_instance(self.db_session, Quiz, quiz_id, quiz_data)

        logger.debug(f"Successfully updated quiz instance \"{quiz_id}\"")
        return updated_quiz

    async def delete_quiz(self, quiz_id: int) -> int:
        logger.debug(f"Received data:\nquiz_id -> \"{quiz_id}\"")
        result = await delete_model_instance(self.db_session, Quiz, quiz_id)

        logger.debug(f"Successfully deleted quiz \"{result}\" from the database")
        return result

    async def get_question_by_id(
              self, 
              question_id: int, 
              current_user_id: int, 
              admin_access_only: bool = False,
              member_access_only: bool = False) -> Question:
        logger.debug(f"Received data:\nquestion_id -> {question_id}")
        query = await self.db_session.execute(
                      select(Question)
                      .where(Question.id == question_id))
        result = query.unique().scalar_one_or_none()
        
        if result:
            if member_access_only:
                company_crud = CompanyRepository(self.db_session)
                await company_crud.get_company_by_id(result.quiz.company_id, current_user_id, member_only=True)
                
            if admin_access_only:
                company_crud = CompanyRepository(self.db_session)
                await company_crud.get_company_by_id(result.quiz.company_id, current_user_id, admin_only=True)
                
        return result 

    async def create_question(self, question_data: QuestionBaseSchema) -> Question:
        logger.debug(f"Received data:\nquestion_data -> {question_data}")
        new_question = await create_model_instance(self.db_session, Question, question_data)
        new_question.answers = []

        await self.db_session.commit()
 
        logger.debug(f"Successfully inserted new question instance into the database")
        return new_question
    
    async def update_question(self, question_id: int, question_data: QuestionUpdateSchema) -> Question:
        logger.debug(f"Received data:\nquestion_id -> {question_id}\nquestion_data -> {question_data}")
        updated_answer = await update_model_instance(self.db_session, Question, question_id, question_data)

        logger.debug(f"Successfully updated question instance \"{question_id}\"")
        return updated_answer

    async def delete_question(self, question_id: int) -> int:
        logger.debug(f"Received data:\nquestion_id -> \"{question_id}\"")
        result = await delete_model_instance(self.db_session, Question, question_id)

        logger.debug(f"Successfully deleted question \"{result}\" from the database")
        return result

    async def get_answer_by_id(self, 
              answer_id: int, 
              current_user_id: int, 
              admin_access_only: bool = False,
              member_access_only: bool = False) -> Answer:
        logger.debug(f"Received data:\nanswer_id -> {answer_id}")
        query = await self.db_session.execute(
                      select(Answer)
                      .where(Answer.id == answer_id))
        result = query.unique().scalar_one_or_none()

        if result:
            if member_access_only:
                company_crud = CompanyRepository(self.db_session)
                await company_crud.get_company_by_id(result.question.quiz.company_id, current_user_id, member_only=True)
                
            if admin_access_only:
                company_crud = CompanyRepository(self.db_session)
                await company_crud.get_company_by_id(result.question.quiz.company_id, current_user_id, admin_only=True)

        return result 

    async def create_answer(self, answer_data: AnswerCreateSchema) -> Answer:
        logger.debug(f"Received data:\nanswer_data -> {answer_data}")
        new_answer = await create_model_instance(self.db_session, Answer, answer_data)
        
        await self.db_session.commit()
 
        logger.debug(f"Successfully inserted new answer instance into the database")
        return new_answer

    async def update_answer(self, answer_id: int, answer_data: AnswerUpdateSchema) -> Answer:
        logger.debug(f"Received data:\nanswer_id -> {answer_id}\nanswer_data -> {answer_data}")
        updated_answer = await update_model_instance(self.db_session, Answer, answer_id, answer_data)

        logger.debug(f"Successfully updated answer instance \"{answer_id}\"")
        return updated_answer

    async def delete_answer(self, answer_id: int) -> int:
        logger.debug(f"Received data:\nanswer_id -> \"{answer_id}\"")
        result = await delete_model_instance(self.db_session, Answer, answer_id)

        logger.debug(f"Successfully deleted answer \"{result}\" from the database")
        return result

    async def unset_correct_answer(self, question: Question) -> None:
        for answer in question.answers:
            if answer.is_correct:
                await update_model_instance(self.db_session, Answer, answer.id, AnswerUpdateSchema(is_correct=False))
                logger.info(f"Successfully made previous correct answer incorrect for the question \"{question.id}\"")
