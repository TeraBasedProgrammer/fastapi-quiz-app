import json
from typing import Any, Callable

import httpx
import pytest
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.companies.models import RoleEnum
from app.quizzes.utils import set_question_status, set_quiz_status
from tests.fixtures.quiz_fixtures import (DEFAULT_ANSWER_DATA,
                                          DEFAULT_QUESTION_DATA,
                                          DEFAULT_QUIZ_DATA)
from tests.fixtures.user_fixtures import DEFAULT_USER_DATA


async def test_get_quiz_by_id(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    response = await client.get(
        "/quizzes/1/", headers={"Authorization": f"Bearer {token}"}
    )

    quiz_data = response.json()

    assert response.status_code == 200
    assert quiz_data["id"] == 1
    assert quiz_data["title"] == DEFAULT_QUIZ_DATA["title"]
    assert quiz_data["description"] == DEFAULT_QUIZ_DATA["description"]
    assert quiz_data["company_id"] == DEFAULT_QUIZ_DATA["company_id"]


async def test_get_quiz_by_id_404(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],) -> None:
    # Instanciate test objects
    await create_user_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    response = await client.get(
        "/quizzes/1/", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
        "is_member",
        (
            True,
            False, 
        )
)
async def test_get_quiz_by_id_403(
          is_member: bool,
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()
    
    # Non admin user
    not_admin_email = "notadmin@email.com"
    await create_user_instance(email=not_admin_email)

    if is_member:
        await create_user_company_instance(user_id=2, company_id=1, role=RoleEnum.Member)

    token = await create_auth_jwt(not_admin_email)
    response = await client.get(
        "/quizzes/1/", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "Forbidden"}}


