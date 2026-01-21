"""
Chat completion schemas (OpenAI-compatible)
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message"""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request"""
    messages: List[Message]
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: bool = False


class ChatCompletionChunk(BaseModel):
    """Streaming chunk"""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[dict]


class ChatCompletionResponse(BaseModel):
    """Chat completion response"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]
    usage: dict


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str = "1.0.0"
