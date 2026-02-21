"""Claude Proxy - Simple OAuth + Bedrock fallback proxy for Claude Code."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any
import json
import logging
from logging.handlers import RotatingFileHandler
import time

from auth import get_auth_from_request
from providers.anthropic import AnthropicProvider
from providers.bedrock import BedrockProvider
from providers import ValidationError, AuthenticationError, RateLimitError
from fallback import FallbackHandler
import config

# Configure logging with rotation and separate files
# Keep 10 files of 10MB each (100MB total) per log type

# Application logs (main, fallback, providers) - meaningful logs
app_handler = RotatingFileHandler(
    '/tmp/claude-proxy.app.log',
    maxBytes=10*1024*1024,  # 10MB per file
    backupCount=10
)
app_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# HTTP request logs (httpx, httpcore) - noisy logs
http_handler = RotatingFileHandler(
    '/tmp/claude-proxy.http.log',
    maxBytes=10*1024*1024,  # 10MB per file
    backupCount=5  # Less history for noisy logs
)
http_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Configure root logger for application logs
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(app_handler)

# Configure httpx/httpcore to use separate log file
for http_logger_name in ['httpx', 'httpcore']:
    http_logger = logging.getLogger(http_logger_name)
    http_logger.handlers.clear()  # Remove inherited handlers
    http_logger.addHandler(http_handler)
    http_logger.propagate = False  # Don't propagate to root logger

logger = logging.getLogger(__name__)

# Request duration thresholds for monitoring
SLOW_REQUEST_THRESHOLD = 30  # seconds
BLOCKING_REQUEST_THRESHOLD = 60  # seconds

# Initialize FastAPI app
app = FastAPI(title="Claude Proxy", version="1.0.0")

# Initialize providers
anthropic = AnthropicProvider()
bedrock = BedrockProvider()

# Create fallback handler with provider priority
fallback = FallbackHandler([anthropic, bedrock])


@app.middleware("http")
async def monitor_request_duration(request: Request, call_next):
    """Monitor request duration to detect blocking operations."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Log slow requests
    if duration > BLOCKING_REQUEST_THRESHOLD:
        logger.error(f"⚠️  BLOCKING REQUEST: {request.url.path} took {duration:.1f}s (threshold: {BLOCKING_REQUEST_THRESHOLD}s)")
    elif duration > SLOW_REQUEST_THRESHOLD:
        logger.warning(f"🐌 Slow request: {request.url.path} took {duration:.1f}s")

    # Add duration header for monitoring
    response.headers["X-Request-Duration"] = f"{duration:.2f}"
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/v1/models")
async def list_models():
    """
    OpenAI-compatible models endpoint for LiteLLM.
    Returns list of available Claude models.
    """
    models = [
        {"id": "claude-opus-4-6", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-sonnet-4-6", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-opus-4-5-20251101", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-sonnet-4-5-20250929", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-opus-4-20250514", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-sonnet-4-20250514", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-7-sonnet-20250219", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-5-sonnet-20241022", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-5-haiku-20241022", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-haiku-4-5-20251001", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-opus-20240229", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-haiku-20240307", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
    ]
    return {"object": "list", "data": models}


@app.post("/v1/messages")
async def messages_endpoint(request: Request):
    """
    Main messages endpoint compatible with Claude Code.
    Handles both streaming and non-streaming requests.
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] → /v1/messages stream={request.query_params.get('beta', 'false')}")

    try:
        # Get authentication
        token, auth_type = get_auth_from_request(request)

        # Parse request body
        body = await request.json()

        logger.info(f"[{request_id}] Request: model={body.get('model')}, max_tokens={body.get('max_tokens')}, stream={body.get('stream', False)}")

        # Get headers to forward
        headers = {}
        if "anthropic-version" in request.headers:
            headers["anthropic-version"] = request.headers["anthropic-version"]
        if "anthropic-beta" in request.headers:
            headers["anthropic-beta"] = request.headers["anthropic-beta"]

        # Check if streaming is requested
        if body.get("stream", False):
            # Stream response - handle errors gracefully
            chunk_count = 0
            async def generate():
                nonlocal chunk_count
                try:
                    async for chunk in fallback.stream_message(body, token, auth_type, headers, request_id):
                        chunk_count += 1
                        # Log first 3 chunks to debug
                        if chunk_count <= 3:
                            logger.debug(f"[{request_id}] Yielding chunk {chunk_count}: {chunk[:150]}...")
                        yield chunk
                except RateLimitError as e:
                    # Return rate limit error event with retry info
                    logger.error(f"🚫 [{request_id}] RATE LIMIT in streaming - returning overloaded_error event: {e}")
                    error_event = {
                        "type": "error",
                        "error": {
                            "type": "overloaded_error",  # Use overloaded_error for better retry handling
                            "message": "Both Anthropic and AWS Bedrock have rate limited your requests after 20+ retry attempts. Please wait 30-60 seconds before trying again. This usually happens during high-traffic periods."
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                except Exception as e:
                    # Return generic error event for other errors
                    error_event = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"

            logger.info(f"[{request_id}] ✓ Starting streaming response")
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "X-Request-ID": request_id
                }
            )
        else:
            # Non-streaming response
            result = await fallback.send_message(body, token, auth_type, headers, request_id)
            logger.info(f"[{request_id}] ✓ Non-streaming response complete")
            return JSONResponse(content=result, headers={"X-Request-ID": request_id})

    except HTTPException:
        raise
    except ValidationError as e:
        # Log concise request info for debugging validation errors
        logger.error(f"[{request_id}] Validation error: {e}")
        logger.error(f"[{request_id}] Request: model={body.get('model')}, max_tokens={body.get('max_tokens')}, tools={len(body.get('tools', []))}, messages={len(body.get('messages', []))}")
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"[{request_id}] Authentication error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except RateLimitError as e:
        logger.error(f"🚫 [{request_id}] RATE LIMIT in non-streaming - returning 429 status: {e}")
        # Return 429 with Retry-After header for proper client handling
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "type": "rate_limit_error",
                    "message": "Both Anthropic and AWS Bedrock have rate limited your requests after 20+ retry attempts. Please wait 30-60 seconds before trying again. This usually happens during high-traffic periods."
                }
            },
            headers={"Retry-After": "60"}  # Suggest 60 second retry
        )
    except Exception as e:
        logger.error(f"Error in messages endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/messages/count_tokens")
async def count_tokens_endpoint(request: Request):
    """
    Token counting endpoint - passthrough to Anthropic API.
    Used by Claude Code to count tokens before making actual requests.
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]

    try:
        # Get authentication
        token, auth_type = get_auth_from_request(request)

        # Parse request body
        body = await request.json()
        model = body.get("model", "unknown")

        logger.debug(f"[{request_id}] → /v1/messages/count_tokens (model={model})")

        # Get headers to forward
        headers = {}
        if "anthropic-version" in request.headers:
            headers["anthropic-version"] = request.headers["anthropic-version"]
        if "anthropic-beta" in request.headers:
            headers["anthropic-beta"] = request.headers["anthropic-beta"]

        # Forward to Anthropic API (only anthropic provider supports token counting)
        from providers.anthropic import AnthropicProvider
        provider = AnthropicProvider()

        # Normalize model name
        if "model" in body:
            body["model"] = provider.normalize_model_name(body["model"])

        # Build headers for Anthropic
        api_headers = {}
        if auth_type == "bearer":
            api_headers["Authorization"] = f"Bearer {token}"
        else:
            api_headers["x-api-key"] = token

        if "anthropic-version" in headers:
            api_headers["anthropic-version"] = headers["anthropic-version"]
        if "anthropic-beta" in headers:
            api_headers["anthropic-beta"] = headers["anthropic-beta"]

        # Make request to count_tokens endpoint
        response = await provider.client.post(
            f"{provider.base_url}/v1/messages/count_tokens",
            json=body,
            headers=api_headers
        )

        if response.status_code != 200:
            # Known Claude Code bug: count_tokens is called without proper auth headers
            # This is harmless - regular message requests work fine
            if response.status_code == 401:
                logger.debug(f"[{request_id}] count_tokens auth error (known Claude Code bug): {response.status_code}")
            else:
                logger.error(f"[{request_id}] ✗ count_tokens failed: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        result = response.json()
        logger.debug(f"[{request_id}] ✓ count_tokens: {result.get('input_tokens', 0)} tokens")
        return JSONResponse(content=result, headers={"X-Request-ID": request_id})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error in count_tokens endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
async def openai_compatibility_endpoint(request: Request):
    """
    OpenAI-compatible endpoint for testing and LiteLLM compatibility.
    Converts OpenAI format to Anthropic format.
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] → /v1/chat/completions (OpenAI)")

    try:
        # Get authentication
        token, auth_type = get_auth_from_request(request)

        # Parse request body
        openai_body = await request.json()

        logger.info(f"[{request_id}] OpenAI Request: model={openai_body.get('model')}, max_tokens={openai_body.get('max_tokens')}, stream={openai_body.get('stream', False)}")

        # Convert OpenAI format to Anthropic format
        anthropic_body = {
            "model": openai_body.get("model", "claude-3-haiku-20240307"),
            "messages": openai_body.get("messages", []),
            "max_tokens": openai_body.get("max_tokens", 1024),
            "temperature": openai_body.get("temperature", 1.0),
            "stream": openai_body.get("stream", False)
        }

        # Get headers
        headers = {}
        if "anthropic-version" in request.headers:
            headers["anthropic-version"] = request.headers["anthropic-version"]
        if "anthropic-beta" in request.headers:
            headers["anthropic-beta"] = request.headers["anthropic-beta"]

        # Handle streaming
        if anthropic_body.get("stream", False):
            async def generate():
                try:
                    async for chunk in fallback.stream_message(anthropic_body, token, auth_type, headers, request_id):
                        yield chunk
                except RateLimitError as e:
                    # Return rate limit error event with retry info
                    logger.error(f"🚫 [{request_id}] RATE LIMIT in OpenAI streaming - returning overloaded_error event: {e}")
                    error_event = {
                        "type": "error",
                        "error": {
                            "type": "overloaded_error",  # Use overloaded_error for better retry handling
                            "message": "Both Anthropic and AWS Bedrock have rate limited your requests after 20+ retry attempts. Please wait 30-60 seconds before trying again. This usually happens during high-traffic periods."
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                except Exception as e:
                    # Return generic error event for other errors
                    error_event = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"

            logger.info(f"[{request_id}] ✓ Starting OpenAI streaming response")
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"X-Request-ID": request_id}
            )
        else:
            # Non-streaming response
            result = await fallback.send_message(anthropic_body, token, auth_type, headers, request_id)

            # Convert to OpenAI format
            openai_response = {
                "id": result.get("id", "msg-proxy"),
                "object": "chat.completion",
                "created": 1234567890,
                "model": result.get("model"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.get("content", [{"text": ""}])[0].get("text", "")
                    },
                    "finish_reason": "stop"
                }],
                "usage": result.get("usage", {})
            }
            logger.info(f"[{request_id}] ✓ OpenAI non-streaming response complete")
            return JSONResponse(content=openai_response, headers={"X-Request-ID": request_id})

    except HTTPException:
        raise
    except ValidationError as e:
        # Log request body for debugging validation errors
        sanitized_body = {k: v for k, v in anthropic_body.items() if k not in ['messages']}  # Exclude messages to avoid logging sensitive data
        sanitized_body['message_count'] = len(anthropic_body.get('messages', []))
        logger.error(f"[{request_id}] Validation error: {e}")
        logger.error(f"[{request_id}] Request params: {json.dumps(sanitized_body)}")
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"[{request_id}] Authentication error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except RateLimitError as e:
        logger.error(f"🚫 [{request_id}] RATE LIMIT in OpenAI non-streaming - returning 429 status: {e}")
        # Return 429 with Retry-After header for proper client handling
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "type": "rate_limit_error",
                    "message": "Both Anthropic and AWS Bedrock have rate limited your requests after 20+ retry attempts. Please wait 30-60 seconds before trying again. This usually happens during high-traffic periods."
                }
            },
            headers={"Retry-After": "60"}  # Suggest 60 second retry
        )
    except Exception as e:
        logger.error(f"Error in OpenAI compatibility endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/event_logging/batch")
async def litellm_event_logging(request: Request):
    """
    LiteLLM telemetry endpoint stub.
    LiteLLM sends usage events here - we accept them silently.
    """
    # Accept the events but don't process them
    return {"status": "success"}


@app.post("//v1/messages")
async def double_slash_error(request: Request):
    """Error handler for double slash in URL."""
    raise HTTPException(
        status_code=400,
        detail="Invalid URL: double slash detected. Your base URL should be 'http://localhost:47000' (without trailing /v1). Current request path: '//v1/messages'"
    )


@app.post("/v1/v1/messages")
async def double_v1_error(request: Request):
    """Error handler for double /v1 prefix."""
    raise HTTPException(
        status_code=400,
        detail="Invalid URL: double /v1 prefix detected. Your base URL should be 'http://localhost:47000' (without /v1) OR 'http://localhost:47000/v1' (with /v1), but not both. Current request path: '/v1/v1/messages'"
    )


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "Claude Proxy",
        "version": "1.0.0",
        "endpoints": [
            "/v1/messages - Claude Code compatible endpoint",
            "/v1/models - List available models (LiteLLM)",
            "/chat/completions - OpenAI compatible endpoint",
            "/v1/chat/completions - OpenAI compatible endpoint (LiteLLM)",
            "/health - Health check"
        ]
    }


if __name__ == "__main__":
    import uvicorn

    # Note: workers > 1 requires passing app as import string
    # Each worker gets its own process and event loop
    uvicorn.run(
        "main:app",  # Import string required for multi-worker mode
        host="127.0.0.1",
        port=config.PROXY_PORT,
        workers=config.WORKERS,
        log_level="info",
        # Enable asyncio debug mode in each worker
        loop="asyncio",
        access_log=True
    )