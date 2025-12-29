"""AWS Bedrock provider implementation."""
import json
import boto3
import asyncio
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from botocore.config import Config
from botocore.exceptions import ReadTimeoutError, ConnectTimeoutError
from typing import Dict, Any, AsyncIterator, Optional
from . import Provider, RateLimitError, ValidationError, TimeoutError
import config

logger = logging.getLogger(__name__)


class BedrockProvider(Provider):
    """Provider for AWS Bedrock."""

    def __init__(self):
        # Configure boto3 with 5-minute timeout
        boto_config = Config(
            read_timeout=config.REQUEST_TIMEOUT,
            connect_timeout=30,
            retries={'max_attempts': 0}  # Handle retries in fallback handler
        )
        # Use Session to enable credential refresh checking
        self.session = boto3.Session()
        self.client = self.session.client(
            "bedrock-runtime",
            region_name=config.AWS_REGION,
            config=boto_config
        )
        # Thread pool for running blocking boto3 calls without blocking event loop
        # Use max_workers=20 to handle concurrent requests across workers
        self.executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="bedrock-io")

    @property
    def name(self) -> str:
        return "bedrock"

    def _check_and_refresh_credentials(self):
        """Check if credentials are expiring soon and refresh proactively."""
        try:
            # Get current credentials from session
            credentials = self.session.get_credentials()
            if not credentials:
                logger.warning("No credentials found, recreating client")
                self._recreate_client()
                return

            # Check if credentials have an expiry time
            # Works with SSO, assume role, credential_process (aws-vault), etc.
            if hasattr(credentials, '_expiry_time') and credentials._expiry_time:
                expiry_time = credentials._expiry_time

                # Calculate time until expiry
                now = datetime.now(expiry_time.tzinfo) if expiry_time.tzinfo else datetime.now()
                time_until_expiry = expiry_time - now

                # Refresh if expiring within 5 minutes
                if time_until_expiry < timedelta(minutes=5):
                    logger.warning(f"🔄 Credentials expiring in {int(time_until_expiry.total_seconds() / 60)}m, refreshing proactively")
                    # Recreate client to force credential_process or SSO refresh
                    self._recreate_client()
                    logger.info("✓ Credentials refreshed successfully")
                elif time_until_expiry < timedelta(minutes=15):
                    logger.debug(f"Credentials valid for {int(time_until_expiry.total_seconds() / 60)} minutes")
        except Exception as e:
            # Don't fail requests due to credential check issues
            logger.debug(f"Credential check error (non-fatal): {e}")

    def _recreate_client(self):
        """Recreate boto3 client to force credential refresh."""
        boto_config = Config(
            read_timeout=config.REQUEST_TIMEOUT,
            connect_timeout=30,
            retries={'max_attempts': 0}
        )
        # Create new session to force credential refresh
        self.session = boto3.Session()
        self.client = self.session.client(
            "bedrock-runtime",
            region_name=config.AWS_REGION,
            config=boto_config
        )

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
        # Proactively refresh credentials if expiring soon
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._check_and_refresh_credentials)

        # Convert model name
        original_model = body.get("model", "claude-3-haiku-20240307")
        bedrock_model = self._convert_to_bedrock_model(original_model)

        # Prepare Bedrock request
        bedrock_body = body.copy()
        bedrock_body["anthropic_version"] = "bedrock-2023-05-31"

        # Remove unsupported parameters and model (model is specified via modelId parameter)
        bedrock_body.pop("stream", None)
        bedrock_body.pop("model", None)

        try:
            # Run blocking boto3 call in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.invoke_model(
                    modelId=bedrock_model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(bedrock_body)
                )
            )

            # Parse response
            result = json.loads(response["body"].read())
            return self._convert_response(result, original_model)

        except self.client.exceptions.ThrottlingException:
            raise RateLimitError("Bedrock rate limit exceeded")
        except self.client.exceptions.ValidationException as e:
            raise ValidationError(f"Bedrock validation error: {str(e)}")
        except (ReadTimeoutError, ConnectTimeoutError) as e:
            raise TimeoutError(f"Bedrock timeout: {str(e)}")
        except Exception as e:
            # Check if it's a timeout in the exception message
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise TimeoutError(f"Bedrock timeout: {str(e)}")
            raise Exception(f"Bedrock error: {str(e)}")

    async def stream_message(
        self,
        body: Dict[str, Any],
        token: str,
        auth_type: str,
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[str]:
        """Stream message from Bedrock."""
        # Proactively refresh credentials if expiring soon
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._check_and_refresh_credentials)

        # Convert model name
        original_model = body.get("model", "claude-3-haiku-20240307")
        bedrock_model = self._convert_to_bedrock_model(original_model)

        # Prepare Bedrock request
        bedrock_body = body.copy()
        bedrock_body["anthropic_version"] = "bedrock-2023-05-31"

        # Remove unsupported parameters and model (model is specified via modelId parameter)
        bedrock_body.pop("stream", None)
        bedrock_body.pop("model", None)

        try:
            # Run blocking boto3 streaming call in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.client.invoke_model_with_response_stream(
                    modelId=bedrock_model,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(bedrock_body)
                )
            )

            # Stream events (iteration is fast, no need to run in executor)
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
        except self.client.exceptions.ValidationException as e:
            raise ValidationError(f"Bedrock validation error: {str(e)}")
        except (ReadTimeoutError, ConnectTimeoutError) as e:
            raise TimeoutError(f"Bedrock timeout: {str(e)}")
        except Exception as e:
            # Check if it's a timeout in the exception message
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise TimeoutError(f"Bedrock timeout: {str(e)}")
            raise Exception(f"Bedrock streaming error: {str(e)}")