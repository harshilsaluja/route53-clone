"""Shared pagination metadata for resource lists."""

from pydantic import BaseModel, Field


class PaginationMetadata(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)
