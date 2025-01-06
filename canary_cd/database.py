import os
import uuid
from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import Depends
from sqlmodel import SQLModel, Field, DateTime, TIMESTAMP, JSON, ARRAY, Column, String
from sqlmodel import Session, create_engine, select, col
from sqlmodel import UniqueConstraint, Relationship

from canary_cd.settings import SALT, SQLITE, logger
from canary_cd.utils.crypto import random_string, CryptoHelper

CONFIG_KEYS = [
    'ROOT_KEY',

    # not implemented
    # Notification Config
    'SLACK_WEBHOOK',
    'DISCORD_WEBHOOK',

    # GitHub App Config
    'GITHUB_APP_ID',
    'GITHUB_SECRET_FILE',
    'GITHUB_WEBHOOK_SECRET',
]

AUTH_TYPES = [
    "ssh",
    "pat",
    "token"
]


def now() -> datetime:
    return datetime.now(timezone.utc)


class Config(SQLModel, table=True):
    """
    Daemon configuration
    """
    key: str = Field(index=True, primary_key=True, unique=True, min_length=1, max_length=32)
    value: str = Field(min_length=1, max_length=64)


class GitKey(SQLModel, table=True):
    """
    GitKey for Pulling Repositories
    can be assigned to several Projects
    can hold SSH Privat/Public Keys and GitHub PAT
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, unique=True)

    name: str = Field(index=True, unique=True, nullable=False, min_length=1, max_length=256)
    auth_type: str = Field()  # ssh, pat, token, app
    nonce: str = Field()
    ciphertext: str = Field()
    public_key: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, sa_column_kwargs={"onupdate": now})

    projects: list["Project"] = Relationship(back_populates="git_key")


class Project(SQLModel, table=True):
    """
    Projects can assign a single remote and a matching Key
    several Environments can be assigned to a single Project
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, unique=True)

    name: str = Field(index=True, unique=True, nullable=False, min_length=1, max_length=256)
    remote: str | None = Field(default=None, nullable=True)

    git_key_id: uuid.UUID | None = Field(default=None, foreign_key="gitkey.id", nullable=True)
    git_key: GitKey | None = Relationship(back_populates="projects")

    token: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, sa_column_kwargs={"onupdate": now})

    environments: list["Environment"] = Relationship(back_populates="project", cascade_delete=True)


class Environment(SQLModel, table=True):
    """
    Environments are assigned to branches and have their own set of Environment Variables
    """
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="project_and_env_name_unique"),
    )
    project_id: uuid.UUID | None = Field(default=None, foreign_key="project.id", primary_key=True)
    project: Project | None = Relationship(back_populates="environments")

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, unique=True)

    name: str = Field(index=True, nullable=False, min_length=1, max_length=256, default='default')
    branch: str | None = Field(default='main', min_length=1, max_length=256)

    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, sa_column_kwargs={"onupdate": now})

    variables: list["Variable"] = Relationship(back_populates="environment", cascade_delete=True)


class Variable(SQLModel, table=True):
    """
    Environment Variables are AES-GCM encrypted
    """
    __table_args__ = (
        UniqueConstraint("environment_id", "key", name="environment_and_key_unique"),
    )
    environment_id: uuid.UUID = Field(default=None, foreign_key="environment.id", primary_key=True)
    environment: Environment | None = Relationship(back_populates="variables")

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, unique=True)

    key: str = Field(min_length=1, max_length=256)
    nonce: str = Field()
    ciphertext: str = Field()

    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, sa_column_kwargs={"onupdate": now})


class Page(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fqdn: str = Field(unique=True)
    token: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, sa_column_kwargs={"onupdate": now})


class Redirect(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source: str = Field(unique=True)
    destination: str = Field()
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, sa_column_kwargs={"onupdate": now})


_connect_args = {"check_same_thread": False}
_engine = create_engine(SQLITE, connect_args=_connect_args)


async def create_db_and_tables():
    SQLModel.metadata.create_all(_engine)

    db = Session(_engine)

    # set initial ROOT_KEY
    q = select(Config).where(Config.key == 'ROOT_KEY')
    root_key = db.exec(q).first()

    if not root_key:
        key = os.environ.get("ROOT_KEY", random_string())
        root_key = Config(key='ROOT_KEY', value=CryptoHelper(SALT).hash(key))
        db.add(root_key)
        db.commit()
        logger.info(f"\nAPI_KEY {key}")


def get_session():
    with Session(_engine) as session:
        yield session


Database = Annotated[Session, Depends(get_session)]
