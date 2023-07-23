from datetime import datetime
from typing import Awaitable, Any

import httpx
import pytest



# Get all users
async def test_get_users_empty(client: httpx.AsyncClient) -> None:
    response = await client.get("/users/")
    assert response.status_code == 200
    assert response.json() == {"items":[],"total":0,"page":1,"size":50,"pages":0}


async def test_get_users(client: httpx.AsyncClient, create_raw_user: Awaitable[None]) -> None:
    # Instanciate user in the DB
    user_data = {
        "email": "test@email.com",
        "name": "ilya",
        "password": "password123",
    }

    await create_raw_user(**user_data)    

    response = await client.get("/users/")
    json_response = response.json()

    assert response.status_code == 200
    assert json_response.get("items") != None
    assert json_response["total"] == 1

    data = json_response["items"][0]
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["id"] == 1
    assert data.get("password") == None
    assert data["registered_at"].split("T")[0] == str(datetime.utcnow().date())


@pytest.mark.parametrize(
    "page, size, items_is_not_empty, total_expected, pages_expected",
    [ 
        (
            1, 10, False, 2, 1
        ),
        (
            1, 1, False, 2, 2
        ),
        (
            3, 10, True, 2, 1 
        )
    ],
)
async def test_get_users_paginated(
    client: httpx.AsyncClient, 
    create_raw_user: Awaitable[None],
    page: int,
    size: int,
    items_is_not_empty: bool,
    total_expected: int, 
    pages_expected: int,
    ) -> None:
    user1_data = {
        "email": "test@email.com",
        "name": "ilya",
        "password": "password123",
    }

    user2_data = {
        "email": "test2@email.com",
        "name": "anton",
        "password": "password123",
    }


    # Instanciate a user in the DB
    await create_raw_user(**user1_data)
    await create_raw_user(**user2_data)

    response = await client.get(f"/users/?page={page}&size={size}")
    json_response = response.json()

    assert response.status_code == 200
    assert bool(json_response.get("items")) != items_is_not_empty
    assert json_response["total"] == total_expected
    assert json_response["pages"] == pages_expected
    assert json_response["size"] == size    

# Get single user
async def test_get_user_by_id(client: httpx.AsyncClient, create_raw_user: Awaitable[None]) -> None:
    user_data = {
        "email": "test@email.com",
        "name": "ilya",
        "password": "password123",
    }

    # Instanciate a user in the DB
    await create_raw_user(**user_data)

    response = await client.get("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["id"] == 1
    assert data.get("password") == None
    assert data["registered_at"].split("T")[0] == str(datetime.utcnow().date())

@pytest.mark.parametrize(
    "user_id, status_code, error_response",
    (
        (
            "definitely-not-an-integer", 
            422,
            {"detail": 
                [
                    {
                        "type":"int_parsing",
                        "loc":["path","user_id"],
                        "msg":"Input should be a valid integer, unable to parse string as an integer",
                        "input":"definitely-not-an-integer","url":"https://errors.pydantic.dev/2.1.2/v/int_parsing"
                        }
                ]
            }
        ),
        (
            1,
            404,
            {"detail":
                {
                    "error":"User is not found"
                }
            }
        )
    )
)
async def test_get_user_by_id_validation(
        client: httpx.AsyncClient,
        create_raw_user: Awaitable[None],
        user_id: int | Any,
        status_code: int,
        error_response: dict[str, Any]) -> None:
    response = await client.get(f"users/{user_id}")
    
    assert response.status_code == status_code
    assert response.json() == error_response