"""
LLM Gateway API routes
"""
import time
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from openai import APIError, APITimeoutError

from app.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    HealthResponse
)
from app.services.llm_client import llm_client
from app.services.cache import llm_cache
from app.services.circuit_breaker import circuit_breaker
from app.services.rate_limiter import rate_limiter
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    """
    Create chat completion (OpenAI-compatible)

    Supports:
    - Request-response mode (stream=false)
    - Streaming mode (stream=true) via SSE
    - Redis caching
    - Circuit breaker protection
    - Rate limiting
    """

    # Check circuit breaker
    if settings.circuit_breaker_enabled and circuit_breaker.is_open():
        logger.error("Circuit breaker is OPEN - rejecting request")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service is temporarily unavailable"
        )

    # Rate limiting
    if settings.rate_limit_enabled:
        try:
            await rate_limiter.acquire()
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, please slow down"
            )

    model = request.model or settings.vitte_llm_model

    # Streaming mode
    if request.stream and settings.streaming_enabled:
        return StreamingResponse(
            stream_completion(request, model),
            media_type="text/event-stream"
        )

    # Non-streaming mode with cache
    try:
        # Check cache
        if settings.cache_enabled:
            cached_response = await llm_cache.get(
                request.messages,
                model,
                request.temperature
            )
            if cached_response:
                circuit_breaker.record_success()
                return build_response(cached_response, model, from_cache=True)

        # Call LLM
        response_text = await llm_client.complete(
            messages=request.messages,
            model=model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            repetition_penalty=request.repetition_penalty,
            frequency_penalty=request.frequency_penalty
        )

        # Cache response
        if settings.cache_enabled:
            await llm_cache.set(
                request.messages,
                model,
                request.temperature,
                response_text
            )

        # Record success
        circuit_breaker.record_success()

        return build_response(response_text, model, from_cache=False)

    except (APITimeoutError, APIError) as e:
        logger.error(f"LLM API error: {e}")
        circuit_breaker.record_failure()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        circuit_breaker.record_failure()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def stream_completion(request: ChatCompletionRequest, model: str):
    """
    Stream chat completion chunks via Server-Sent Events

    Yields:
        str: SSE formatted chunks (data: {...})
    """
    import json
    import uuid

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())

    try:
        async for chunk_text in llm_client.complete_stream(
            messages=request.messages,
            model=model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        ):
            # Format as SSE chunk
            chunk_data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": chunk_text},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"

        # Final chunk with finish_reason
        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

        circuit_breaker.record_success()

    except (APITimeoutError, APIError) as e:
        logger.error(f"Stream error: {e}")
        circuit_breaker.record_failure()
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "api_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"


def build_response(
    content: str,
    model: str,
    from_cache: bool = False
) -> ChatCompletionResponse:
    """Build chat completion response"""
    import uuid

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(time.time()),
        model=model,
        choices=[
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }
        ],
        usage={
            "prompt_tokens": 0,  # We don't track tokens separately
            "completion_tokens": 0,
            "total_tokens": 0,
            "from_cache": from_cache
        }
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service=settings.service_name
    )


@router.get("/metrics")
async def get_metrics():
    """Get service metrics"""
    return {
        "circuit_breaker": circuit_breaker.get_state(),
        "rate_limiter": rate_limiter.get_state(),
        "cache_enabled": settings.cache_enabled,
        "streaming_enabled": settings.streaming_enabled
    }
