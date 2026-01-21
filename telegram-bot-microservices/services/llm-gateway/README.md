# LLM Gateway

Production-ready LLM gateway service for DeepSeek integration with caching, retry logic, circuit breaker, and streaming support.

## Features

- ✅ **Retry logic** - 3 attempts with exponential backoff
- ✅ **Redis caching** - 1 hour TTL for identical prompts
- ✅ **Circuit breaker** - Protects against cascading failures
- ✅ **Rate limiting** - Token bucket (100 req/min)
- ✅ **Streaming support** - Real-time response via SSE
- ✅ **Health checks** - `/health` and `/metrics` endpoints
- ✅ **OpenAI-compatible API** - Drop-in replacement

---

## API Endpoints

### POST `/v1/chat/completions`

Chat completion (OpenAI-compatible)

**Request:**
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello!"}
  ],
  "model": "deepseek/deepseek-v3.2",
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Response (non-streaming):**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1705920000,
  "model": "deepseek/deepseek-v3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "from_cache": false
  }
}
```

**Streaming mode** (`stream: true`):
Returns Server-Sent Events (SSE):
```
data: {"id":"chatcmpl-abc123","choices":[{"delta":{"content":"Hello"}}]}
data: {"id":"chatcmpl-abc123","choices":[{"delta":{"content":"!"}}]}
data: {"id":"chatcmpl-abc123","choices":[{"delta":{},"finish_reason":"stop"}]}
data: [DONE]
```

---

### GET `/health`

Health check

**Response:**
```json
{
  "status": "healthy",
  "service": "llm-gateway",
  "version": "1.0.0"
}
```

---

### GET `/metrics`

Service metrics

**Response:**
```json
{
  "circuit_breaker": {
    "state": "closed",
    "failure_count": 0,
    "failure_threshold": 5
  },
  "rate_limiter": {
    "rate": 100,
    "tokens_available": 98.5
  },
  "cache_enabled": true,
  "streaming_enabled": true
}
```

---

## Configuration

Environment variables (see `.env`):

```bash
# Service
SERVICE_NAME=llm-gateway
HOST=0.0.0.0
PORT=8001

# DeepSeek via ProxyAPI
PROXYAPI_API_KEY=sk-...
OPENROUTER_BASE_URL=https://api.proxyapi.ru/openrouter/v1
VITTE_LLM_MODEL=deepseek/deepseek-v3.2

# Redis cache
REDIS_URL=redis://redis:6379/1
CACHE_TTL=3600
CACHE_ENABLED=true

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_ENABLED=true

# Circuit breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
CIRCUIT_BREAKER_ENABLED=true

# Streaming
STREAMING_ENABLED=true
```

---

## Architecture

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐
│   Bot   │────▶│ LLM Gateway  │────▶│ DeepSeek API │
└─────────┘     │              │     └──────────────┘
                │  - Cache     │
┌─────────┐     │  - Retry     │
│   API   │────▶│  - Circuit   │
└─────────┘     │  - Rate Lim  │
                └──────┬───────┘
                       │
                   ┌───▼────┐
                   │  Redis │
                   └────────┘
```

---

## Usage from Bot/API

```python
import httpx

# Non-streaming
async def get_llm_response(messages: list):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://llm-gateway:8001/v1/chat/completions",
            json={
                "messages": messages,
                "stream": false
            }
        )
        return response.json()["choices"][0]["message"]["content"]

# Streaming
async def stream_llm_response(messages: list):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://llm-gateway:8001/v1/chat/completions",
            json={"messages": messages, "stream": true}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_data = json.loads(line[6:])
                    if chunk_data != "[DONE]":
                        delta = chunk_data["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
```

---

## Development

```bash
# Run locally
cd services/llm-gateway
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Test endpoint
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hi"}],
    "stream": false
  }'
```

---

## Monitoring

- **Circuit breaker state**: Check `/metrics` endpoint
- **Cache hit rate**: Check logs for "Cache HIT/MISS"
- **Rate limiting**: Check logs for "Rate limit reached"
- **LLM latency**: Check logs for "LLM completion success"

---

**Version:** 1.0.0
**Author:** Vitte Team
**License:** Proprietary
