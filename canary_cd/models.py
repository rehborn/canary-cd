import uuid
from datetime import datetime
from typing import Any, Self, Optional, Annotated

from pydantic import BaseModel, Field, computed_field, PlainValidator, ConfigDict, field_validator, field_serializer

from canary_cd.utils.pattern import *


class DateBase(BaseModel):
    created_at: datetime = Field(examples=["1999-12-31T23:59:59.000Z"])
    updated_at: datetime = Field(examples=["2000-01-01T00:00:00.000Z"])

# Config
class ConfigUpdate(BaseModel):
    key: str = Field(examples=CONFIG_KEYS)
    value: str = Field(examples=['config-value'])

# Authentication
class AuthUpdate(BaseModel):
    name: Optional[str] = Field(min_length=1, max_length=256, pattern=NAME_PATTERN, examples=NAME_EXAMPLES)


class AuthCreate(AuthUpdate):
    auth_type: str = Field(examples=AUTH_TYPES)
    auth_key: Optional[str] = Field(None, pattern=AUTH_KEY_PATTERN, examples=AUTH_KEY_EXAMPLES)


class AuthDetails(AuthUpdate, DateBase):
    auth_type: str = Field(examples=['ssh'])
    public_key: str | None = Field(examples=PUBLIC_KEY_EXAMPLES)


class AuthDetailsCount(AuthDetails, DateBase):
    projects: Optional[list["ProjectCreate"]] = Field(exclude=True)
    project_count: Optional[int] = Field(None)

    @field_serializer('project_count')
    def project_count(self, value: Any) -> int:
        return len(self.projects)


# Project
class ProjectUpdate(BaseModel):
    remote: Optional[str] | None = Field(None, examples=REPO_EXAMPLES, pattern=single_pattern(GIT_REPO_PATTERN))
    branch: Optional[str] = Field(None, examples=['main'])
    key: Optional[str] = Field(None, examples=['key-name'])


class ProjectCreate(ProjectUpdate):
    name: Optional[str] = Field(min_length=1, max_length=256, pattern=NAME_PATTERN, examples=NAME_EXAMPLES)


class ProjectDetails(DateBase):
    id: uuid.UUID = Field()
    name: str = Field(min_length=1, max_length=256, pattern=NAME_PATTERN, examples=NAME_EXAMPLES)
    remote: Optional[str] | None = Field(None, examples=REPO_EXAMPLES)  # , pattern=REPO_PATTERN)
    branch: Optional[str] = Field(None, examples=['main'])
    auth_id: Optional[uuid.UUID] | None = Field()
    auth: Optional["AuthCreate"] | None = Field(exclude=True)
    key: Optional[str] = Field(None, examples=['key-name'])

    @field_serializer('key')
    def serialize(self, value: Any):
        if self.auth:
            return f'{self.auth.auth_type}:{self.auth.name}'


class ProjectCreatedDetails(ProjectDetails):
    token: str = Field()


# Secret/Environment Variables
class VariableBase(BaseModel):
    key: str = Field(min_length=1, max_length=256, pattern=r"^[A-Z0-9_]+$", examples=["HOST"])


class VariableUpdate(VariableBase):
    value: str = Field(min_length=1, max_length=1024, examples=["example.com"])


class VariableDetails(VariableBase, DateBase):
    id: uuid.UUID = Field()
    # project_id: uuid.UUID = Field()


class VariableValueDetails(VariableDetails):
    value: str | None = Field()


# Page
class PageCreate(BaseModel):
    fqdn: str = Field(min_length=1, max_length=256, pattern=FQDN_PATTERN, examples=FQDN_EXAMPLES)
    cors_hosts: str | None = Field(None)

class PageDetails(PageCreate, DateBase):
    id: uuid.UUID = Field()

# Redirect
class RedirectCreate(BaseModel):
    source: str = Field(min_length=1, max_length=256, pattern=FQDN_PATTERN, examples=[FQDN_EXAMPLES[1]])
    destination: str = Field(min_length=1, max_length=256, pattern=FQDN_PATTERN, examples=FQDN_EXAMPLES)

class RedirectUpdate(BaseModel):
    destination: str = Field(min_length=1, max_length=256, pattern=FQDN_PATTERN, examples=FQDN_EXAMPLES)


class RedirectDetails(RedirectCreate, DateBase):
    id: uuid.UUID = Field()
