import json
from datetime import datetime
from typing import Any, Callable, Dict

import httpx
import pytest

from .conftest import DEFAULT_COMPANY_DATA, DEFAULT_USER_DATA


async def test_get_companies_empty(client: httpx.AsyncClient,
                                   create_auth_jwt: Callable[..., Any],
                                   create_user_instance: Callable[..., Any]) -> None:
    await create_user_instance()
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])

    response = await client.get("/companies/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 50, "pages": 0}


async def test_get_companies(client: httpx.AsyncClient, 
                             create_default_company_object: Callable[..., Any],
                             create_auth_jwt: Callable[..., Any]) -> None:
    await create_default_company_object()
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])

    response = await client.get("/companies/", headers={"Authorization": f"Bearer {token}"})
    json_response = response.json()

    assert response.status_code == 200
    assert json_response.get("items") is not None
    assert json_response["total"] == 1

    data = json_response["items"][0]
    users = data["users"]
    assert len(users) == 1

    assert data["id"] == DEFAULT_COMPANY_DATA["id"]
    assert data["title"] == DEFAULT_COMPANY_DATA["title"]
    assert data["description"] == DEFAULT_COMPANY_DATA["description"]
    assert data["created_at"].split("T")[0] == str(datetime.utcnow().date())

    assert users[0]["email"] == DEFAULT_USER_DATA["email"]
    assert users[0]["name"] == DEFAULT_USER_DATA["name"]
    assert users[0]["registered_at"].split("T")[0] == str(datetime.utcnow().date())


async def test_get_companies_hidden(client: httpx.AsyncClient, 
                                    create_default_company_object: Callable[..., Any],
                                    create_auth_jwt: Callable[..., Any],
                                    create_company_instance: Callable[..., Any]) -> None:
    await create_default_company_object()
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])

    # Create additional hidden companies
    await create_company_instance(title="hiddenCompany", is_hidden=True)
    await create_company_instance(title="secondHiddenCompany", is_hidden=True)

    response = await client.get("/companies/", headers={"Authorization": f"Bearer {token}"})
    json_response = response.json()

    assert response.status_code == 200
    assert json_response.get("items") is not None
    assert json_response["total"] == 1


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
async def test_get_companies_paginated(
        client: httpx.AsyncClient,
        page: int,
        size: int,
        items_is_not_empty: bool,
        total_expected: int,
        pages_expected: int,
        create_default_company_object: Callable[..., Any],
        create_company_instance: Callable[..., Any],
        create_auth_jwt: Callable[..., Any]) -> None:
    await create_default_company_object()
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])

    # Create additional company
    await create_company_instance(title="Company", is_hidden=False)

    response = await client.get(f"/companies/?page={page}&size={size}", headers={"Authorization": f"Bearer {token}"})
    json_response = response.json()

    assert response.status_code == 200
    assert bool(json_response.get("items")) != items_is_not_empty
    assert json_response["total"] == total_expected
    assert json_response["pages"] == pages_expected
    assert json_response["size"] == size


async def test_get_company_by_id(client: httpx.AsyncClient,
                                 create_default_company_object: Callable[..., Any],
                                 create_auth_jwt: Callable[..., Any]) -> None:
    await create_default_company_object()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    response = await client.get("/companies/1", headers={"Authorization": f"Bearer {token}"})
    json_response = response.json()

    assert response.status_code == 200
    assert isinstance(json_response, dict)


    assert json_response["id"] == DEFAULT_COMPANY_DATA["id"]
    assert json_response["title"] == DEFAULT_COMPANY_DATA["title"]
    assert json_response["description"] == DEFAULT_COMPANY_DATA["description"]
    assert json_response["created_at"].split("T")[0] == str(datetime.utcnow().date())


