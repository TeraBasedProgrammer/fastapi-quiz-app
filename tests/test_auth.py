import json
from datetime import datetime
from typing import Awaitable, Any

import httpx
import pytest

from app.auth.handlers import AuthHandler


# Signup
@pytest.mark.parametrize(
        "user_data",
        (
            {"email": "test@email.com", "name": "ilya", "password": "password123"},
            {"email": "test@email.com", "password": "password123"}
        )
)
async def test_signup(client: httpx.AsyncClient, user_data: dict[str, Any], get_user_by_id: Awaitable[list]) -> None:
    auth = AuthHandler()
    response = await client.post("/signup", data=json.dumps(user_data))
    assert response.status_code == 201
    
    # Check if user was inserted into the database
    db_response = await get_user_by_id(1)
    assert len(db_response) == 1
    user_from_db = dict(db_response[0])

    assert user_from_db["email"] == user_data["email"]
    assert user_from_db["id"] == 1
    assert user_from_db["name"] == user_data.get("name")
    assert user_from_db["registered_at"].date() == datetime.utcnow().date()
    assert auth.verify_password(user_data["password"], user_from_db["password"]) == True
    

    data = response.json()
    assert data["email"] == user_data["email"]
    assert data.get("name") == user_data.get("name")
    assert data["id"] == 1
    assert data.get("password") == None
    assert data["registered_at"].split("T")[0] == str(datetime.utcnow().date())

@pytest.mark.parametrize(      
    "user_data, error_message, status_code",
    (
        (
            {"email": "testemail.com", "name": "ilya", "password": "password123"},
            {
            "detail": [
                {
                "type": "value_error",
                "loc": [
                    "body",
                    "email"
                ],
                "msg": "value is not a valid email address: The email address is not valid. It must have exactly one @-sign.",
                "input": "testemail.com",
                "ctx": {
                    "reason": "The email address is not valid. It must have exactly one @-sign."
                }
                }
            ]
            },
            422
        ),
        (
            {"email": "test@email.com", "name": "ilya123", "password": "password123"},
            {
                "detail": "Name should contain only english letters"
            },
            400
        ),
        (
            {"email": "test@email.com", "name": "ilya", "password": "short1"},
            {
                "detail": "Password should contain at least eight characters, at least one letter and one number"
            },
            400
        ),
        (
            {"email": "test@email.com", "name": "ilya", "password": "doesnthavenumbers"},
            {
                "detail": "Password should contain at least eight characters, at least one letter and one number"
            }, 
            400
        )
    )
)
async def test_signup_validation_error(
    client: httpx.AsyncClient, 
    user_data: dict[str, Any], 
    error_message: dict[str | Any], 
    status_code: int
    ) -> None: 
    response = await client.post("/signup", data=json.dumps(user_data))
    assert response.status_code == status_code
    
    data = response.json()
    assert data == error_message


async def test_signup_duplicate(client: httpx.AsyncClient, create_raw_user: Awaitable[None]) -> None:
    user_data = {
        "email": "test@email.com", 
        "name": "ilya",
        "password": "password123"
    }

    await create_raw_user(**user_data)

    duplicate_response = await client.post("/signup", data=json.dumps(user_data))
    assert duplicate_response.status_code == 400
    assert duplicate_response.json() == {"detail": {"error": "User with this email already exists"}}


# Login
async def test_login(client:httpx.AsyncClient, create_raw_user: Awaitable[None]):
    await create_raw_user()
    creds = {
        "email": "test@email.com",
        "password": "password123"
    }

    response = await client.post("/login", data=json.dumps(creds))
    assert response.status_code == 200
    assert response.json().get("token") != None


@pytest.mark.parametrize(
    "user_data, error_response",
    (
        (
            {"email": "not_registered@gmail,com", "password": "password123"},
            {"detail": {"error": "User with this email is not registered in the system"}}
        ),
        (
            {"email": "test@email.com", "password": "definitelyincorrectpassword123"},
            {"detail": {"error": "Invalid password"}}
        )
    )
)
async def test_login_validation_error(
    client:httpx.AsyncClient, 
    create_raw_user: Awaitable[None],
    user_data: dict[str, Any],
    error_response: dict[str, str]):
    await create_raw_user()

    response = await client.post("/login", data=json.dumps(user_data))
    assert response.status_code == 400
    assert response.json() == error_response