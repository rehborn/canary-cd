"""Project Test"""
from context import *
from canary_cd.models import ProjectDetails

TEST_NAME = 'test-project-for-secret'
TEST_REMOTE = 'git@github.com/github/example.git'
TEST_PROJECT = {'name': TEST_NAME, 'remote': TEST_REMOTE, 'branch': 'main'}
TEST_SECRET = {'key': 'KEY', 'value': 'VALUE'}

class TestSecretAPI:
    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_project_create_for_secrets(self, client: AsyncClient, session: Session):
        response = await client.post("/project", json=TEST_PROJECT)
        data = response.json()
        assert 'name' in data.keys()
        assert 'remote' in data.keys()
        assert response.status_code == 201

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestSecretAPI::test_project_create_for_secrets'])
    async def test_secret_create(self, client: AsyncClient, session: Session):
        response = await client.put(f"/secret/{TEST_NAME}", json=TEST_SECRET)
        data = response.json()
        assert 'key' in data.keys()
        assert response.status_code == 200

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestSecretAPI::test_secret_create'])
    async def test_secret_view(self, client: AsyncClient, session: Session):
        response = await client.get(f"/secret/{TEST_NAME}")
        data = response.json()
        assert response.status_code == 200
        assert len(data) == 1

        assert 'key' in data[0].keys()
        assert 'value' in data[0].keys()
        assert data[0]['key'] == TEST_SECRET['key']
        assert data[0]['value'] == TEST_SECRET['value']

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestSecretAPI::test_secret_create'])
    async def test_secret_delete(self, client: AsyncClient):
        response = await client.delete(f'/secret/{TEST_NAME}/{TEST_SECRET["key"]}')
        data = response.json()
        assert response.status_code == 200
        assert data['detail'] == f'{TEST_SECRET["key"]} deleted'
