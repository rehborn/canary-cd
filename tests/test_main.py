"""Main Test"""
from context import *

def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["detail"] == "I'm a Canary!"

def test_failed_auth(client: TestClient):
    client.headers = {}
    response = client.get("/project/list")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
