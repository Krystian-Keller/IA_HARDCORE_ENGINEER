from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Route = Literal["knowledge_getnet", "knowledge_web", "customer_support"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: NonEmptyText = Field(max_length=5000)
    user_id: NonEmptyText = Field(max_length=100)


class ChatResponse(BaseModel):
    answer: NonEmptyText
    agents_used: list[str]
    tools_used: list[str]
    sources: list[str] = Field(default_factory=list)


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    route: Route


class ToolDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tools: list[Literal["get_customer_profile", "get_customer_activity"]] = Field(
        min_length=1, max_length=2
    )


class Chunk(BaseModel):
    text: NonEmptyText
    source: HttpUrl


class SearchResult(BaseModel):
    title: NonEmptyText
    snippet: NonEmptyText
    url: HttpUrl


class AppError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
