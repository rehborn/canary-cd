import io
import tarfile

from context import *

TEST_FQDN = 'webhook-test.com'
TEST_NAME = 'webhook-test'
TEST_REMOTE = 'git@github.com:github/gitignore.git'
TEST_PROJECT = {'name': TEST_NAME, 'remote': TEST_REMOTE, 'branch': 'main'}

class TestWebhookAPI:
    @pytest.fixture(scope='function')
    def create_project_dummy(self, session: Session):
        project = Project(**TEST_PROJECT)
        session.add(project)
        session.commit()

    @pytest.mark.anyio
    @pytest.mark.usefixtures('create_project_dummy')
    async def test_project_webhook(self, client: AsyncClient, session: Session):
        response = await client.get(f'/project/{TEST_NAME}/refresh-token')
        token = response.json()['token']
        response = await client.post(f'/webhook/project/{token}')
        assert response.json()['detail'] == f"deployment started {TEST_NAME}"

    @pytest.mark.anyio
    async def test_project_invalid_webhook(self, client: AsyncClient, session: Session):
        response = await client.post(f'/webhook/project/invalid-token')
        assert response.status_code == 404
        assert response.json()['detail'] == 'Project not found'

    @pytest.mark.anyio
    async def test_page_webhook_invalid(self, client: AsyncClient, session: Session):
        response = await client.post(f"/webhook/page/invalid-token", content='')
        assert response.status_code == 403
        assert response.json()['detail'] == 'Page not found'

    @pytest.mark.anyio
    async def test_page_webhook(self, client: AsyncClient, session: Session):
        # create page
        await client.post("/page", json={'fqdn': TEST_FQDN})

        # refresh token
        response = await client.get(f'/page/{TEST_FQDN}/refresh-token')
        token = response.json()['token']

        # create payload archive including index.html
        payload = io.BytesIO()
        with tarfile.open('payload.tar.bz2', 'w|bz2', fileobj=payload) as t:
            b = 'test'.encode('utf-8')
            tarinfo = tarfile.TarInfo('index.html')
            tarinfo.size = len(b)
            t.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(b))
        payload.seek(0)

        # upload
        response = await client.post(f"/webhook/page/{token}", content=payload.read())
        assert response.status_code == 200
        assert response.json()['detail'] == f"{TEST_FQDN} uploaded"

        with open (settings.PAGES_CACHE / TEST_FQDN / 'index.html', 'r') as f:
            assert f.read() == 'test'
