import uuid
from datetime import datetime

from fastapi import HTTPException
from typing import Any, Self, Optional, Annotated

from pydantic import BaseModel, Field, computed_field, PlainValidator, ConfigDict
from sqlalchemy.orm import Relationship

from canary_cd.database import Project

FQDN_PATTERN = r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$"
FQDN_EXAMPLES = ['example.com']

NAME_PATTERN = r"^([a-z]{1})[a-z0-9-]+$"
NAME_EXAMPLES = ['project-name']

REPO_PATTERN = r"^(?:(https?|git|ssh):\/\/)?(?:([^@\/:]+)(?::([^@\/:]+))?@)?([^:\/]+)(?::(\d+))?(?:[\/:](.+?))(?:(\.git))?$"
REPO_EXAMPLES = ["git@github.com:namespace/github/repo.git"]

AUTH_KEY_PATTERN = r"^(ssh:|pat:ghp_)[a-zA-Z0-9-]+$"
AUTH_KEY_EXAMPLES = ["ssh:key", "pat:ghp_1234"]


class DateBase(BaseModel):
    created_at: datetime = Field(examples=["1999-12-31T23:59:59.000Z"])
    updated_at: datetime = Field(examples=["2000-01-01T00:00:00.000Z"])


# GitKey
class GitKeyUpdate(BaseModel):
    name: str = Field()


class GitKeyCreate(GitKeyUpdate):
    auth_type: str = Field()
    auth_key: Optional[str] = Field(None)


class GitKeyDetails(GitKeyUpdate, DateBase):
    auth_type: str = Field()
    public_key: str | None = Field()
    projects: Optional[list["Project"]] = Relationship(back_populates="projects")


# Project
class ProjectUpdate(BaseModel):
    key: Optional[str] = Field(None)
    remote: Optional[str] | None = Field(None, examples=REPO_EXAMPLES, pattern=REPO_PATTERN)


class ProjectCreate(ProjectUpdate):
    name: str = Field(min_length=1, max_length=256, pattern=NAME_PATTERN, examples=NAME_EXAMPLES)


class ProjectDetails(DateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field()
    name: str = Field(min_length=1, max_length=256, pattern=NAME_PATTERN, examples=NAME_EXAMPLES)
    remote: Optional[str] | None = Field(None, examples=REPO_EXAMPLES)  # , pattern=REPO_PATTERN)
    git_key: Optional["GitKeyDetails"] = Field()


class ProjectCreatedDetails(ProjectDetails):
    token: str = Field()


# Environment
class EnvUpdate(BaseModel):
    branch: str = Field(min_length=1, max_length=256, pattern=NAME_PATTERN)


class EnvBase(EnvUpdate):
    name: str = Field(min_length=1, max_length=256, pattern=NAME_PATTERN)


class EnvDetails(EnvBase, DateBase):
    pass


# Environment Variable
class VariableBase(BaseModel):
    key: str = Field(min_length=1, max_length=256, pattern=r"^[A-Z0-9_]+$", examples=["FOO"])


class VariableUpdate(VariableBase):
    value: str = Field(min_length=1, max_length=1024, examples=["value"])


class VariableDetails(VariableBase, DateBase):
    id: uuid.UUID = Field()
    environment_id: uuid.UUID = Field()


class VariableValueDetails(VariableDetails):
    value: str | None = Field()


# Page
class PageBase(BaseModel):
    fqdn: str = Field(min_length=1, max_length=256, pattern=FQDN_PATTERN)


# class PageUpdate(BaseModel):
# target: str = Field(min_length=1, max_length=256, pattern=r"^[a-z0-9-]+$")
# redirects: Optional[list[str]] = Field(default=None)


# class PageCreate(PageBase, PageUpdate):
#     pass

class PageDetails(PageBase, DateBase):
    id: uuid.UUID = Field()
    # redirects: list[PageBase] = Field(default=None)


# Redirect
class RedirectBase(BaseModel):
    source: str = Field(min_length=1, max_length=256, pattern=FQDN_PATTERN, examples=FQDN_EXAMPLES)
    destination: str = Field(min_length=1, max_length=256, pattern=FQDN_PATTERN, examples=FQDN_EXAMPLES)


class RedirectCreate(RedirectBase):
    pass


class RedirectUpdate(BaseModel):
    destination: str = Field(min_length=1, max_length=256, pattern=FQDN_PATTERN, examples=FQDN_EXAMPLES)


class RedirectDetails(RedirectBase, DateBase):
    id: uuid.UUID = Field()
