from typing import Any, Callable, Dict

import httpx
import pytest
from pydantic import EmailStr

from app.companies.models import RoleEnum

from .conftest import DEFAULT_USER_DATA


@pytest.mark.parametrize(
    "auth_email",
    (
        (DEFAULT_USER_DATA["email"]),
        ("admin@example.com")
    )
)
async def test_send_invitation(
          auth_email: EmailStr,
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          get_request_by_id: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_user_instance(auth_email)
    await create_company_instance()
    await create_user_company_instance()

    # Receiver objects
    await create_user_instance(email="user1@example.com", password="password123")

    token = await create_auth_jwt(auth_email)
    response = await client.post("/companies/1/invite/2/", headers={"Authorization": f"Bearer {token}"})

    data = response.json()

    assert response.status_code == 201
    assert data == {"response": "Invitation was successfully sent"}

    request = await get_request_by_id(1)
    assert request.company_id == 1
    assert request.receiver_id == 2


@pytest.mark.parametrize(
        "company_id, user_id, auth_email, sender_role, status_code, response",
        (
            (1000, 2, DEFAULT_USER_DATA["email"], None, 404, {"detail": {"error": "Requested company is not found"}}),
            (1, 2, "not_member_user@email.com", None, 403, {"detail": {"error": "Forbidden"}}),
            (1, 2, "member_user@email.com", RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}}),
            (1, 1000, DEFAULT_USER_DATA["email"], None, 404, {"detail": {"error": "Requested user is not found"}}),
            (1, 1, DEFAULT_USER_DATA["email"], None, 400, {"detail": {"error": "Requested user is already a member of the company"}}),
        )
)
async def test_send_invitation_error(
          user_id: int, 
          company_id: int,
          status_code: int,
          auth_email: EmailStr,
          sender_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_default_company_object()

    # Receiver objects
    await create_user_instance(email="user1@example.com", password="password123")

    # Company another user object
    if auth_email != DEFAULT_USER_DATA["email"]:
        await create_user_instance(email=auth_email, password="password123")
        if sender_role:
            await create_user_company_instance(user_id=3, company_id=1, role=sender_role)

    token = await create_auth_jwt(auth_email)
    server_response = await client.post(f"/companies/{company_id}/invite/{user_id}/", headers={"Authorization": f"Bearer {token}"})
    response_data = server_response.json()

    assert server_response.status_code == status_code
    assert response_data == response


async def test_send_invitation_with_received_request(
          client: httpx.AsyncClient, 
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any], 
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_default_company_object()

    # Receiver objects
    await create_user_instance(email="user1@example.com", password="password123")

    # Request, sent by user
    await create_company_request_instance(sender_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post(f"/companies/1/invite/2/", headers={"Authorization": f"Bearer {token}"})
    response_data = server_response.json()

    assert server_response.status_code == 400
    assert response_data == {"detail": {"error": "User 2 have already sent a request to the company 1"}}


@pytest.mark.parametrize(
    "auth_email, role, user_to_kick_role",
    (
        (DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Member),
        (DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Admin),
        ("admin@example.com", RoleEnum.Admin, RoleEnum.Member)
    )
)
async def test_kick_user(
          role: RoleEnum,
          auth_email: EmailStr,
          user_to_kick_role: RoleEnum,
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Query executor object
    await create_user_instance(auth_email)
    await create_company_instance()
    await create_user_company_instance(role=role)

    # Member objects
    await create_user_instance(email="user1@example.com", password="password123")
    await create_user_company_instance(user_id=2, company_id=1, role=user_to_kick_role)

    token = await create_auth_jwt(auth_email)
    response = await client.delete("/companies/1/kick/2/", headers={"Authorization": f"Bearer {token}"})

    data = response.json()

    assert response.status_code == 200
    assert data == {"response": "User user1@example.com was successfully kicked from the company"}


@pytest.mark.parametrize(
    "company_id, user_id, auth_email, executor_role, user_to_kick_role, status_code, response",
    (
        (1000, 2, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Member, 404, {"detail": {"error": "Requested company is not found"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Member, RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}}),
        (1, 1000, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Member, 404, {"detail": {"error": "Requested user is not found"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Owner, None, 400, {"detail": {"error": "User user1@example.com is not the member of the company MyCompany"}}),
        (1, 1, DEFAULT_USER_DATA["email"], RoleEnum.Owner, None, 400, {"detail": {"error": "You can't kick yourself from the company"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Admin, RoleEnum.Admin, 403, {"detail": {"error": "You don't have permission to perform this action"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Admin, RoleEnum.Owner, 403, {"detail": {"error": "You don't have permission to perform this action"}}),
    )
)
async def test_kick_user_error(
          user_id: int, 
          company_id: int,
          status_code: int,
          auth_email: EmailStr,
          executor_role: RoleEnum,
          response: Dict[str, Any],
          user_to_kick_role: RoleEnum,
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Query executor object
    await create_user_instance(auth_email)
    await create_company_instance()
    await create_user_company_instance(role=executor_role)

    # Member objects
    await create_user_instance(email="user1@example.com", password="password123")
    if user_to_kick_role:
        await create_user_company_instance(user_id=2, company_id=1, role=user_to_kick_role)

    token = await create_auth_jwt(auth_email)
    server_response = await client.delete(f"/companies/{company_id}/kick/{user_id}/", headers={"Authorization": f"Bearer {token}"})

    data = server_response.json()

    assert server_response.status_code == status_code
    assert data == response


async def test_get_company_requests(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_default_company_object()

    # Sender object
    sender_user = await create_user_instance(email="user1@example.com", password="password123")

    # Request object
    await create_company_request_instance(sender_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.get(f"/companies/1/requests/", headers={"Authorization": f"Bearer {token}"})

    data = server_response.json()[0]

    assert server_response.status_code == 200
    assert len(data) == 2

    assert data["request_id"] == 1 
    assert data["user"]["id"] == 2
    assert data["user"]["name"] == sender_user["name"]
    assert data["user"]["email"] == sender_user["email"]


@pytest.mark.parametrize(
    "company_id, auth_email, receiver_role, status_code, response",
    (
        (1, "justmember@email.com", RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}}),
        (1000, "user@email.com", RoleEnum.Owner, 404, {"detail": {"error": "Requested company is not found"}}),
    )
)
async def test_get_company_requests_error(
          company_id: int,
          status_code: int, 
          auth_email: EmailStr,
          receiver_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance(auth_email)
    await create_company_instance()
    await create_user_company_instance(role=receiver_role)

    token = await create_auth_jwt(auth_email)
    server_response = await client.get(f"/companies/{company_id}/requests/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response
    

async def test_get_company_invitations(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver object
    await create_default_company_object()

    # Invited object
    invited_user = await create_user_instance(email="user1@example.com", password="password123")

    # Request object
    await create_company_request_instance(receiver_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.get(f"/companies/1/invitations/", headers={"Authorization": f"Bearer {token}"})
    data = server_response.json()[0]
    

    assert server_response.status_code == 200
    assert len(data) == 2

    assert data["invitation_id"] == 1 
    assert data["user"]["id"] == 2
    assert data["user"]["name"] == invited_user["name"]
    assert data["user"]["email"] == invited_user["email"]


@pytest.mark.parametrize(
    "company_id, auth_email, receiver_role, status_code, response",
    (
        (1, "justmember@email.com", RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}}),
        (1000, "user@email.com", RoleEnum.Owner, 404, {"detail": {"error": "Requested company is not found"}}),
    )
)
async def test_get_company_invitations_error(
          company_id: int,
          status_code: int, 
          auth_email: EmailStr,
          receiver_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance(auth_email)
    await create_company_instance()
    await create_user_company_instance(role=receiver_role)

    token = await create_auth_jwt(auth_email)
    server_response = await client.get(f"/companies/{company_id}/invitations/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_get_admins_list(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None: 
    # Instanciate test objects
    # Receiver objects
    await create_user_instance(DEFAULT_USER_DATA["email"])
    await create_company_instance()
    await create_user_company_instance(role=RoleEnum.Admin)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.get("/companies/1/admins/", headers={"Authorization": f"Bearer {token}"})

    data = server_response.json()[0]

    assert server_response.status_code == 200
    assert len(server_response.json()) == 1

    assert data["email"] == DEFAULT_USER_DATA["email"]
    assert data["name"] == DEFAULT_USER_DATA["name"]
    assert data["role"] == "admin"
    

@pytest.mark.parametrize(
    "company_id, auth_email, receiver_role, status_code, response",
    (
        (1, "justmember@email.com", RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}}),
        (1000, "user@email.com", RoleEnum.Owner, 404, {"detail": {"error": "Requested company is not found"}}),
    )
)
async def test_get_admins_list_error(
          company_id: int,
          status_code: int, 
          auth_email: EmailStr,
          receiver_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance(auth_email)
    await create_company_instance()
    await create_user_company_instance(role=receiver_role)

    token = await create_auth_jwt(auth_email)
    server_response = await client.get(f"/companies/{company_id}/invitations/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_give_admin_role(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Executor objects
    await create_default_company_object()

    # Member objects
    await create_user_instance(email="user1@example.com", password="password123")
    await create_user_company_instance(user_id=2, company_id=1, role=RoleEnum.Member)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    response = await client.post("/companies/1/set-admin/2/", headers={"Authorization": f"Bearer {token}"})

    data = response.json()

    assert response.status_code == 200
    assert data == {"response": "User user1@example.com was successfuly assigned as admin"}


@pytest.mark.parametrize(
    "company_id, member_id, auth_email, executor_role, member_role, status_code, response",
    (
        (1000, 2, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Member, 404, {"detail": {"error": "Requested company is not found"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Member, RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Admin, RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}}),
        (1, 1, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Member, 400, {"detail": {"error": "You can't change your own role"}}),
        (1, 1000, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Member, 404, {"detail": {"error": "Requested user is not found"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Owner, None, 400, {"detail": {"error": "User user1@example.com is not the member of the company MyCompany"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Admin, 400, {"detail": {"error": "User user1@example.com is already an admin in the company MyCompany"}}),
    )
)
async def test_give_admin_role_error(
          member_id: int, 
          company_id: int,
          status_code: int,
          auth_email: EmailStr,
          member_role: RoleEnum,
          executor_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Executor objects
    await create_user_instance(auth_email)
    await create_company_instance()
    await create_user_company_instance(role=executor_role)

    # Member objects
    await create_user_instance(email="user1@example.com", password="password123")
    if member_role:
        await create_user_company_instance(user_id=2, company_id=1, role=member_role)

    token = await create_auth_jwt(auth_email)
    server_response = await client.post(f"/companies/{company_id}/set-admin/{member_id}/", headers={"Authorization": f"Bearer {token}"})

    data = server_response.json()

    assert server_response.status_code == status_code
    assert data == response


async def test_take_admin_role(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Executor objects
    await create_default_company_object()

    # Admin objects
    await create_user_instance(email="user1@example.com", password="password123")
    await create_user_company_instance(user_id=2, company_id=1, role=RoleEnum.Admin)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    response = await client.post("/companies/1/unset-admin/2/", headers={"Authorization": f"Bearer {token}"})

    data = response.json()

    assert response.status_code == 200
    assert data == {"response": "The admin role has been taken away from the user user1@example.com"}


@pytest.mark.parametrize(
    "company_id, admin_id, auth_email, executor_role, admin_role, status_code, response",
    (
        (1000, 2, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Admin, 404, {"detail": {"error": "Requested company is not found"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Member, RoleEnum.Admin, 403, {"detail": {"error": "Forbidden"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Admin, RoleEnum.Admin, 403, {"detail": {"error": "Forbidden"}}),
        (1, 1, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Admin, 400, {"detail": {"error": "You can't change your own role"}}),
        (1, 1000, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Admin, 404, {"detail": {"error": "Requested user is not found"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Owner, None, 400, {"detail": {"error": "User user1@example.com is not the member of the company MyCompany"}}),
        (1, 2, DEFAULT_USER_DATA["email"], RoleEnum.Owner, RoleEnum.Member, 400, {"detail": {"error": "User user1@example.com is not an admin in the company MyCompany"}}),
    )
)
async def test_take_admin_role_error(
          admin_id: int, 
          company_id: int,
          status_code: int,
          auth_email: EmailStr,
          admin_role: RoleEnum,
          executor_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Executor objects
    await create_user_instance(auth_email)
    await create_company_instance()
    await create_user_company_instance(role=executor_role)

    # Admin objects
    await create_user_instance(email="user1@example.com", password="password123")
    if admin_role:
        await create_user_company_instance(user_id=2, company_id=1, role=admin_role)

    token = await create_auth_jwt(auth_email)
    server_response = await client.post(f"/companies/{company_id}/unset-admin/{admin_id}/", headers={"Authorization": f"Bearer {token}"})

    data = server_response.json()

    assert server_response.status_code == status_code
    assert data == response


async def test_leave_company(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Member objects
    await create_user_instance(DEFAULT_USER_DATA["email"])
    await create_company_instance()
    await create_user_company_instance(role=RoleEnum.Member)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/companies/1/leave/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 200
    assert server_response.json() == {"response": "You have successfully left company 1"}


@pytest.mark.parametrize(
    "company_id, user_role, status_code, response",
    (
        (1000, RoleEnum.Member, 404, {"detail": {"error": "Requested company is not found"}}),
        (1, None, 400, {"detail": {"error": "User 1 is not the member of the company 1"}}),
        (1, RoleEnum.Owner, 400, {"detail": {"error": "Owner can't leave its company"}}),
    )
)
async def test_leave_company_error(
          company_id: int,
          status_code: int, 
          user_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Member objects
    await create_user_instance(DEFAULT_USER_DATA["email"])
    await create_company_instance()
    if user_role:
        await create_user_company_instance(role=user_role)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/companies/{company_id}/leave/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_accept_user_request(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_default_company_object()

    # Sender objects
    await create_user_instance("sender@example.com")

    # Request object 
    await create_company_request_instance(sender_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post(f"/requests/1/accept/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 200
    assert server_response.json() == {"response": "Membership request was successfully accepted"}


@pytest.mark.parametrize(
    "request_id, receiver_role, status_code, response",
    (
        (1000, RoleEnum.Owner, 404, {"detail": {"error": "Membership request is not found"}}),
        (1, RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}})
    )
)
async def test_accept_user_request_error(
          request_id: int, 
          status_code: int,
          receiver_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance(DEFAULT_USER_DATA["email"])
    await create_company_instance()
    await create_user_company_instance(role=receiver_role)

    # Sender objects
    await create_user_instance("sender@example.com")

    # Request object 
    await create_company_request_instance(sender_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post(f"/requests/{request_id}/accept/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_decline_request(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_default_company_object()

    # Sender objects
    await create_user_instance("sender@example.com")

    # Request object 
    await create_company_request_instance(sender_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/requests/1/decline/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 200
    assert server_response.json() == {"response": "Membership request was successfully declined"}


@pytest.mark.parametrize(
    "request_id, receiver_role, status_code, response",
    (
        (1000, RoleEnum.Owner, 404, {"detail": {"error": "Membership request is not found"}}),
        (1, RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}})
    )
)
async def test_decline_request_error(
          request_id: int, 
          status_code: int,
          receiver_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance(DEFAULT_USER_DATA["email"])
    await create_company_instance()
    await create_user_company_instance(role=receiver_role)

    # Sender objects
    await create_user_instance("sender@example.com")

    # Request object 
    await create_company_request_instance(sender_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/requests/{request_id}/decline/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_cancel_sent_invitation(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_default_company_object()

    # Receiver objects
    await create_user_instance("receiver@example.com")

    # Create request
    await create_company_request_instance(receiver_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/invitations/1/cancel/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 200
    assert server_response.json() == {"response": "Invitation was successfully canceled"}


@pytest.mark.parametrize(
    "request_id, sender_role, status_code, response",
    (
        (1000, RoleEnum.Owner,  404,  {"detail": {"error": "Invitation is not found"}}),
        (1, RoleEnum.Member, 403, {"detail": {"error": "Forbidden"}})
    )
)
async def test_cancel_sent_invitation_error(
          request_id: int, 
          status_code: int,
          sender_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_user_instance(DEFAULT_USER_DATA["email"])
    await create_company_instance()
    await create_user_company_instance(role=sender_role)

    # Receiver objects
    await create_user_instance("receiver@example.com")

    # Create request
    await create_company_request_instance(receiver_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/invitations/{request_id}/cancel/", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response
 