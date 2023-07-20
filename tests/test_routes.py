import httpx


async def test_get_users(client: httpx.AsyncClient) -> None:
    response = await client.get("/users/")
    assert response.status_code == 200
    assert response.json() == {"items":[],"total":0,"page":1,"size":50,"pages":0}


async def test_get_user_by_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/users/1")
    assert response.status_code == 404
    assert response.json() == {"detail":{"error":"User is not found"}}
