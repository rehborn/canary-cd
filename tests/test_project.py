"""Project Test"""
from context import *
from canary_cd.models import ProjectDetails
from canary_cd.dependencies import ch

TEST_NAME = "test"
TEST_REMOTE = 'git@github.com/github/example.git'
TEST_AUTH_NAME = 'dummy-auth-key'
TEST_PROJECT = {'name': TEST_NAME, 'remote': TEST_REMOTE, 'branch': 'main', 'key': TEST_AUTH_NAME}
TEST_PROJECT_INVALID_KEY = {'name': 'invalid-key', 'remote': TEST_REMOTE, 'branch': 'main', 'key': 'invalid-key'}
TEST_PROJECT_NO_NAME = {'name': None, 'remote': TEST_REMOTE, 'branch': 'main'}


class TestProjectAPI:
    @pytest.fixture()
    def create_auth_dummy(self, session: Session):
        nonce, ciphertext = ch.encrypt('gh_pat')
        auth = Auth(
            name=TEST_AUTH_NAME,
            auth_type='pat',
            nonce=nonce,
            ciphertext=ciphertext,
        )
        session.add(auth)
        session.commit()

    @pytest.mark.anyio
    @pytest.mark.dependency()
    @pytest.mark.usefixtures('create_auth_dummy')
    async def test_project_create(self, client: AsyncClient):
        response = await client.post("/project", json=TEST_PROJECT)
        data = response.json()
        assert 'name' in data.keys()
        assert 'remote' in data.keys()
        assert data['key'] == f'pat:{TEST_AUTH_NAME}'
        assert response.status_code == 201

    @pytest.mark.anyio
    async def test_project_create_invalid_key(self, client: AsyncClient):
        response = await client.post("/project", json=TEST_PROJECT_INVALID_KEY)
        data = response.json()
        assert response.status_code == 404
        assert data['detail'] == 'Key does not exist'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_create_duplicate(self, client: AsyncClient):
        response = await client.post("/project", json=TEST_PROJECT)
        assert response.json()['detail'] == 'Project already exists'
        assert response.status_code == 403

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_view(self, client: AsyncClient, session: Session):
        response = await client.get(f"/project/{TEST_NAME}")
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == TEST_NAME
        # for field, item in type(ProjectDetails).model_fields.items():
        #     if not item.exclude:
        #         assert field in data, f'{field} not in {data}'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_update(self, client: AsyncClient, session: Session):
        response = await client.put(f"/project/{TEST_NAME}", json=TEST_PROJECT)
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == TEST_NAME

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_update_invalid_key(self, client: AsyncClient, session: Session):
        response = await client.put(f"/project/{TEST_NAME}", json={'key': 'invalid'})
        assert response.status_code == 404
        assert response.json()['detail'] == 'Key does not exist'

    @pytest.mark.anyio
    async def test_project_update_does_not_exist(self, client: AsyncClient, session: Session):
        response = await client.put(f"/project/does-not-exist", json=TEST_PROJECT)
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_project_does_not_exist(self, client: AsyncClient, session: Session):
        response = await client.get(f"/project/404")
        assert response.status_code == 404

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_list(self, client: AsyncClient, session: Session):
        response = await client.get('/project')
        data = response.json()
        assert response.status_code == 200
        assert len(data) == 1
        assert type(data) == list
        # for field, item in ProjectDetails.model_fields.items():
        #     if not item.exclude:
        #          assert field in data[0],f'{field} not in {data[0]}'

        assert 'id' in data[0]
        assert data[0]['name'] == TEST_NAME
        assert data[0]['remote'] == TEST_REMOTE
        assert data[0]['branch'] == 'main'
        assert data[0]['key'] == f'pat:{TEST_AUTH_NAME}'
        assert response.status_code == 200

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_update(self, client: AsyncClient, session: Session):
        response = await client.put(f'/project/{TEST_NAME}', json=TEST_PROJECT)
        data = response.json()
        assert 'name' in data.keys()
        assert 'remote' in data.keys()
        assert response.status_code == 200

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_refresh_token(self, client: AsyncClient):
        response = await client.get(f'/project/{TEST_NAME}/refresh-token')
        data = response.json()
        assert response.status_code == 200
        assert data['token']
        assert len(data['token']) == 64

    @pytest.mark.anyio
    async def test_project_refresh_token_invalid(self, client: AsyncClient):
        response = await client.get(f'/project/invalid/refresh-token')
        assert response.status_code == 404
        assert response.json()['detail'] == 'Project not found'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_delete(self, client: AsyncClient):
        response = await client.delete(f'/project/{TEST_NAME}')
        data = response.json()
        assert response.status_code == 200
        assert data['detail'] == f'{TEST_NAME} deleted'

    @pytest.mark.anyio
    async def test_project_delete_does_not_exist(self, client: AsyncClient):
        response = await client.delete(f'/project/404')
        assert response.status_code == 404

    # @pytest.mark.anyio
    # @pytest.mark.dependency()
    # async def test_project_create_100(self, client: AsyncClient):
    #     for i in range(1, 100):
    #         response = await client.post("/project", json=TEST_PROJECT_NO_NAME)
    #         assert response.status_code == 201
