from typing import Any, Callable, Dict

import httpx
import pytest
from pydantic import EmailStr

from app.companies.models import RoleEnum

from .conftest import DEFAULT_USER_DATA


async def test_get_user_invitations(
          client: httpx.AsyncClient, create_user_instance: Callable[..., Any], 
          create_auth_jwt: Callable[..., Any],
          create_company_instance: Callable[..., Any], 
          create_user_company_instance: Callable[..., Any], 
          create_company_request_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any]) -> None:
    # Instanciate objects
    # Receiver objects
    await create_default_company_object()

    # Sender objects
    another_user = await create_user_instance(email="user1@example.com", password="password123")
    another_company = await create_company_instance(title="AnotherCompany")
    await create_user_company_instance(user_id=2, company_id=2)

    # Request object
    await create_company_request_instance(sender_id=None, receiver_id=1, company_id=2)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    response = await client.get("/me/invitations", headers={"Authorization": f"Bearer {token}"})

    data = response.json()[0]

    assert response.status_code == 200
    assert data["invitation_id"] == 1 
    assert data["company"]["id"] == 2
    assert data["company"]["title"] == another_company["title"]
    assert data["company"]["description"] == another_company["description"]
    assert data["company"]["is_hidden"] == another_company["is_hidden"]

    
async def test_get_user_requests(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any], 
          create_user_company_instance: Callable[..., Any], 
          create_company_request_instance: Callable[..., Any],
          create_default_company_object: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_default_company_object()

    # Receiver objects
    another_user = await create_user_instance(email="user1@example.com", password="password123")
    another_company = await create_company_instance(title="AnotherCompany")
    await create_user_company_instance(user_id=2, company_id=2)

    # Request object
    await create_company_request_instance(sender_id=1, receiver_id=None, company_id=2)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    response = await client.get("/me/requests", headers={"Authorization": f"Bearer {token}"})

    data = response.json()[0]

    assert response.status_code == 200
    assert data["request_id"] == 1 
    assert data["company"]["id"] == 2
    assert data["company"]["title"] == another_company["title"]
    assert data["company"]["description"] == another_company["description"]
    assert data["company"]["is_hidden"] == another_company["is_hidden"]


async def test_send_membership_request(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance("companyowner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Sender objects
    await create_user_instance(DEFAULT_USER_DATA["email"])

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post(f"/requests/send/1", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 200
    assert server_response.json() == {"response": "Membership request was successfully sent"}
    

@pytest.mark.parametrize(
    "company_id, member_role, status_code, response",
    (
        (1000, None, 404, {"detail": {"error": "Requested company is not found"}}),
        (1, RoleEnum.Member, 400, {"detail": {"error": "You are already a member of this company"}}),
    )
)
async def test_send_membership_request_error(
          company_id: int, 
          status_code: int,
          member_role: RoleEnum,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any]) -> None: 
    # Instanciate test objects
    # Receiver objects
    await create_user_instance("companyowner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Sender objects
    await create_user_instance(DEFAULT_USER_DATA["email"])
    if member_role:
        await create_user_company_instance(company_id=company_id, user_id=2, role=member_role)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post(f"/requests/send/{company_id}", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_send_request_with_received_invitation(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance("companyowner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Sender objects
    await create_user_instance(DEFAULT_USER_DATA["email"])

    # Create invtitation
    await create_company_request_instance(receiver_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post(f"/requests/send/1", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 400
    assert server_response.json() == {"detail": {"error": "You have already received invitation to the company 1"}}


async def test_cancel_sent_request(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance("companyowner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Sender objects
    await create_user_instance(DEFAULT_USER_DATA["email"])

    # Create request
    await create_company_request_instance(sender_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/requests/1/cancel", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 200
    assert server_response.json() == {"response": "Membership request was successfully canceled"}


@pytest.mark.parametrize(
    "request_id, auth_email, sender_id, status_code, response",
    (
        (1000, DEFAULT_USER_DATA["email"], 2,  404,  {"detail": {"error": "Membership request is not found"}}),
        (1, DEFAULT_USER_DATA["email"], 3, 403, {"detail": {"error": "Forbidden"}})
    )
)
async def test_cancel_sent_request_error(
          sender_id: int,
          request_id: int, 
          status_code: int,
          auth_email: EmailStr,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Receiver objects
    await create_user_instance("companyowner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Sender objects
    await create_user_instance(auth_email)

    if sender_id !=2:
        await create_user_instance("anothersender@example.com")

    # Create request
    await create_company_request_instance(sender_id=sender_id, company_id=1)

    token = await create_auth_jwt(auth_email)
    server_response = await client.delete(f"/requests/{request_id}/cancel", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_accept_invitation(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_user_instance("owner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Receiver objects
    await create_user_instance(DEFAULT_USER_DATA["email"])

    # Request object 
    await create_company_request_instance(receiver_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post(f"/invitations/1/accept", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 200
    assert server_response.json() == {"response": "Invitation was successfully accepted"}


@pytest.mark.parametrize(
    "request_id, receiver_id, status_code, response",
    (
        (1000, 2, 404,  {"detail": {"error": "Invitation is not found"}}),
        (1, 3, 403, {"detail": {"error": "Forbidden"}})
    )
)
async def test_accept_invitation_error(
          request_id: int, 
          receiver_id: int,
          status_code: int,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_user_instance("owner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Receiver objects
    await create_user_instance(DEFAULT_USER_DATA["email"])

    if receiver_id != 2:
        await create_user_instance("anotheruser@example.com")

    # Request object 
    await create_company_request_instance(receiver_id=receiver_id, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.post(f"/invitations/{request_id}/accept", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response


async def test_decline_invitation(
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_user_instance("owner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Receiver objects
    await create_user_instance(DEFAULT_USER_DATA["email"])

    # Request object 
    await create_company_request_instance(receiver_id=2, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/invitations/1/decline", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == 200
    assert server_response.json() == {"response": "Invitation was successfully declined"}


@pytest.mark.parametrize(
    "request_id, receiver_id, status_code, response",
    (
        (1000, 2, 404,  {"detail": {"error": "Invitation is not found"}}),
        (1, 3, 403, {"detail": {"error": "Forbidden"}})
    )
)
async def test_decline_invitation_error(
          request_id: int, 
          receiver_id: int,
          status_code: int,
          response: Dict[str, Any],
          client: httpx.AsyncClient,
          create_auth_jwt: Callable[..., Any],
          create_user_instance: Callable[..., Any],
          create_company_instance: Callable[..., Any],
          create_user_company_instance: Callable[..., Any],
          create_company_request_instance: Callable[..., Any]) -> None:
    # Instanciate test objects
    # Sender objects
    await create_user_instance("owner@example.com")
    await create_company_instance()
    await create_user_company_instance()

    # Receiver objects
    await create_user_instance(DEFAULT_USER_DATA["email"])

    if receiver_id != 2:
        await create_user_instance("anotheruser@example.com")

    # Request object 
    await create_company_request_instance(receiver_id=receiver_id, company_id=1)

    token = await create_auth_jwt(DEFAULT_USER_DATA["email"])
    server_response = await client.delete(f"/invitations/{request_id}/decline", headers={"Authorization": f"Bearer {token}"})

    assert server_response.status_code == status_code
    assert server_response.json() == response
    