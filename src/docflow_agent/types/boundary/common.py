from pydantic import Field

from docflow_agent.types.boundary.base import BoundaryModel


class FileInfo(BoundaryModel):
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content_type: str = Field(min_length=1)


class EcmAuth(BoundaryModel):
    api_key: str = Field(min_length=1, repr=False)
    api_secret: str = Field(min_length=1, repr=False)
    access_token: str | None = Field(default=None, repr=False)
    tenant_id: str | None = Field(default=None, min_length=1)


class EcmSearchQuery(BoundaryModel):
    text: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1)
    offset: int = Field(default=0, ge=0)
    filters: dict[str, str] = Field(default_factory=dict)
