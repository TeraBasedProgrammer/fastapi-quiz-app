import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import (Any, AsyncGenerator, Awaitable, Callable, Dict, Generator,
                    Optional, TypeAlias)

import httpx
import pytest
from auth.handlers import AuthHandler
from py_dotenv import read_dotenv
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import joinedload

from app.companies.models import Company, CompanyUser, RoleEnum
from app.company_requests.models import CompanyRequest
from app.config import settings
from app.database import Base, get_async_session
from app.main import app
from app.quizzes.models import Answer, Question, Quiz
from app.users.models import User

# Activate venv
read_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))

Jwt: TypeAlias = str

DATABASE_URL: str = settings.test_database_url

DB_TABLES: Dict[str, Optional[str]] = {
    "users": "users_id_seq",
    "companies": "companies_id_seq",
    "company_user": None,
    "company_request": "company_request_id_seq",
    "quizzes": "quizzes_id_seq",
    "questions": "questions_id_seq",
    "answers": "answers_id_seq",
}

DEFAULT_USER_DATA = {
    "id": 1,
    "email": "test@email.com",
    "name": "ilya",
    "password": "password123"
}

DEFAULT_COMPANY_DATA = {
    "id": 1,
    "title": "MyCompany",
    "description": "Description",
    "is_hidden": False
}

DEFAULT_QUIZ_DATA = {
    "id": 1,
    "title": "Quiz",
    "description": "Description",
    "company_id": 1,
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


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, Any]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session', autouse=True)
async def prepare_database() -> None:
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
async def async_session_test() -> AsyncSession:
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield async_session


@pytest.fixture(scope="function", autouse=True)
async def clean_tables(async_session_test):
    """Clean data in all tables before running test function"""
    async with async_session_test() as session:
        async with session.begin():
            for table_for_cleaning, id_seq in DB_TABLES.items():
                await session.execute(text(f"DELETE FROM {table_for_cleaning};"))
                if id_seq:
                    await session.execute(text(f"ALTER SEQUENCE {id_seq} RESTART WITH 1;"))


async def _get_test_async_session() -> AsyncGenerator[AsyncSession, Any]:
    try:
        # create async engine for interaction with test database
        test_engine = create_async_engine(
            DATABASE_URL, future=True, echo=True
        )

        # create async session for the interaction with test database
        test_async_session = async_sessionmaker(
            test_engine, expire_on_commit=False, class_=AsyncSession
        )
        async with test_async_session() as session:
            yield session
    finally:
        pass


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[httpx.AsyncClient, Any]:
    app.dependency_overrides[get_async_session] = _get_test_async_session
    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def get_user_by_id(async_session_test) -> Callable[[str], Awaitable[list]]:
    async def get_user_by_id(user_id: str) -> list:
        async with async_session_test() as session:
            result = await session.execute(select(User).options(joinedload(User.companies)).where(User.id == user_id))
            user = result.unique().scalar_one_or_none()
            return [user] if user else []
    return get_user_by_id


@pytest.fixture(scope='function')
async def create_raw_user(async_session_test) -> Callable[[str, str, str], Awaitable[None]]:
    async def create_raw_user(email: str, name: str, password: str) -> None:
        auth = AuthHandler()
        hashed_password = await auth.get_password_hash(password)

        async with async_session_test() as session:
            user = User(
                email=email,
                password=hashed_password,
                name=name,
                registered_at=datetime.utcnow(),
                auth0_registered=False)
            session.add(user)
            await session.commit()

    return create_raw_user


@pytest.fixture(scope="function")
async def create_user_instance(create_raw_user) -> Callable[[str, str, str], Awaitable[dict[str, Any]]]:
    async def create_user_instance(email: str = DEFAULT_USER_DATA["email"],
                                   name: str = DEFAULT_USER_DATA["name"],
                                   password: str = DEFAULT_USER_DATA["password"]) -> dict[str, Any]:
        await create_raw_user(email=email, name=name, password=password)
        return {
            "email": email,
            "name": name,
            "password": password
        }

    return create_user_instance


@pytest.fixture(scope='function')
async def create_raw_company(async_session_test) -> Callable[[str, str, bool], Awaitable[None]]:
    async def create_raw_company(title: str, description: str, is_hidden: bool) -> None:
        async with async_session_test() as session:
            company = Company(
                title=title,
                description=description,
                is_hidden=is_hidden,
                created_at=datetime.utcnow())
            session.add(company)
            await session.commit()
    return create_raw_company


