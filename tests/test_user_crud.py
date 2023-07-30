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
    assert data["companies"] == []
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
    assert data["companies"] == []
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
    assert response.json() == {"deleted_instance_id": 1}


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
        ({"email": "anotheremail@gmail.com"}, 400, {"detail": "User email can't be changed, try again"}),
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
    print(response.json())
    print(response_error)
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


async def test_user_with_company(client: httpx.AsyncClient,
                                 create_default_company_object: Callable[..., Any]) -> None:
    # Initialize data
    await create_default_company_object()
    
    response = await client.get("/users/1")
    assert response.status_code == 200
    data = response.json()

    companies = data["companies"]
    assert len(companies) == 1
    assert companies[0]["title"] == "MyCompany"
    assert companies[0]["description"] == "Description"
    assert companies[0].get("is_hidden") == None
    assert companies[0]["created_at"].split("T")[0] == str(datetime.utcnow().date())
    


async def test_user_after_company_delete(client: httpx.AsyncClient,
                                         create_auth_jwt: Callable[..., Any],                                         
                                         create_default_company_object: Callable[..., Any]) -> None:
    # Initialize data
    await create_default_company_object()
    
    response_before = await client.get("/users/1")
    assert response_before.status_code == 200
    data_before = response_before.json()

    # Check companies list before deleting the company
    companies_before = data_before["companies"]
    assert len(companies_before) == 1

    token = await create_auth_jwt(data_before["email"])
    response_delete = await client.delete("/companies/1/delete", headers={"Authorization": f"Bearer {token}"})
    assert response_delete.json() == {"deleted_instance_id" : 1}

    response_after = await client.get("/users/1")
    assert response_after.status_code == 200
    
    # Check companies list after deleting the company
    data_after = response_after.json()
    companies_after = data_after["companies"]
    assert len(companies_after) == 0