async def test_create_quiz(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_company_object: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_company_object()
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])

    quiz_data = {
        "title": DEFAULT_QUIZ_DATA["title"],
        "description": DEFAULT_QUIZ_DATA["description"],
        "company_id": DEFAULT_QUIZ_DATA["company_id"],
        "completion_time": DEFAULT_QUIZ_DATA["completion_time"]
    }
    server_response = await client.post("/quizzes/", data=json.dumps(quiz_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200
    quiz_data = server_response.json()

    assert quiz_data["id"] == 1
    assert quiz_data["title"] == quiz_data["title"]
    assert quiz_data["description"] == quiz_data["description"]
    assert quiz_data["company_id"] == quiz_data["company_id"]
    assert quiz_data["completion_time"] == quiz_data["completion_time"]


@pytest.mark.parametrize(
    "request_sender, quiz_data, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            {"title": "Quiz?", "description": "Quiz", "company_id": 1, "completion_time": 15},
            400,
            {"detail": "Title may contain only english letters, numbers and special characters (.-'!()/ )"}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            {},
            422,
            {
                "detail": 
                [
                    {
                        "input": {},
                        "loc": ["body","title"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    },
                    {
                        "input": {},
                        "loc": ["body", "description"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    },
                    {
                        "input": {},
                        "loc": ["body","company_id"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    },
                    {
                        "input": {},
                        "loc": ["body","completion_time"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    }
                ],
            }
        ), 
        (
            DEFAULT_USER_DATA["email"],
            {"title": "Quiz", "description": "Quiz", "company_id": 150, "completion_time": 15},
            404,
            {"detail": {"error": "Company with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            {"title": "Quiz", "description": "Quiz", "company_id": 1, "completion_time": 15},
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
    )
)
async def test_create_quiz_error(
          status_code: int,
          request_sender: EmailStr,
          client: httpx.AsyncClient,
          response: dict[str, Any],
          quiz_data: dict[str, Any],
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_company_object()
    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.post("/quizzes/", data=json.dumps(quiz_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


@pytest.mark.parametrize(
        "same_company, status_code",
        (
            (True, 400),
            (False, 200),
        )
)
async def test_create_duplicate_quiz(
          status_code: int,
          same_company: bool,
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()

    if not same_company:
        await create_company_instance(title="Another company")
        await create_user_company_instance(company_id=2)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    company_id = DEFAULT_QUIZ_DATA["company_id"] if same_company else 2 
    quiz_data = {
        "title": DEFAULT_QUIZ_DATA["title"],
        "description": DEFAULT_QUIZ_DATA["description"],
        "company_id": company_id,
        "completion_time": DEFAULT_QUIZ_DATA["completion_time"]
    }
    server_response = await client.post("/quizzes/", data=json.dumps(quiz_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code


async def test_create_question(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    question_data = {
        "title": DEFAULT_QUESTION_DATA["title"],
        "quiz_id": DEFAULT_QUESTION_DATA["quiz_id"]
    }

    server_response = await client.post("/quizzes/questions/", data=json.dumps(question_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200

    response_data = server_response.json()
    assert response_data["id"] == DEFAULT_QUESTION_DATA["id"]
    assert response_data["title"] == DEFAULT_QUESTION_DATA["title"]
    assert response_data["quiz_id"] == DEFAULT_QUESTION_DATA["quiz_id"]


@pytest.mark.parametrize(
    "request_sender, question_data, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            {"title": "Question?", "quiz_id": 1},
            400,
            {"detail": "Title may contain only english letters, numbers and special characters (.-'!()/ )"}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            {},
            422,
            {
                "detail": 
                [
                    {
                        "input": {},
                        "loc": ["body","title"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    },
                    {
                        "input": {},
                        "loc": ["body", "quiz_id"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    },
                ],
            }
        ), 
        (
            DEFAULT_USER_DATA["email"],
            {"title": "Question", "quiz_id": 150},
            404,
            {"detail": {"error": "Quiz with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            {"title": "Question", "quiz_id": 1},
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
    )
)
async def test_create_question_error(
          status_code: int,
          response: dict[str, Any],
          request_sender: EmailStr,
          question_data: dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()
    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.post("/quizzes/questions/", data=json.dumps(question_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


@pytest.mark.parametrize(
        "same_quiz, status_code",
        (
            (True, 400),
            (False, 200),
        )
)
async def test_create_duplicate_question(
          status_code: int,
          same_quiz: bool,
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_quiz_instance: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()
    if not same_quiz:
        await create_quiz_instance(title="Another quiz")
    quiz_id = DEFAULT_QUESTION_DATA["quiz_id"] if same_quiz else 2 

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     
    question_data = {
        "title": DEFAULT_QUESTION_DATA["title"],
        "quiz_id": quiz_id
    }
    server_response = await client.post("/quizzes/questions/", data=json.dumps(question_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code


async def test_create_answer(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    answer_data = {
        "title": DEFAULT_ANSWER_DATA["title"],
        "question_id": DEFAULT_ANSWER_DATA["question_id"],
        "is_correct": DEFAULT_ANSWER_DATA["is_correct"]
    }

    server_response = await client.post("/quizzes/answers/", data=json.dumps(answer_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200

    response_data = server_response.json()
    assert response_data["id"] == DEFAULT_ANSWER_DATA["id"]
    assert response_data["title"] == DEFAULT_ANSWER_DATA["title"]
    assert response_data["question_id"] == DEFAULT_ANSWER_DATA["question_id"]


@pytest.mark.parametrize(
    "request_sender, answer_data, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            {"title": "Answer?", "question_id": 1, "is_correct": False},
            400,
            {"detail": "Title may contain only english letters, numbers and special characters (.-'!()/ )"}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            {},
            422,
            {
                "detail": 
                [
                    {
                        "input": {},
                        "loc": ["body","title"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    },
                    {
                        "input": {},
                        "loc": ["body", "question_id"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    },
                    {
                        "input": {},
                        "loc": ["body", "is_correct"],
                        "msg": "Field required",
                        "type": "missing",
                        "url": "https://errors.pydantic.dev/2.1.2/v/missing"
                    },
                ],
            }
        ), 
        (
            DEFAULT_USER_DATA["email"],
            {"title": "Answer", "question_id": 150, "is_correct": False},
            404,
            {"detail": {"error": "Question with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            {"title": "Answer", "question_id": 1, "is_correct": False},
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
    )
)
async def test_create_answer_error(
          status_code: int,
          response: dict[str, Any],
          request_sender: EmailStr,
          answer_data: dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()
    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.post("/quizzes/answers/", data=json.dumps(answer_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


@pytest.mark.parametrize(
        "same_question, status_code",
        (
            (True, 400),
            (False, 200),
        )
)
async def test_create_duplicate_answer(
          status_code: int,
          same_question: bool,
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_question_instance: Callable[..., Any],
          create_default_answer_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_answer_instance()

    if not same_question:
        await create_question_instance(title="Another question")

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    question_id = DEFAULT_ANSWER_DATA["question_id"] if same_question else 2 
    answer_data = {
        "title": DEFAULT_ANSWER_DATA["title"],
        "question_id": question_id,
        "is_correct": DEFAULT_ANSWER_DATA["is_correct"],
    }
    server_response = await client.post("/quizzes/answers/", data=json.dumps(answer_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code


async def test_update_quiz(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()
    
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])

    quiz_data = {
        "title": "New quiz title",
        "description": "New quiz description",
    }
    server_response = await client.patch("/quizzes/1/update/", data=json.dumps(quiz_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200
    quiz_data = server_response.json()

    assert quiz_data["id"] == 1
    assert quiz_data["title"] == quiz_data["title"]
    assert quiz_data["description"] == quiz_data["description"]
    assert quiz_data["company_id"] == DEFAULT_QUIZ_DATA["company_id"]


@pytest.mark.parametrize(
    "request_sender, quiz_id, quiz_data, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            DEFAULT_QUIZ_DATA["id"],
            {"title": "New quiz title?"},
            400,
            {"detail": "Title may contain only english letters, numbers and special characters (.-'!()/ )"}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            150,
            {"title": "New quiz title"},
            404,
            {"detail": {"error": "Quiz with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            DEFAULT_QUIZ_DATA["id"],
            {"title": "New quiz title"},
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            DEFAULT_QUIZ_DATA["id"],
            {},
            400,
            {"detail": {"error": "At least one valid parameter (title, description) should be provided for quiz update"}}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            DEFAULT_QUIZ_DATA["id"],
            {"something": "inappropriate", "gg": "wp"},
            400,
            {"detail": {"error": "At least one valid parameter (title, description) should be provided for quiz update"}}
        ), 
    )
)
async def test_update_quiz_error(
          quiz_id: int,
          status_code: int,
          request_sender: EmailStr,
          client: httpx.AsyncClient,
          response: dict[str, Any],
          quiz_data: dict[str, Any],
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()
    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.patch(f"/quizzes/{quiz_id}/update/", data=json.dumps(quiz_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_update_duplicate_quiz(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_quiz_instance: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()

    # Create new quiz
    await create_quiz_instance(title="Another quiz")

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    quiz_data = {
        "title": DEFAULT_QUIZ_DATA["title"],
    }
    server_response = await client.patch("/quizzes/2/update/", data=json.dumps(quiz_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 400


async def test_update_question(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    question_data = {
        "title": "New question title"
    }

    server_response = await client.patch("/quizzes/questions/1/update/", data=json.dumps(question_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200

    response_data = server_response.json()
    assert response_data["id"] == DEFAULT_QUESTION_DATA["id"]
    assert response_data["title"] == question_data["title"]
    assert response_data["quiz_id"] == DEFAULT_QUESTION_DATA["quiz_id"]


@pytest.mark.parametrize(
    "request_sender, question_id, question_data, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            DEFAULT_QUESTION_DATA["id"],
            {"title": "New question title?"},
            400,
            {"detail": "Title may contain only english letters, numbers and special characters (.-'!()/ )"}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            150,
            {"title": "New question title"},
            404,
            {"detail": {"error": "Question with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            DEFAULT_QUESTION_DATA["id"],
            {"title": "New question title"},
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            DEFAULT_QUESTION_DATA["id"],
            {},
            400,
            {"detail": {"error": "At least one valid parameter (title) should be provided for question update"}}
        ), 
        (
            DEFAULT_USER_DATA["email"],
           
            DEFAULT_QUESTION_DATA["id"],
            {"something": "inappropriate", "gg": "wp"},
            400,
            {"detail": {"error": "At least one valid parameter (title) should be provided for question update"}}
        ), 
    )
)
async def test_update_question_error(
          question_id: int,
          status_code: int,
          response: dict[str, Any],
          request_sender: EmailStr,
          question_data: dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()

    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.patch(f"/quizzes/questions/{question_id}/update/", data=json.dumps(question_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_update_duplicate_question(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_question_instance: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()

    # Create new question
    await create_question_instance(title="Another question")

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    question_data = {
        "title": DEFAULT_QUESTION_DATA["title"],
    }
    server_response = await client.patch("/quizzes/questions/2/update/", data=json.dumps(question_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 400


async def test_update_answer(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_answer_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_answer_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    answer_data = {
        "title": "New answer title",
        "is_correct": True,
    }

    server_response = await client.patch("/quizzes/answers/1/update/", data=json.dumps(answer_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200

    response_data = server_response.json()
    assert response_data["id"] == DEFAULT_ANSWER_DATA["id"]
    assert response_data["title"] == answer_data["title"]
    assert response_data["is_correct"] == answer_data["is_correct"]


@pytest.mark.parametrize(
    "request_sender, answer_id, question_data, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            DEFAULT_ANSWER_DATA["id"],
            {"title": "New answer title?", "is_correct": True},
            400,
            {"detail": "Title may contain only english letters, numbers and special characters (.-'!()/ )"}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            DEFAULT_ANSWER_DATA["id"],
            {"title": "New answer title", "is_correct": "Not a boolean"},
            422,
            {
                'detail': 
                [
                    {
                        'input': 'Not a boolean',
                        'loc': ['body','is_correct'],
                        'msg': 'Input should be a valid boolean, unable to interpret '
                        'input',
                        'type': 'bool_parsing',
                        'url': 'https://errors.pydantic.dev/2.1.2/v/bool_parsing'
                    }
                ],
           }
        ), 
        (
            DEFAULT_USER_DATA["email"],
            150,
            {"title": "New answer title", "is_correct": True},
            404,
            {"detail": {"error": "Answer with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            DEFAULT_ANSWER_DATA["id"],
            {"title": "New answer title", "is_correct": True},
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
        (
            DEFAULT_USER_DATA["email"],
            DEFAULT_QUESTION_DATA["id"],
            {},
            400,
            {"detail": {"error": "At least one valid parameter (title, is_correct) should be provided for answer update"}}
        ), 
        (
            DEFAULT_USER_DATA["email"],
           
            DEFAULT_QUESTION_DATA["id"],
            {"something": "inappropriate", "gg": "wp"},
            400,
            {"detail": {"error": "At least one valid parameter (title, is_correct) should be provided for answer update"}}
        ), 
    )
)
async def test_update_answer_error(
          answer_id: int,
          status_code: int,
          response: dict[str, Any],
          request_sender: EmailStr,
          question_data: dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_answer_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_answer_instance()

    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.patch(f"/quizzes/answers/{answer_id}/update/", data=json.dumps(question_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_update_answer_to_incorrect(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_answer_instance: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()
    await create_answer_instance(is_correct=True)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    server_response = await client.patch(f"/quizzes/answers/1/update/", data=json.dumps({"is_correct": False}), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 400
    assert server_response.json() == {'detail': {'error': "You can't unset a correct answer directly. Instead mark another answer as correct"}}


async def test_update_duplicate_answer(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_answer_instance: Callable[..., Any],
          create_default_answer_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_answer_instance()

    # Create new question
    await create_answer_instance(title="Another answer")

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    question_data = {
        "title": DEFAULT_ANSWER_DATA["title"],
    }
    server_response = await client.patch("/quizzes/answers/2/update/", data=json.dumps(question_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 400


async def test_delete_quiz(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    server_response = await client.delete("/quizzes/1/delete/", headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200


@pytest.mark.parametrize(
    "request_sender, quiz_id, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            150,
            404,
            {"detail": {"error": "Quiz with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            DEFAULT_QUIZ_DATA["id"],
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
    )
)
async def test_delete_quiz_error(
          quiz_id: int, 
          status_code: int,
          request_sender: EmailStr,
          client: httpx.AsyncClient,
          response: dict[str, Any],
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_quiz_instance()
    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.delete(f"/quizzes/{quiz_id}/delete/", headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_delete_question(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    server_response = await client.delete("/quizzes/questions/1/delete/", headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200


@pytest.mark.parametrize(
    "request_sender, question_id, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            150,
            404,
            {"detail": {"error": "Question with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            DEFAULT_QUESTION_DATA["id"],
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
    )
)
async def test_delete_question_error(
          question_id: int, 
          status_code: int,
          request_sender: EmailStr,
          client: httpx.AsyncClient,
          response: dict[str, Any],
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()
    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.delete(f"/quizzes/questions/{question_id}/delete/", headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_delete_answer(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_default_answer_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_answer_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    server_response = await client.delete("/quizzes/answers/1/delete/", headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 200


@pytest.mark.parametrize(
    "request_sender, answer_id, status_code, response",
    (
        (
            DEFAULT_USER_DATA["email"],
            150,
            404,
            {"detail": {"error": "Answer with id 150 is not found"}}
        ), 
        (
            "not_admin@example.com",
            DEFAULT_QUESTION_DATA["id"],
            403,
            {"detail": {"error": "Forbidden"}}
        ), 
    )
)
async def test_delete_answer_error(
          answer_id: int, 
          status_code: int,
          request_sender: EmailStr,
          client: httpx.AsyncClient,
          response: dict[str, Any],
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_answer_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_answer_instance()
    if request_sender != DEFAULT_USER_DATA["email"]:
        await create_user_instance(request_sender)

    token = await create_auth_jwt(request_sender)     

    server_response = await client.delete(f"/quizzes/answers/{answer_id}/delete/", headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_delete_correct_answer(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_answer_instance: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    await create_default_question_instance()
    await create_answer_instance(is_correct=True)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    server_response = await client.delete(f"/quizzes/answers/1/delete/", headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 400
    assert server_response.json() == {'detail': {'error': "You can't delete a correct answer"}}     
    

@pytest.mark.parametrize(
        "with_answers, has_correct_answer, updated_fully_created",
        (
            (True, True, True),
            (True, False, False),
            (False, False, False)
        )
)
async def test_set_question_status(
          with_answers: bool,
          has_correct_answer: bool,
          updated_fully_created: bool,
          async_session_test: AsyncSession,
          get_question_by_id: Callable[..., Any], 
          create_answer_instance: Callable[..., Any],
          create_default_question_instance: Callable[..., Any]) -> None:
    question = await create_default_question_instance()

    if with_answers:
        await create_answer_instance()
        is_correct = True if has_correct_answer else False
        await create_answer_instance(title="Second answer", is_correct=is_correct)

    async with async_session_test() as session:
        await set_question_status(session=session, question_id=question.id)

    updated_question = await get_question_by_id(question_id=DEFAULT_QUESTION_DATA["id"])
    assert updated_question.fully_created == updated_fully_created 


@pytest.mark.parametrize(
        "with_questions, questions_are_fully_created, updated_fully_created",
        (
            (True, True, True),
            (True, False, False),
            (False, False, False),
        )
)
async def test_set_quiz_status(
          with_questions: bool,
          updated_fully_created: bool,
          async_session_test: AsyncSession,
          questions_are_fully_created: bool,
          get_quiz_by_id: Callable[..., Any], 
          create_question_instance: Callable[..., Any],
          create_default_quiz_instance: Callable[..., Any]) -> None:
    quiz = await create_default_quiz_instance()

    if with_questions:
        fully_created = True if questions_are_fully_created else False
        await create_question_instance(fully_created=fully_created)
        await create_question_instance(title="Second question", fully_created=fully_created)

    async with async_session_test() as session:
        await set_quiz_status(session=session, quiz_id=quiz.id)

    updated_quiz = await get_quiz_by_id(quiz_id=DEFAULT_QUIZ_DATA["id"])
    assert updated_quiz.fully_created == updated_fully_created 