@pytest.fixture(scope="function")
async def create_company_instance(create_raw_company) -> Callable[[str, str, bool], Awaitable[dict[str, Any]]]:
    async def create_company_instance(title: str = DEFAULT_COMPANY_DATA["title"],
                                   description: str = DEFAULT_COMPANY_DATA["description"],
                                   is_hidden: bool = DEFAULT_COMPANY_DATA["is_hidden"]) -> dict[str, Any]:
        await create_raw_company(title=title, description=description, is_hidden=is_hidden)
        return {
            "title": title,
            "description": description,
            "is_hidden": is_hidden
        }

    return create_company_instance

@pytest.fixture(scope="function")
async def create_user_company_instance(async_session_test) -> Callable[[str, str, RoleEnum], Awaitable[None]]:
    async def create_user_company_instance(user_id: int = 1, company_id: int = 1, role = RoleEnum.Owner) -> None:
        async with async_session_test() as session:
            company_user = CompanyUser(
                company_id=company_id,
                user_id=user_id,
                role=role
            )
            session.add(company_user)
            await session.commit()
    return create_user_company_instance


@pytest.fixture(scope="function")
async def create_default_company_object(create_company_instance,
                                        create_user_instance,
                                        create_user_company_instance) -> Callable[[None], Awaitable[None]]:
    async def create_default_company_object() -> None:
        await create_company_instance()
        await create_user_instance()
        await create_user_company_instance()
    return create_default_company_object


@pytest.fixture(scope="function")
async def create_company_request_instance(async_session_test) -> Callable[[int, Optional[int], Optional[int]], Awaitable[CompanyRequest]]:
    async def create_company_request_instance(company_id: int, 
                                            sender_id: Optional[int] = None, 
                                            receiver_id: Optional[int] = None) -> CompanyRequest:
        async with async_session_test() as session:
            new_company_request = CompanyRequest(company_id=company_id, sender_id=sender_id, receiver_id=receiver_id)
            session.add(new_company_request)
            await session.commit()
            return new_company_request
    return create_company_request_instance


@pytest.fixture(scope="function")
async def get_request_by_id(async_session_test) -> Callable[[int], Awaitable[CompanyRequest]]:
    async def get_request_by_id(request_id: int) -> CompanyRequest:
        async with async_session_test() as session:
            request = await session.execute(select(CompanyRequest).where(CompanyRequest.id == request_id))
            return request.scalar_one_or_none()
    return get_request_by_id


@pytest.fixture(scope="function")
async def create_quiz_instance(async_session_test) -> Callable[[int], Awaitable[Quiz]]:
    async def create_quiz_instance(title: str = DEFAULT_QUIZ_DATA["title"], 
                                    description: str = DEFAULT_QUIZ_DATA["description"],
                                    company_id: int = DEFAULT_QUIZ_DATA["company_id"], 
                                    fully_created: bool = DEFAULT_QUIZ_DATA["fully_created"]) -> Quiz:
        async with async_session_test() as session:
            quiz = Quiz(title=title, 
                        description=description, 
                        company_id=company_id, 
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
async def get_quiz_by_id(async_session_test) -> Callable[[int], Awaitable[Quiz]]:
    async def get_quiz_by_id(quiz_id: int) -> Quiz:
        async with async_session_test() as session:
            result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
            question = result.unique().scalar_one_or_none()
            return question
    return get_quiz_by_id

@pytest.fixture(scope="function")
async def create_question_instance(async_session_test) -> Callable[[int], Awaitable[Question]]:
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
async def get_question_by_id(async_session_test) -> Callable[[str], Awaitable[Question]]:
    async def get_question_by_id(question_id: int) -> Question:
        async with async_session_test() as session:
            result = await session.execute(select(Question).where(Question.id == question_id))
            question = result.unique().scalar_one_or_none()
            return question
    return get_question_by_id

@pytest.fixture(scope="function")
async def create_answer_instance(async_session_test) -> Callable[[int], Awaitable[Answer]]:
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


@pytest.fixture(scope="function")
async def create_auth_jwt(async_session_test) -> Callable[[str], Awaitable[Jwt]]:
    async def create_auth_jwt(user_email: str) -> Jwt:
        async with async_session_test() as session:
            auth = AuthHandler()
            token = await auth.encode_token(user_email, session)
            return token

    return create_auth_jwt
