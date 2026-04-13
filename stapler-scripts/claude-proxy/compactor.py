"""FusionEngine compression middleware for claude-proxy.

Compresses the messages[] array before it is forwarded to Anthropic/Bedrock.
Designed for transparent, per-request compression with zero behavioral change
to Claude Code sessions.

Architecture decisions:
  ADR-001: Inserted at /v1/messages handler level, before FallbackHandler.dispatch()
  ADR-002: OpenFeature InMemoryProvider — no external services
  ADR-003: Rewind marker from claw_compactor.rewind.marker serves as double-compression guard
  ADR-004: STAPLER_COMPRESS=0 env var as unconditional bypass (in config.py)

FusionEngine API (actual, from v7.1.0):
  FusionEngine(enable_rewind=True, aggressive=True)
  engine.compress_messages(messages) -> {
      "messages": list[dict],
      "stats": {original_tokens, compressed_tokens, reduction_pct, total_timing_ms, message_count, ...},
      "per_message": list[dict],
      "markers": list[str],
      "warnings": list[str],
  }
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from openfeature import api
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

from config import COMPRESS_ENABLED, COMPRESS_FLOOR_BYTES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons (one per worker process — see Bug 004 in plan)
# ---------------------------------------------------------------------------

_engine = None        # FusionEngine instance; None when disabled or not yet init
_ff = None            # OpenFeature client singleton


def init_compactor() -> None:
    """Called once at proxy startup in each worker process.

    Initializes FusionEngine and OpenFeature InMemoryProvider.
    Skipped entirely when STAPLER_COMPRESS=0 (ADR-004 killswitch).
    """
    global _engine, _ff

    if not COMPRESS_ENABLED:
        logger.info("Compression disabled via STAPLER_COMPRESS=0")
        return

    try:
        from claw_compactor.fusion.engine import FusionEngine
        _engine = FusionEngine(enable_rewind=True, aggressive=True)
        logger.info(f"FusionEngine initialized (stages: {_engine.stage_names})")
    except Exception as e:
        logger.error(f"FusionEngine init failed — compression disabled: {e}")
        return

    flags = {
        "compression-enabled": InMemoryFlag(
            default_variant="on",
            variants={"on": True, "off": False},
        ),
        "compression-floor-bytes": InMemoryFlag(
            default_variant="default",
            variants={"default": COMPRESS_FLOOR_BYTES},
        ),
        "rewind-tool-injection": InMemoryFlag(
            default_variant="on",
            variants={"on": True, "off": False},
        ),
    }

    try:
        api.set_provider(InMemoryProvider(flags))
        _ff = api.get_client()
        logger.info("OpenFeature InMemoryProvider initialized")
    except Exception as e:
        logger.error(f"OpenFeature init failed — using defaults: {e}")


def get_flags() -> dict[str, Any]:
    """Return current flag values. Called once per request."""
    if _ff is None:
        return {
            "enabled": False,
            "floor": COMPRESS_FLOOR_BYTES,
            "rewind": False,
        }
    return {
        "enabled": _ff.get_boolean_value("compression-enabled", False),
        "floor": _ff.get_integer_value("compression-floor-bytes", COMPRESS_FLOOR_BYTES),
        "rewind": _ff.get_boolean_value("rewind-tool-injection", False),
    }


# ---------------------------------------------------------------------------
# Double-compression guard (ADR-003)
# ---------------------------------------------------------------------------

def _has_rewind_markers(messages: list[dict]) -> bool:
    """Return True if any message content contains Rewind retrieval markers.

    Rewind markers are embedded by FusionEngine when lossy compression occurs.
    Their presence means at least one prior round of compression has run —
    re-compressing would corrupt the markers and waste tokens.

    Pattern: [N items compressed to M. Retrieve: hash=XXXX]
    """
    try:
        from claw_compactor.rewind.marker import has_markers
    except ImportError:
        return False

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            if has_markers(content):
                return True
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "") or block.get("content", "")
                    if isinstance(text, str) and has_markers(text):
                        return True
    return False


# ---------------------------------------------------------------------------
# Rewind tool injection
# ---------------------------------------------------------------------------

def _ensure_rewind_tool(tools: list[dict] | None, messages: list[dict]) -> list[dict]:
    """Inject the rewind_retrieve tool definition if compressed content is present.

    Only injects if:
    - rewind-tool-injection flag is enabled
    - compressed content (Rewind markers) is present in messages
    - rewind_retrieve not already in tools (idempotent)
    """
    tools = tools or []

    if not _has_rewind_markers(messages):
        return tools

    if any(t.get("name") == "rewind_retrieve" for t in tools):
        return tools

    try:
        from claw_compactor.rewind import rewind_tool_def
        rewind_def = rewind_tool_def(provider="anthropic")
        return tools + [rewind_def]
    except ImportError:
        return tools


# ---------------------------------------------------------------------------
# Core compression entry point
# ---------------------------------------------------------------------------

def _run_compression_sync(
    messages: list[dict],
    flags: dict,
) -> tuple[list[dict], dict]:
    """Synchronous compression — called via asyncio.to_thread.

    Returns (compressed_messages, stats).
    """
    if _engine is None:
        return messages, {}

    # Skip if total message size is below floor
    total_bytes = sum(
        len(json.dumps(m.get("content", "")).encode())
        for m in messages
    )
    if total_bytes < flags.get("floor", COMPRESS_FLOOR_BYTES):
        return messages, {"skipped": "below_floor", "total_bytes": total_bytes}

    result = _engine.compress_messages(messages)
    return result["messages"], result["stats"]


async def compress_messages(
    messages: list[dict],
    tools: list[dict],
    flags: dict,
) -> tuple[list[dict], list[dict], dict]:
    """Compress messages array.

    Returns (compressed_messages, updated_tools, stats).

    stats keys: original_tokens, compressed_tokens, reduction_pct, total_timing_ms,
                message_count, skipped (if not compressed)
    """
    if not flags.get("enabled"):
        return messages, tools, {}

    # Double-compression guard (ADR-003)
    if _has_rewind_markers(messages):
        logger.debug("Skipping compression: Rewind markers already present")
        return messages, tools, {"skipped": "already_compressed"}

    # Run FusionEngine in thread pool (sync CPU-bound operation)
    compressed_messages, stats = await asyncio.to_thread(
        _run_compression_sync, messages, flags
    )

    if stats.get("skipped"):
        return messages, tools, stats

    reduction_pct = stats.get("reduction_pct", 0)
    tokens_saved = stats.get("original_tokens", 0) - stats.get("compressed_tokens", 0)
    logger.info(
        f"Compression: {reduction_pct:.1f}% reduction, "
        f"{tokens_saved} tokens saved "
        f"({stats.get('original_tokens', 0)} → {stats.get('compressed_tokens', 0)})"
    )

    # Inject Rewind tool if markers are present in output
    updated_tools = tools
    if flags.get("rewind"):
        updated_tools = _ensure_rewind_tool(tools, compressed_messages)

    return compressed_messages, updated_tools, stats
