"""Configuration settings for Claude Proxy."""
import os
import multiprocessing
from typing import Optional

# OAuth token for Anthropic API
CLAUDE_CODE_OAUTH_TOKEN: Optional[str] = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")

# AWS settings for Bedrock
AWS_PROFILE: str = os.environ.get("AWS_PROFILE", "Sandbox.AdministratorAccess")
AWS_REGION: str = os.environ.get("AWS_REGION", "us-west-2")

# Proxy settings
PROXY_PORT: int = int(os.environ.get("PROXY_PORT", "47000"))
COOLDOWN_SECONDS: int = int(os.environ.get("COOLDOWN_SECONDS", "300"))  # 5 minutes
REQUEST_TIMEOUT: int = int(os.environ.get("REQUEST_TIMEOUT", "300"))  # 5 minutes
BEDROCK_MAX_RETRIES: int = int(os.environ.get("BEDROCK_MAX_RETRIES", "20"))  # Retry rate limits/timeouts
BEDROCK_THREAD_POOL_SIZE: int = int(os.environ.get("BEDROCK_THREAD_POOL_SIZE", "40"))  # Threads for boto3 calls per worker
WORKERS: int = int(os.environ.get("WORKERS", str(multiprocessing.cpu_count())))  # Default: one worker per CPU core

# Compression (stapler-compactor)
# Set STAPLER_COMPRESS=0 to disable all compression (killswitch per ADR-004)
COMPRESS_ENABLED: bool = os.environ.get("STAPLER_COMPRESS", "1") != "0"
COMPRESS_FLOOR_BYTES: int = int(os.environ.get("COMPRESS_FLOOR_BYTES", "4096"))