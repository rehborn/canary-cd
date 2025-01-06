import os
import tempfile

import pytest
import sys
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
import logging


logger = logging.getLogger(__name__)

# Overwrite auto generation for SALT and API_KEY settings
SALT='DWlKl7lBstE5M/FEv0v6Fx53nZDF0jJkLMURflbIRSw='
ROOT_KEY = 'test'

os.environ.setdefault('SALT', SALT)
os.environ.setdefault('ROOT_KEY', ROOT_KEY)

temp = tempfile.TemporaryDirectory(delete=False)
logger.debug(f'DATA_DIR: {temp.name}')

os.environ.setdefault('DATA_DIR', temp.name)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from canary_cd.main import app  # pylint: disable=import-error,wrong-import-position
from canary_cd.database import *
from canary_cd.utils.crypto import CryptoHelper

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override  # noqa
    headers = {"Authorization": f"Bearer {ROOT_KEY}"}
    client = TestClient(app, headers=headers)
    yield client
    app.dependency_overrides.clear()  # noqa


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    db = Session(engine)

    # set initial ROOT_KEY
    root_key = Config(key='ROOT_KEY', value=CryptoHelper(SALT).hash(ROOT_KEY))
    db.add(root_key)
    db.commit()
    return db
    # create_db_and_tables()
    # with Session(engine) as session:
    #     yield session
#
#
# headers = {"Authorization": f"Bearer {ROOT_KEY}"}
# client = TestClient(app, headers=headers)
