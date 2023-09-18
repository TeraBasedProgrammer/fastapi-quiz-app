from typing import Any, Awaitable, Callable

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.quizzes.models import Answer, Question, Quiz

DEFAULT_QUIZ_DATA = {
    "id": 1,
    "title": "Quiz",
    "description": "Description",
    "company_id": 1,
    "completion_time": 15,
    "fully_created": False
}

DEFAULT_QUESTION_DATA = {
    "id": 1,
    "title": "Question",
    "quiz_id": 1,
    "fully_created": False
}

DEFAULT_ANSWER_DATA = {
    "id": 1,
    "title": "Answer",
    "question_id": 1,
    "is_correct": False
}


@pytest.fixture(scope="function")
async def create_quiz_instance(async_session_test: AsyncSession) -> Callable[[int], Awaitable[Quiz]]:
    async def create_quiz_instance(title: str = DEFAULT_QUIZ_DATA["title"], 
                                    description: str = DEFAULT_QUIZ_DATA["description"],
                                    company_id: int = DEFAULT_QUIZ_DATA["company_id"], 
                                    completion_time: int = DEFAULT_QUIZ_DATA["completion_time"], 
                                    fully_created: bool = DEFAULT_QUIZ_DATA["fully_created"]) -> Quiz:
        async with async_session_test() as session:
            quiz = Quiz(title=title, 
                        description=description, 
                        company_id=company_id, 
                        completion_time=completion_time,
                        fully_created=fully_created)
            session.add(quiz)
            await session.commit()
            return quiz

    return create_quiz_instance


@pytest.fixture
async def create_default_quiz_instance(
          create_default_company_object,
          create_quiz_instance)-> Callable[[int], Awaitable[Quiz]]:
    async def create_default_quiz_instance() -> Quiz:
        await create_default_company_object()
        quiz = await create_quiz_instance()
        return quiz
    return create_default_quiz_instance

@pytest.fixture
async def get_quiz_by_id(async_session_test: AsyncSession) -> Callable[[int], Awaitable[Quiz]]:
    async def get_quiz_by_id(quiz_id: int) -> Quiz:
        async with async_session_test() as session:
            result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
            question = result.unique().scalar_one_or_none()
            return question
    return get_quiz_by_id

@pytest.fixture(scope="function")
async def create_question_instance(async_session_test: AsyncSession) -> Callable[[int], Awaitable[Question]]:
    async def create_question_instance(title: str = DEFAULT_QUESTION_DATA["title"], 
                                       quiz_id: int = DEFAULT_QUESTION_DATA["quiz_id"], 
                                       fully_created: bool = DEFAULT_QUESTION_DATA["fully_created"]) -> Question:
        async with async_session_test() as session:
            question = Question(title=title, 
                               quiz_id=quiz_id,
                               fully_created=fully_created)
            session.add(question)
            await session.commit()
            return question

    return create_question_instance


@pytest.fixture 
async def create_default_question_instance(
          create_default_quiz_instance,
          create_question_instance) -> Callable[[int], Awaitable[Question]]:
    async def create_default_question_instance() -> Question:
        await create_default_quiz_instance()
        question = await create_question_instance()
        return question
    return create_default_question_instance

@pytest.fixture
async def get_question_by_id(async_session_test: AsyncSession) -> Callable[[str], Awaitable[Question]]:
    async def get_question_by_id(question_id: int) -> Question:
        async with async_session_test() as session:
            result = await session.execute(select(Question).where(Question.id == question_id))
            question = result.unique().scalar_one_or_none()
            return question
    return get_question_by_id


@pytest.fixture(scope="function")
async def create_answer_instance(async_session_test: AsyncSession) -> Callable[[int], Awaitable[Answer]]:
    async def create_answer_instance(title: str = DEFAULT_ANSWER_DATA["title"], 
                                     question_id: int = DEFAULT_ANSWER_DATA["question_id"], 
                                     is_correct: bool = DEFAULT_ANSWER_DATA["is_correct"]) -> Answer:
        async with async_session_test() as session:
            answer = Answer(title=title, 
                            question_id=question_id,
                            is_correct=is_correct)
            session.add(answer)
            await session.commit()
            return answer

    return create_answer_instance


@pytest.fixture 
async def create_default_answer_instance(
          create_default_question_instance,
          create_answer_instance) -> Callable[[int], Awaitable[Question]]:
    async def create_default_answer_instance() -> Question:
        await create_default_question_instance()
        answer = await create_answer_instance()
        return answer
    return create_default_answer_instance
