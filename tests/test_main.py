import pytest_asyncio

import pytest
import httpx
from app.main import app


@pytest_asyncio.fixture()
async def client():
    async with httpx.AsyncClient(app=app, base_url='http://testserver') as client:
        yield client


@pytest.mark.asyncio
async def test_main(client: httpx.AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status_code": 200, "detail": "ok", "result": "working"}
