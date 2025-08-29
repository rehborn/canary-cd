"""Config Tests"""

from context import *
from canary_cd.models import ConfigUpdate

CONFIG_KEY = 'DISCORD_WEBHOOK'
CONFIG_VALUE = 'https://discord.com/api/webhooks/test/test'
TEST_CONFIG = {'key': CONFIG_KEY, 'value': CONFIG_VALUE}
TEST_CONFIG_INVALID = {'key': 'invalid-key', 'value': 'value'}
TEST_CONFIG_ROOT_KEY = {'key': 'ROOT_KEY', 'value': 'test'}


class TestConfigAPI:
    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_config_set(self, client: AsyncClient, session: Session):
        response = await client.put("/config", json=TEST_CONFIG)
        data = response.json()
        assert data['key'] == CONFIG_KEY
        assert data['value'] == CONFIG_VALUE
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_config_set_invalid_key(self, client: AsyncClient, session: Session):
        response = await client.put("/config", json=TEST_CONFIG_INVALID)
        data = response.json()
        assert response.status_code == 403
        assert data['detail'] == 'Invalid Config key'

    @pytest.mark.anyio
    async def test_config_set_root_key(self, client: AsyncClient, session: Session):
        response = await client.put("/config", json=TEST_CONFIG_ROOT_KEY)
        data = response.json()
        assert response.status_code == 200
        assert data['key'] == 'ROOT_KEY'

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestConfigAPI::test_config_set'])
    async def test_config_list(self, client: AsyncClient, session: Session):
        response = await client.get("/config")
        data = response.json()

        assert len(data) == 1
        assert data[0]['key'] == CONFIG_KEY
        assert data[0]['value'] == CONFIG_VALUE
        # for field in ConfigUpdate.model_fields.keys():
        #     assert field in data[0]

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestConfigAPI::test_config_list'])
    async def test_config_delete(self, client: AsyncClient, session: Session):
        response = await client.delete(f"/config/{CONFIG_KEY}")
        data = response.json()

        assert response.status_code == 200
        assert data['detail'] == f'{CONFIG_KEY} deleted'

    @pytest.mark.anyio
    async def test_config_delete_root_key(self, client: AsyncClient, session: Session):
        response = await client.delete(f"/config/ROOT_KEY")
        data = response.json()

        assert response.status_code == 403
        assert data['detail'] == 'ROOT_KEY cannot be deleted'

    @pytest.mark.anyio
    async def test_config_delete_invalid(self, client: AsyncClient, session: Session):
        response = await client.delete(f"/config/does-not-exist")
        data = response.json()

        assert response.status_code == 404
        assert data['detail'] == 'does-not-exist not found'