@pytest.mark.parametrize(
    "company_id, status_code, error_response",
    (
        (
            "definitely-not-an-integer",
            422,
            {"detail":
                [
                    {
                        "type": "int_parsing",
                        "loc": ["path", "company_id"],
                        "msg": "Input should be a valid integer, unable to parse string as an integer",
                        "input": "definitely-not-an-integer",
                        "url": "https://errors.pydantic.dev/2.1.2/v/int_parsing"
                    }
                ]
            }
        ),
        (
            100,
            404,
            {"detail":
                {
                    "error": "Company is not found"
                }
            }
        )
    )
)
async def test_get_company_by_id_validation(
        client: httpx.AsyncClient,
        company_id: int | Any,
        status_code: int,
        error_response: dict[str, Any],
        create_default_company_object: Callable[..., Any],
        create_auth_jwt: Callable[..., Any]) -> None:
    await create_default_company_object()
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])

    response = await client.get(f"companies/{company_id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == status_code
    assert response.json() == error_response


@pytest.mark.parametrize(
        "owner_email, status_code",
        (
            ("notme@example.com", 403),
            (DEFAULT_USER_DATA["email"], 200)
        )
)
async def test_get_hidden_company_by_id(client: httpx.AsyncClient,
                                        owner_email: str,
                                        status_code: int,
                                        create_company_instance: Callable[..., Any],
                                        create_auth_jwt: Callable[..., Any],
                                        create_user_instance: Callable[..., Any],
                                        create_user_company_instance: Callable[..., Any]) -> None:
                                        
    # Create hidden company
    await create_user_instance(email=owner_email)
    await create_company_instance(is_hidden=True)
    await create_user_company_instance(user_id=1, company_id=1)

    # Create current user
    if DEFAULT_USER_DATA["email"] != owner_email:
        await create_user_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.get(f"companies/1", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code


@pytest.mark.parametrize(
        "company_id, owner_email, status_code, response",
        (
            (1, "notme@example.com", 403, {"detail": {"error": "Forbidden"}}),
            (100, DEFAULT_USER_DATA["email"], 404, {"detail": {"error": "Company is not found"}}),
            (1, DEFAULT_USER_DATA["email"], 200, {"deleted_instance_id": 1})
        )
)
async def test_delete_company(client: httpx.AsyncClient,
                              response: Dict[str, Any],
                            company_id: int,
                            owner_email: str,
                            status_code: int,
                            create_company_instance: Callable[..., Any],
                            create_auth_jwt: Callable[..., Any],
                            create_user_instance: Callable[..., Any],
                            create_user_company_instance: Callable[..., Any]) -> None:
    # Create company
    await create_user_instance(email=owner_email)
    await create_company_instance()
    await create_user_company_instance(user_id=1, company_id=1)

    # Create current user
    if DEFAULT_USER_DATA["email"] != owner_email:
        await create_user_instance()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"companies/{company_id}/delete", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


# Signup
@pytest.mark.parametrize(
    "company_data, status_code, response",
    (
        (
            {"title": "MyCompany", "description": "desc", "is_hidden": "False"},
            201,
            {"id": 1, "title": "MyCompany"}
        ), 
        (
            {"title": "MyCompany1?", "description": "desc", "is_hidden": "False"},
            400,
            {"detail": "Title may contain only english letters, numbers and special characters ('.', '-', ' ')"}
        ), 
        (
            {"title": "MyCompany1", "description": "desc", "is_hidden": "Bullshit"},
            422,
            {"detail": [{"type": "bool_parsing","loc": ["body","is_hidden"],"msg": "Input should be a valid boolean, unable to interpret input","input": "Bullshit","url": "https://errors.pydantic.dev/2.1.2/v/bool_parsing"}]}
        ), 
        (
            {"description": "desc", "is_hidden": "false"},
            422,
            {"detail": [{"type": "missing","loc": ["body","title"],"msg": "Field required","input": {"description": "desc","is_hidden": "false"},"url": "https://errors.pydantic.dev/2.1.2/v/missing"}]}
        ), 
    )
)
async def test_create_company(client: httpx.AsyncClient,
                      company_data: dict[str, Any],
                      status_code: int,
                      response: dict[str, Any],
                      create_user_instance: Callable[..., Any],
                      create_auth_jwt: Callable[..., Any]) -> None:
    await create_user_instance()
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])     

    server_response = await client.post("/companies/", data=json.dumps(company_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_company_duplicate(client: httpx.AsyncClient, 
                                 create_auth_jwt: Callable[..., Any],
                                 create_default_company_object: Callable[..., Any]) -> None:
    await create_default_company_object()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post("/companies/", 
                                        data=json.dumps({"title": DEFAULT_COMPANY_DATA["title"], "description": DEFAULT_COMPANY_DATA["description"], "is_hidden": DEFAULT_COMPANY_DATA["is_hidden"]}), 
                                        headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 400
    assert server_response.json() == {"detail": {"error": "Company with this name already exists"}}



@pytest.mark.parametrize(
    "update_data, status_code",
    (
        ({"title": "NewCompanyTitle"}, 200),
        ({"title": "dsfdss?"}, 400),
    )
)
async def test_update_company(client: httpx.AsyncClient,
                              update_data: dict[str, Any],
                              status_code: int,
                           create_default_company_object: Callable[..., Any],
                           create_auth_jwt: Callable[..., Any]) -> None:
    await create_default_company_object()

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.patch("/companies/1/update", data=json.dumps(update_data), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == status_code


async def test_update_company_permission(client: httpx.AsyncClient,
                           create_company_instance: Callable[..., Any],
                           create_user_instance: Callable[..., Any],
                           create_user_company_instance: Callable[..., Any],
                           create_auth_jwt: Callable[..., Any]) -> None:
    # Create company object that won't belong to current user
    await create_user_instance("notmyemail@examle.com")
    await create_company_instance()
    await create_user_company_instance()

    # Create current user
    await create_user_instance(DEFAULT_USER_DATA["email"])
    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])

    server_response = await client.patch("/companies/1/update", data=json.dumps({"title": "title"}), headers={"Authorization": f"Bearer {token}"})
    assert server_response.status_code == 403
    assert server_response.json() == {"detail": {"error": "Forbidden"}}
