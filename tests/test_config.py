"""Config Tests"""

from context import *
from canary_cd.models import ConfigUpdate

CONFIG_KEY = 'DISCORD_WEBHOOK'
CONFIG_VALUE = 'https://discord.com/api/webhooks/test/test'
TEST_CONFIG = {'key': CONFIG_KEY, 'value': CONFIG_VALUE}


class TestConfigAPI:
    @pytest.mark.anyio
    @pytest.mark.dependency()
    async def test_config_create(self, client: AsyncClient, session: Session):
        response = await client.put("/config", json=TEST_CONFIG)
        data = response.json()

        # for field in ConfigUpdate.model_fields.keys():
        #     assert field in data

        assert data['key'] == CONFIG_KEY
        assert data['value'] == CONFIG_VALUE
        assert response.status_code == 200

    @pytest.mark.anyio
    @pytest.mark.dependency(depends=['TestConfigAPI::test_config_create'])
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
