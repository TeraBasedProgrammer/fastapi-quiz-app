import json
from datetime import datetime
from typing import Any, Callable

import httpx
import pytest


# Get all users
async def test_get_users_empty(client: httpx.AsyncClient) -> None:
    response = await client.get("/users/")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 50, "pages": 0}


async def test_get_users(client: httpx.AsyncClient, create_user_instance: Callable[..., Any]) -> None:
    # Instantiate user in the DB
    user_data = await create_user_instance()

    response = await client.get("/users/")
    json_response = response.json()

    assert response.status_code == 200
    assert json_response.get("items") is not None
    assert json_response["total"] == 1

    data = json_response["items"][0]
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["id"] == 1
    assert data.get("password") is None
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
        create_user_instance: Callable[..., Any],
        page: int,
        size: int,
        items_is_not_empty: bool,
        total_expected: int,
        pages_expected: int,
) -> None:
    user2_data = {
        "email": "test2@email.com",
        "name": "anton",
        "password": "password123",
    }

    # Instantiate 2 users in the DB
    await create_user_instance()
    await create_user_instance(**user2_data)

    response = await client.get(f"/users/?page={page}&size={size}")
    json_response = response.json()

    assert response.status_code == 200
    assert bool(json_response.get("items")) != items_is_not_empty
    assert json_response["total"] == total_expected
    assert json_response["pages"] == pages_expected
    assert json_response["size"] == size


# Get single user
async def test_get_user_by_id(client: httpx.AsyncClient,
                              create_user_instance: Callable[..., Any]) -> None:
    # Instantiate a user in the DB
    user_data = await create_user_instance()

    response = await client.get("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["id"] == 1
    assert data.get("password") is None
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
                        "type": "int_parsing",
                        "loc": ["path", "user_id"],
                        "msg": "Input should be a valid integer, unable to parse string as an integer",
                        "input": "definitely-not-an-integer",
                        "url": "https://errors.pydantic.dev/2.1.2/v/int_parsing"
                    }
                ]
            }
        ),
        (
            1,
            404,
            {"detail":
                {
                    "error": "User is not found"
                }
            }
        )
    )
)
async def test_get_user_by_id_validation(
        client: httpx.AsyncClient,
        user_id: int | Any,
        status_code: int,
        error_response: dict[str, Any]) -> None:
    response = await client.get(f"users/{user_id}")

    assert response.status_code == status_code
    assert response.json() == error_response


# Delete user
async def test_delete_user(client: httpx.AsyncClient,
                           create_user_instance: Callable[..., Any],
                           create_auth_jwt: Callable[..., Any]) -> None:
    user_data = await create_user_instance()
    jwt = await create_auth_jwt(user_data["email"])
    response = await client.delete("/users/1/delete", headers={"Authorization": f"Bearer {jwt}"})

    assert response.status_code == 200
    assert response.json() == {"deleted_user_id": 1}


async def test_delete_user_not_found(client: httpx.AsyncClient,
                                     create_user_instance: Callable[..., Any],
                                     create_auth_jwt: Callable[..., Any]) -> None:
    user_data = await create_user_instance()
    jwt = await create_auth_jwt(user_data["email"])
    response = await client.delete("/users/200/delete", headers={"Authorization": f"Bearer {jwt}"})

    assert response.status_code == 404
    assert response.json() == {"detail": {"error": "User is not found"}}


async def test_delete_user_permission_error(client: httpx.AsyncClient,
                                            create_user_instance: Callable[..., Any],
                                            create_auth_jwt: Callable[..., Any]) -> None:
    await create_user_instance()
    user2_data = await create_user_instance(email="test2@example.com", password="password123", name="anton")
    jwt = await create_auth_jwt(user2_data["email"])

    response = await client.delete("/users/1/delete", headers={"Authorization": f"Bearer {jwt}"})

    assert response.status_code == 403
    assert response.json() == {'detail': {'error': 'Forbidden'}}


# Update user
async def test_update_user(client: httpx.AsyncClient,
                           create_user_instance: Callable[..., Any],
                           create_auth_jwt: Callable[..., Any]) -> None:
    user_data = await create_user_instance()
    jwt = await create_auth_jwt(user_data["email"])

    update_data = {"name": "New Name"}
    response = await client.patch("/users/1/update", headers={"Authorization": f"Bearer {jwt}"},
                                  data=json.dumps(update_data))
    assert response.status_code == 200


@pytest.mark.parametrize(
    "update_data, status_code, response_error",
    (
        ({"name": "1231jnkdskjas"}, 400, {"detail": "Name should contain only english letters"}),
        ({"password": "short"}, 400, {"detail": "Password should contain at least eight characters, at least one letter and one number"}),
        ({"email": "anotheremail@gmail.com"}, 400, {"detail": "You can't change the email"}),
        ({}, 400, {"detail": {"error": "At least one parameter should be provided for user update query"}}),
    )
)
async def test_update_user_validation(
        client: httpx.AsyncClient,
        create_user_instance: Callable[..., Any],
        create_auth_jwt: Callable[..., Any],
        update_data: dict[str, Any],
        status_code: int,
        response_error: dict[str, Any]) -> None:
    user_data = await create_user_instance()
    jwt = await create_auth_jwt(user_data["email"])

    response = await client.patch("/users/1/update", headers={"Authorization": f"Bearer {jwt}"},
                                  data=json.dumps(update_data))
    assert response.status_code == status_code
    assert response.json() == response_error


async def test_update_user_permission_error(client: httpx.AsyncClient,
                                            create_user_instance: Callable[..., Any],
                                            create_auth_jwt: Callable[..., Any]) -> None:
    await create_user_instance()
    user2_data = await create_user_instance(email="test2@example.com", password="password123", name="anton")
    jwt = await create_auth_jwt(user2_data["email"])

    response = await client.patch("/users/1/update",
                                  headers={"Authorization": f"Bearer {jwt}"},
                                  data=json.dumps({"name": "name"}))

    assert response.status_code == 403
    assert response.json() == {'detail': {'error': 'Forbidden'}}
