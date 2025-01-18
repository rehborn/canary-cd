import os
import uuid
from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import Depends
from sqlmodel import SQLModel, Field, DateTime, TIMESTAMP, JSON, ARRAY, Column, String
from sqlmodel import Session, create_engine, select, column, asc, desc
from sqlmodel import UniqueConstraint, Relationship

from canary_cd.settings import SALT, SQLITE, logger
from canary_cd.utils.crypto import random_string, CryptoHelper


def now() -> datetime:
    return datetime.now(timezone.utc)


class Config(SQLModel, table=True):
    """
    Daemon configuration
    """
    key: str = Field(index=True, primary_key=True, unique=True, min_length=1, max_length=32)
    value: str = Field(min_length=1, max_length=64)


class Auth(SQLModel, table=True):
    """
    Authentication for Pulling Repositories
    - can be assigned to several Projects
    - can hold SSH Privat/Public Keys and GitHub PAT

    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, unique=True)

    name: str = Field(index=True, unique=True, nullable=False, min_length=1, max_length=256)
    auth_type: str = Field()  # ssh, pat, token, app
    nonce: str = Field()
    ciphertext: str = Field()
    public_key: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, sa_column_kwargs={"onupdate": now})

    projects: list["Project"] = Relationship(back_populates="auth")


class Project(SQLModel, table=True):
    """
    Projects can assign a single remote and a matching Key
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, unique=True)

    name: str = Field(index=True, unique=True, nullable=False, min_length=1, max_length=256)
    remote: str | None = Field(default=None, nullable=True)
    branch: str | None = Field(default='main', min_length=1, max_length=256)

    auth_id: uuid.UUID | None = Field(default=None, foreign_key="auth.id", nullable=True)
    auth: Auth | None = Relationship(back_populates="projects")

    token: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, sa_column_kwargs={"onupdate": now})

    secrets: list["Secret"] = Relationship(back_populates="project", cascade_delete=True)


class Secret(SQLModel, table=True):
    """
    Secrets are AES-GCM encrypted
    """
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="project_id_and_secret_key_unique"),
    )
    project_id: uuid.UUID | None = Field(default=None, foreign_key="project.id", primary_key=True)
    project: Project | None = Relationship(back_populates="secrets")

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
