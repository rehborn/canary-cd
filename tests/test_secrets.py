"""Project Test"""
from context import *
from canary_cd.models import ProjectDetails

TEST_NAME = 'test-project-for-secret'
TEST_REMOTE = 'git@github.com/github/example.git'
TEST_PROJECT = {'name': TEST_NAME, 'remote': TEST_REMOTE, 'branch': 'main'}
TEST_SECRET = {'key': 'KEY', 'value': 'VALUE'}

class TestSecretAPI:
    @pytest.fixture()
    def create_project_dummy(self, session: Session):
        project = Project(**TEST_PROJECT)
        session.add(project)
        session.commit()

    @pytest.mark.anyio
    @pytest.mark.dependency()
    @pytest.mark.usefixtures('create_project_dummy')
    async def test_secret_set(self, client: AsyncClient, session: Session):
        response = await client.put(f"/secret/{TEST_NAME}", json=TEST_SECRET)
        data = response.json()
        assert 'key' in data.keys()
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_secret_set_invalid_project(self, client: AsyncClient, session: Session):
        response = await client.put(f"/secret/does-not-exist", json=TEST_SECRET)
        data = response.json()
        assert response.status_code == 403
        assert data['detail'] == 'Project does not exists'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestSecretAPI::test_secret_set'])
    async def test_secret_list(self, client: AsyncClient, session: Session):
        response = await client.get(f"/secret/{TEST_NAME}")
        data = response.json()
        assert response.status_code == 200
        assert len(data) == 1

        assert 'key' in data[0].keys()
        assert 'value' in data[0].keys()
        assert data[0]['key'] == TEST_SECRET['key']
        assert data[0]['value'] == TEST_SECRET['value']

    @pytest.mark.anyio
    async def test_secret_list_invalid_project(self, client: AsyncClient, session: Session):
        response = await client.get(f"/secret/does-not-exist")
        data = response.json()
        assert response.status_code == 403
        assert data['detail'] == 'Project does not exists'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestSecretAPI::test_secret_set'])
    async def test_secret_delete(self, client: AsyncClient):
        response = await client.delete(f'/secret/{TEST_NAME}/{TEST_SECRET["key"]}')
        data = response.json()
        assert response.status_code == 200
        assert data['detail'] == f'{TEST_SECRET["key"]} deleted'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestSecretAPI::test_secret_set'])
    async def test_secret_delete_invalid_key(self, client: AsyncClient):
        response = await client.delete(f'/secret/{TEST_NAME}/invalid-key')
        data = response.json()
        assert response.status_code == 403
        assert data['detail'] == 'Secret does not exists'

    @pytest.mark.anyio
    async def test_secret_delete_invalid_project(self, client: AsyncClient):
        response = await client.delete(f'/secret/does-not-exist/key')
        data = response.json()
        assert response.status_code == 403
        assert data['detail'] == 'Project does not exists'