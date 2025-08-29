from context import *

TEST_FQDN = 'export-test.com'


class TestExportAPI:
    @pytest.fixture()
    def create_page_dummy(self, session: Session):
        page = Page(**{'fqdn': TEST_FQDN})
        session.add(page)
        session.commit()

    @pytest.mark.anyio
    @pytest.mark.usefixtures('create_page_dummy')
    async def test_export_traefik_json(self, client: AsyncClient):
        response = await client.get('/export/traefik.json')
        assert response.status_code == 200
        data = response.json()

        assert 'http' in data
        assert type(data['http']) == dict
        for field in ['routers', 'services']:
            assert field in data['http']

        assert data['http']['routers'].get(f'backend-router-{TEST_FQDN}')

        for field in ['service', 'rule', 'entryPoints', 'tls']:
            assert field in data['http']['routers'][f'backend-router-{TEST_FQDN}']

        assert data['http']['routers'][f'backend-router-{TEST_FQDN}']['rule'] == f'Host(`{TEST_FQDN}`)'
        assert data['http']['services'].get('backend-service-static-pages')
        assert type(data['http']['services']['backend-service-static-pages']['loadBalancer']['servers']) == list
