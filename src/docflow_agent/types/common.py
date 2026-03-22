from dataclasses import dataclass, field


@dataclass(frozen=True)
class FileInfo:
    name: str
    path: str
    content_type: str


@dataclass(frozen=True)
class EcmAuth:
    api_key: str = field(repr=False)
    api_secret: str = field(repr=False)
    access_token: str | None = field(default=None, repr=False)
    tenant_id: str | None = None


@dataclass(frozen=True)
class EcmSearchQuery:
    text: str
    limit: int = 20
    offset: int = 0
    filters: dict[str, str] = field(default_factory=dict)
