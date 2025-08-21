"""Main Tests"""
from context import *

@pytest.mark.anyio
async def test_root(client: AsyncClient, session: Session):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["detail"] == "I'm a Canary!"

@pytest.mark.anyio
async def test_failed_auth(client: AsyncClient):
    client.headers = {}
    response = await client.get("/config")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
