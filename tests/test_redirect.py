"""Test Redirects"""
from context import *
from canary_cd.models import PageDetails
from canary_cd.models import RedirectDetails

TEST_SOURCE = 'example.com'
TEST_DEST = 'www.example.com'

class TestRedirectAPI:
    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_redirect_create(self, client: AsyncClient, session: Session):
        response = await client.post("/redirect", json={'source': TEST_SOURCE, 'destination': TEST_DEST})
        assert response.status_code == 201
        data = response.json()
        assert data['source'] == TEST_SOURCE
        # for field in RedirectDetails.model_fields.keys():
        #     assert field in data

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestRedirectAPI::test_redirect_create'])
    async def test_redirect_create_already_exists(self, client: AsyncClient, session: Session):
        response = await client.post("/redirect", json={'source': TEST_SOURCE, 'destination': TEST_DEST})
        assert response.status_code == 403

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestRedirectAPI::test_redirect_create'])
    async def test_redirect_list(self, client: AsyncClient, session: Session):
        response = await client.get('/redirect')
        data = response.json()
        assert response.status_code == 200
        assert len(data) == 1
        assert type(data) == list
        # for field in RedirectDetails.model_fields.keys():
        #     assert field in data[0]

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestRedirectAPI::test_redirect_create'])
    async def test_redirect_delete(self, client: AsyncClient):
        response = await client.delete(f'/redirect/{TEST_SOURCE}')
        data = response.json()
        assert response.status_code == 200
        assert data['detail'] == f'{TEST_SOURCE} deleted'

    @pytest.mark.anyio
    async def test_redirect_delete_does_not_exist(self, client: AsyncClient):
        response = await client.delete(f'/redirect/null.com')
        assert response.status_code == 404
