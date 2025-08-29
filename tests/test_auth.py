"""Main Tests"""
from context import *
from canary_cd.models import AuthDetails, AuthDetailsCount
from canary_cd.utils.tasks import generate_ssh_keypair

TEST_AUTH_SSH = {
    "name": "example-ssh-key",
    "auth_type": "ssh",
}

TEST_AUTH_PAT = {
    "name": "example-pat-key",
    "auth_type": "pat",
    "auth_key": "gh_pat"
}

TEST_INVALID_AUTH_TYPE = {
    "name": "example-invalid-type",
    "auth_type": "invalid",
    "auth_key": "gh_pat"
}

TEST_INVALID_AUTH_KEY = {
    "name": "example-invalid-key",
    "auth_type": "pat",
    "auth_key": ""
}


class TestAuthAPI:
    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_auth_create_ssh(self, client: AsyncClient, session: Session):
        """Generate ssh key"""
        response = await client.post("/auth", json=TEST_AUTH_SSH)
        assert response.status_code == 201
        data = response.json()

        for field in ['name', 'auth_type']:
            assert data[field] == TEST_AUTH_SSH[field]

        assert data['public_key'].startswith('ssh-ed2551')
        assert data['public_key'].endswith(TEST_AUTH_SSH['name'])

    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_auth_create_ssh_blank_name(self, client: AsyncClient, session: Session):
        """Generate ssh Key and name"""
        response = await client.post("/auth", json={"name": None, "auth_type": "ssh"})
        assert response.status_code == 201
        data = response.json()
        assert len(data['name']) > 0
        assert len(data['name'].split('-')) == 2
        assert data['public_key'].startswith('ssh-ed25519')

    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_auth_create_ssh_import(self, client: AsyncClient, session: Session):
        """Import ssh key and generate public_key server side"""
        name = 'auth-ssh-import'
        auth_key, public_key = await generate_ssh_keypair(name)
        response = await client.post("/auth", json={"name": name, "auth_type": "ssh", "auth_key": auth_key})
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == name
        assert data['public_key'] == public_key

    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_auth_create_pat(self, client: AsyncClient, session: Session):
        """Create PAT"""
        response = await client.post("/auth", json=TEST_AUTH_PAT)
        assert response.status_code == 201
        data = response.json()
        for field in ['name', 'auth_type']:
            assert data[field] == TEST_AUTH_PAT[field]

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestAuthAPI::test_auth_create_ssh'])
    async def test_auth_create_duplicate(self, client: AsyncClient, session: Session):
        """Fail Create duplicate key"""
        response = await client.post("/auth", json=TEST_AUTH_SSH)
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_auth_create_invalid_auth_type(self, client: AsyncClient, session: Session):
        response = await client.post("/auth", json=TEST_INVALID_AUTH_TYPE)
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_auth_create_empty_auth_key(self, client: AsyncClient, session: Session):
        response = await client.post("/auth", json=TEST_INVALID_AUTH_KEY)
        assert response.status_code == 400
        assert response.json()['detail'] == 'No key provided'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestAuthAPI::test_auth_create_ssh',
                                     'TestAuthAPI::test_auth_create_ssh_blank_name',
                                     'TestAuthAPI::test_auth_create_ssh_import',
                                     'TestAuthAPI::test_auth_create_pat',
                                     ])
    async def test_auth_list(self, client: AsyncClient, session: Session):
        response = await client.get("/auth")
        data = response.json()

        assert len(data) == 4
        for entry in data:
            assert entry['name']
            assert entry['auth_type'] in ['ssh', 'pat']

            # for field in AuthDetails.model_fields.keys():
            #     assert field in data[0]

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestAuthAPI::test_auth_create_ssh'])
    async def test_auth_view(self, client: AsyncClient, session: Session):
        response = await client.get("/auth/{}".format(TEST_AUTH_SSH['name']))
        data = response.json()

        for field in ['name', 'auth_type']:
            assert data[field] == TEST_AUTH_SSH[field]
        assert 'public_key' in data
        assert 'project_count' in data
        assert data['public_key'].startswith('ssh-ed25519')

    @pytest.mark.anyio
    async def test_auth_view_does_not_exist(self, client: AsyncClient, session: Session):
        response = await client.get("/auth/does-not-exist")
        data = response.json()
        assert response.status_code == 404
        assert data['detail'] == 'Key does not exists'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestAuthAPI::test_auth_list', 'TestAuthAPI::test_auth_view'])
    async def test_auth_delete(self, client: AsyncClient, session: Session):
        response = await client.delete("/auth/{}".format(TEST_AUTH_SSH['name']))
        data = response.json()
        assert response.status_code == 200
        assert data['detail'] == '{} deleted'.format(TEST_AUTH_SSH['name'])

    @pytest.mark.anyio
    async def test_auth_delete_non_existing(self, client: AsyncClient, session: Session):
        response = await client.delete("/auth/does-not-exist")
        assert response.status_code == 404
        assert response.json()['detail'] == 'Authentication Key not found'
