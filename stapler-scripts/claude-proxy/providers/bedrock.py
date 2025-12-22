"""AWS Bedrock provider implementation."""
import json
import boto3
from typing import Dict, Any, AsyncIterator, Optional
from . import Provider, RateLimitError
import config


class BedrockProvider(Provider):
    """Provider for AWS Bedrock."""

    def __init__(self):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=config.AWS_REGION
        )

    @property
    def name(self) -> str:
        return "bedrock"

    def _convert_to_bedrock_model(self, model: str) -> str:
        """Convert model name to Bedrock format."""
        # Remove any existing prefixes
        model = self.normalize_model_name(model)

        # Remove -bedrock suffix if present
        if model.endswith("-bedrock"):
            model = model[:-8]

        # Map to Bedrock model ID
        model_mapping = {
            "claude-opus-4-5-20251101": "us.anthropic.claude-opus-4-5-20251101-v1:0",
            "claude-sonnet-4-5-20250929": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "claude-opus-4-20250514": "us.anthropic.claude-opus-4-20250514-v1:0",
            "claude-sonnet-4-20250514": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "claude-3-7-sonnet-20250219": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "claude-3-5-sonnet-20241022": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "claude-3-5-haiku-20241022": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
            "claude-haiku-4-5-20251001": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            "claude-3-opus-20240229": "us.anthropic.claude-3-opus-20240229-v1:0",
            "claude-3-haiku-20240307": "us.anthropic.claude-3-haiku-20240307-v1:0",
        }

        return model_mapping.get(model, f"us.anthropic.{model}-v1:0")

    def _convert_response(self, bedrock_response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Convert Bedrock response to Anthropic format."""
        # Extract content from Bedrock response
        content = bedrock_response.get("content", [])
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        return {
            "id": bedrock_response.get("id", "msg_bedrock"),
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": bedrock_response.get("stop_reason", "end_turn"),
            "stop_sequence": bedrock_response.get("stop_sequence"),
            "usage": bedrock_response.get("usage", {
                "input_tokens": 0,
                "output_tokens": 0
            })
        }

    async def send_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send message to Bedrock."""
        # Convert model name
        original_model = body.get("model", "claude-3-haiku-20240307")
        bedrock_model = self._convert_to_bedrock_model(original_model)

        # Prepare Bedrock request
        bedrock_body = body.copy()
        bedrock_body["model"] = bedrock_model

        # Remove unsupported parameters
        bedrock_body.pop("stream", None)

        try:
            # Synchronous call wrapped in async
            response = self.client.invoke_model(
                modelId=bedrock_model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(bedrock_body)
            )

            # Parse response
            result = json.loads(response["body"].read())
            return self._convert_response(result, original_model)

        except self.client.exceptions.ThrottlingException:
            raise RateLimitError("Bedrock rate limit exceeded")
        except Exception as e:
            raise Exception(f"Bedrock error: {str(e)}")

    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[str]:
        """Stream message from Bedrock."""
        # Convert model name
        original_model = body.get("model", "claude-3-haiku-20240307")
        bedrock_model = self._convert_to_bedrock_model(original_model)

        # Prepare Bedrock request
        bedrock_body = body.copy()
        bedrock_body["model"] = bedrock_model

        try:
            # Invoke with streaming
            response = self.client.invoke_model_with_response_stream(
                modelId=bedrock_model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(bedrock_body)
            )

            # Stream events
            for event in response["body"]:
                chunk = json.loads(event["chunk"]["bytes"])

                # Convert to SSE format matching Anthropic
                if chunk.get("type") == "content_block_delta":
                    sse_data = {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": chunk.get("delta", {})
                    }
                    yield f"data: {json.dumps(sse_data)}\n"
                elif chunk.get("type") == "message_stop":
                    yield "data: [DONE]\n"

        except self.client.exceptions.ThrottlingException:
            raise RateLimitError("Bedrock rate limit exceeded")
        except Exception as e:
            raise Exception(f"Bedrock streaming error: {str(e)}")