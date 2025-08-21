"""Main Tests"""
from context import *
from canary_cd.models import AuthDetails, AuthDetailsCount

TEST_AUTH_SSH = {
  "name": "example-name",
  "auth_type": "ssh",
  "auth_key": "ssh-ed25519 ABC"
}

TEST_AUTH_PAT = {
  "name": "example-name",
  "auth_type": "pat",
  "auth_key": "gh_pat"
}

class TestAuthAPI:
    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_auth_create(self, client: AsyncClient, session: Session):
        response = await client.post("/auth", json=TEST_AUTH_SSH)
        assert response.status_code == 201
        data = response.json()

        for field in ['name', 'auth_type']:
            assert data[field] == TEST_AUTH_SSH[field]

        # for field in AuthDetails.model_fields.keys():
        #     assert field in data


    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestAuthAPI::test_auth_create'])
    async def test_auth_list(self, client: AsyncClient, session: Session):
        response = await client.get("/auth")
        data = response.json()

        assert len(data) == 1
        for field in ['name', 'auth_type']:
            assert data[0][field] == TEST_AUTH_SSH[field]

        # for field in AuthDetails.model_fields.keys():
        #     assert field in data[0]


    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestAuthAPI::test_auth_create'])
    async def test_auth_view(self, client: AsyncClient, session: Session):
        response = await client.get("/auth/{}".format(TEST_AUTH_SSH['name']))
        data = response.json()

        for field in ['name', 'auth_type']:
            assert data[field] == TEST_AUTH_SSH[field]

        # for field in AuthDetails.model_fields.keys():
        #     assert field in data

        assert 'project_count' in data

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestAuthAPI::test_auth_list', 'TestAuthAPI::test_auth_view'])
    async def test_auth_delete(self, client: AsyncClient, session: Session):
        response = await client.delete("/auth/{}".format(TEST_AUTH_SSH['name']))
        data = response.json()
        assert response.status_code == 200
        assert data['detail'] == '{} deleted'.format(TEST_AUTH_SSH['name'])
