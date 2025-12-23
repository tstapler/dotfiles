"""Claude Proxy - Simple OAuth + Bedrock fallback proxy for Claude Code."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any
import json

from auth import get_auth_from_request
from providers.anthropic import AnthropicProvider
from providers.bedrock import BedrockProvider
from fallback import FallbackHandler
import config

# Initialize FastAPI app
app = FastAPI(title="Claude Proxy", version="1.0.0")

# Initialize providers
anthropic = AnthropicProvider()
bedrock = BedrockProvider()

# Create fallback handler with provider priority
fallback = FallbackHandler([anthropic, bedrock])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/v1/messages")
async def messages_endpoint(request: Request):
    """
    Main messages endpoint compatible with Claude Code.
    Handles both streaming and non-streaming requests.
    """
    try:
        # Get authentication
        token, auth_type = get_auth_from_request(request)

        # Parse request body
        body = await request.json()

        # Get headers to forward
        headers = {}
        if "anthropic-version" in request.headers:
            headers["anthropic-version"] = request.headers["anthropic-version"]

        # Check if streaming is requested
        if body.get("stream", False):
            # Stream response
            async def generate():
                try:
                    async for chunk in fallback.stream_message(body, token, auth_type, headers):
                        yield chunk
                except Exception as e:
                    error_event = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Non-streaming response
            result = await fallback.send_message(body, token, auth_type, headers)
            return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in messages endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/completions")
async def openai_compatibility_endpoint(request: Request):
    """
    OpenAI-compatible endpoint for testing.
    Converts OpenAI format to Anthropic format.
    """
    try:
        # Get authentication
        token, auth_type = get_auth_from_request(request)

        # Parse request body
        openai_body = await request.json()

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

        # Handle streaming
        if anthropic_body.get("stream", False):
            async def generate():
                try:
                    async for chunk in fallback.stream_message(anthropic_body, token, auth_type, headers):
                        yield chunk
                except Exception as e:
                    error_event = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming response
            result = await fallback.send_message(anthropic_body, token, auth_type, headers)

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
            return JSONResponse(content=openai_response)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in OpenAI compatibility endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "Claude Proxy",
        "version": "1.0.0",
        "endpoints": [
            "/v1/messages - Claude Code compatible endpoint",
            "/chat/completions - OpenAI compatible endpoint",
            "/health - Health check"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=config.PROXY_PORT)