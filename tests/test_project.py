"""Project Test"""
from context import *
from canary_cd.models import ProjectDetails

TEST_NAME = "test"
TEST_REMOTE = 'git@github.com/github/example.git'
TEST_PROJECT = {'name': TEST_NAME, 'remote': TEST_REMOTE, 'branch': 'main'}

class TestProjectAPI:
    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_project_create(self, client: AsyncClient, session: Session):
        response = await client.post("/project", json=TEST_PROJECT)
        data = response.json()
        assert 'name' in data.keys()
        assert 'remote' in data.keys()
        assert response.status_code == 201

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
            assert data[0]['key'] is None
            assert response.status_code == 200


    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_update(self, client: AsyncClient, session: Session):
        response = await client.put(f'/project/{TEST_NAME}', json=TEST_PROJECT)
        # data = response.json()
        # assert 'name' in data.keys()
        # assert 'remote' in data.keys()
        # assert response.status_code == 200


    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestProjectAPI::test_project_create'])
    async def test_project_refresh_token(self, client: AsyncClient):
        response = await client.get(f'/project/{TEST_NAME}/refresh-token')
        data = response.json()
        assert response.status_code == 200
        assert data['token']
        assert len(data['token']) == 64

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
