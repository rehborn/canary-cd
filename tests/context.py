import os
import tempfile

import pytest
import sys
from httpx import ASGITransport, AsyncClient
import logging

ROOT_KEY = 'test'
os.environ['ROOT_KEY'] = ROOT_KEY
os.environ['HTTPD_CONFIG_DUMP'] = '1'

temp = tempfile.TemporaryDirectory(delete=True)
os.environ['DATA_DIR'] = temp.name

from canary_cd import settings
from canary_cd.main import lifespan

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from canary_cd.main import app  # pylint: disable=import-error,wrong-import-position
from canary_cd.database import *


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(name="client", scope="session")
async def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override  # noqa
    headers = {"Authorization": f"Bearer {ROOT_KEY}"}
    transport = ASGITransport(app=app)
    async with lifespan(app):
        async with AsyncClient(transport=transport, headers=headers, base_url="http://test") as client:
            yield client
    app.dependency_overrides.clear()  # noqa


@pytest.fixture(name="session", scope="session")
async def session_fixture():
    sqlite = 'sqlite:///{}/database.sqlite'.format(settings.DATA_DIR.absolute())
    engine = create_engine(
        sqlite,
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
