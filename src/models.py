"""Data model. Pydantic rejects anything outside the allowed values."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator

Evidence = Literal["Verified", "Partially Verified", "Unverified", "Pending"]
Access = Literal["Self-serve", "Paid plan required", "Approval required", "Contact sales / partner", "Unknown"]
Buildability = Literal["Easy", "Medium", "Difficult", "Not Feasible", "Unknown"]
Mcp = Literal["Official", "Community", "None found", "Unknown"]
BlockerType = Literal["None", "Partner / approval gate", "Paid plan", "No public API",
                      "Complex auth", "Rate limits / quotas", "Other", "Unknown"]
AuthMethod = Literal["OAuth2", "API key", "Bearer token", "Basic", "JWT", "Other", "Unknown"]
ApiType = Literal["REST", "GraphQL", "SOAP", "gRPC", "SDK/CLI only", "Other", "Unknown"]


class App(BaseModel):
    id: int
    name: str
    category: str
    domain_hint: str = ""


class AppResearch(BaseModel):
    app_id: int
    name: str
    category: str
    description: str = "Unknown"
    auth_methods: list[AuthMethod] = Field(default_factory=lambda: ["Unknown"])
    access: Access = "Unknown"
    api_types: list[ApiType] = Field(default_factory=lambda: ["Unknown"])
    api_breadth: str = "Unknown"
    mcp: Mcp = "Unknown"
    mcp_url: str = ""
    auth_sources: list[str] = Field(default_factory=list)
    api_sources: list[str] = Field(default_factory=list)
    mcp_sources: list[str] = Field(default_factory=list)
    buildability: Buildability = "Unknown"
    blocker_type: BlockerType = "Unknown"
    blocker: str = "Unknown"
    sources: list[str] = Field(default_factory=list)
    evidence: Evidence = "Pending"
    notes: str = ""
    pass_number: int = 1
    human_corrected_fields: list[str] = Field(default_factory=list)
    researched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @field_validator("sources", "auth_sources", "api_sources", "mcp_sources")
    @classmethod
    def sources_must_be_urls(cls, v: list[str]) -> list[str]:
        clean = []
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"not a URL: {url}")
            if url not in clean:
                clean.append(url)
        return clean
