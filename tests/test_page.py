"""Page Tests"""
from context import *
from canary_cd.models import PageDetails

TEST_FQDN = 'example.com'
TEST_CORS = 'https://example2.com'


def create_page(session: Session, data: dict) -> Page:
    page = Page(**data)
    session.add(page)
    session.commit()
    session.refresh(page)
    return page

class TestPageAPI:
    # @pytest.fixture
    # def page(self, session: Session):
    #     logger.debug("fixture")
    #     page = create_page(session, {'fqdn': TEST_FQDN})

    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_page_create(self, client: AsyncClient, session: Session):
        response = await client.post("/page", json={'fqdn': TEST_FQDN})
        assert response.status_code == 201
        data = response.json()
        assert data['fqdn'] == TEST_FQDN
        # for field in PageDetails.model_fields.keys():
        #     assert field in data

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestPageAPI::test_page_create'])
    async def test_page_create_already_exists(self, client: AsyncClient, session: Session):
        response = await client.post("/page", json={'fqdn': TEST_FQDN})
        assert response.status_code == 403

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestPageAPI::test_page_create'])
    async def test_page_view(self, client: AsyncClient, session: Session):
        response = await client.get(f"/page/{TEST_FQDN}")
        assert response.status_code == 200
        data = response.json()
        assert data['fqdn'] == TEST_FQDN
        # for field in PageDetails.model_fields.keys():
        #     assert field in data

    @pytest.mark.anyio
    async def test_page_does_not_exist(self, client: AsyncClient, session: Session):
        response = await client.get(f"/page/null.com")
        assert response.status_code == 404

    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_page_create_with_cors(self, client: AsyncClient, session: Session):
        """Create a Page with a CORS Hosts"""
        response = await client.post("/page", json={'fqdn': 'example3.com', 'cors_hosts': TEST_CORS})
        data = response.json()
        assert response.status_code == 201
        assert data['fqdn'] == 'example3.com'
        assert data['cors_hosts'] == TEST_CORS

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestPageAPI::test_page_create', 'TestPageAPI::test_page_create_with_cors'])
    async def test_page_list(self, client: AsyncClient, session: Session):
        response = await client.get('/page')
        data = response.json()
        assert response.status_code == 200
        assert len(data) == 2
        assert type(data) == list
        # for field in PageDetails.model_fields.keys():
        #     assert field in data[0]

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestPageAPI::test_page_create'])
    async def test_page_refresh_token(self, client: AsyncClient):
        response = await client.get(f'/page/{TEST_FQDN}/refresh-token')
        data = response.json()
        assert response.status_code == 200
        assert data['token']
        assert len(data['token']) == 64

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestPageAPI::test_page_create'])
    async def test_page_delete(self, client: AsyncClient):
        response = await client.delete(f'/page/{TEST_FQDN}')
        data = response.json()
        assert response.status_code == 200
        assert data['detail'] == f'{TEST_FQDN} deleted'

    @pytest.mark.anyio
    async def test_page_delete_does_not_exist(self, client: AsyncClient):
        response = await client.delete(f'/page/null.com')
        assert response.status_code == 404
