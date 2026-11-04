from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class V2BaseModel(BaseModel):
    model_config = {
        'str_strip_whitespace': True,
    }


class CreateThreadRequest(V2BaseModel):
    title: str = Field(min_length=1, max_length=255)


class PostMessageRequest(V2BaseModel):
    thread_id: str
    provider: str = Field(min_length=1)
    content: str = Field(min_length=1)

    @field_validator('provider')
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        if not value:
            raise ValueError('provider cannot be empty')
        return value.lower()


class ApprovalDecisionRequest(V2BaseModel):
    decision: str


class KnowledgeAssetIngestRequest(V2BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_type: str = 'note'
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class McpToolCallRequest(V2BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class McpResourceReadRequest(V2BaseModel):
    uri: str
