"""
llm_client.py — Anthropic SDK wrapper for ProcureOps.

Adapted from sop-deviation-review/backend/llm_client.py. The one structural
difference: ProcureOps runs 5 agents across two model tiers (Haiku for
Requisition Intake and Inventory Management; Sonnet for Sourcing/Quote
Comparison and Invoice Verification, per the brief's complexity split), so
call_model() takes an explicit model_id instead of being hardcoded to one
model. call_haiku()/call_sonnet() are thin convenience wrappers.

Never raises to callers — errors are always surfaced through LLMResponse.error,
and .parsed() always falls back to a safe, escalate-by-default response.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

HAIKU_MODEL = "claude-haiku-4-5"
SONNET_MODEL = "claude-sonnet-4-6"

# Safe fallback — conservative by default: always escalate when the system
# itself cannot produce a reliable answer. Never auto-approve on failure.
SAFE_FALLBACK: dict[str, Any] = {
    "summary": (
        "Automated processing could not be completed due to a system error. "
        "This item requires manual review before any decision is made."
    ),
    "escalate": True,
    "reason_code": "INSUFFICIENT_INFORMATION",
    "confidence": "Low",
    "rationale": (
        "The agent encountered an error and could not produce a reliable "
        "assessment. All failed or uncertain runs escalate by default."
    ),
}


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    error: str | None
    stop_reason: str | None
    cached_tokens: int = 0

    @property
    def success(self) -> bool:
        return self.error is None

    def parsed(self) -> dict[str, Any]:
        try:
            return json.loads(self.text)
        except (json.JSONDecodeError, TypeError):
            return dict(SAFE_FALLBACK)


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. Add it to .env or the shell environment."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _extract_content(response: anthropic.types.Message) -> tuple[str, str | None]:
    for block in response.content:
        if block.type == "tool_use":
            return json.dumps(block.input, ensure_ascii=False), "tool_use"
        if block.type == "text":
            return block.text, response.stop_reason
    return "", response.stop_reason


def call_model(
    model_id: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    tools: list[dict] | None = None,
    tool_choice: dict | None = None,
) -> LLMResponse:
    """Call any Anthropic model via the Messages API. Never raises."""
    t0 = time.monotonic()
    try:
        client = _get_client()
        kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": user_message}],
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        response = client.messages.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)
        text, stop_reason = _extract_content(response)
        cached = getattr(response.usage, "cache_read_input_tokens", 0) or 0

        return LLMResponse(
            text=text, input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens, latency_ms=latency_ms,
            error=None, stop_reason=stop_reason, cached_tokens=int(cached),
        )

    except EnvironmentError as exc:
        return LLMResponse(json.dumps(SAFE_FALLBACK), 0, 0, int((time.monotonic() - t0) * 1000),
                            f"Configuration error: {exc}", None)
    except anthropic.AuthenticationError as exc:
        return LLMResponse(json.dumps(SAFE_FALLBACK), 0, 0, int((time.monotonic() - t0) * 1000),
                            f"Authentication error - check ANTHROPIC_API_KEY: {exc}", None)
    except anthropic.RateLimitError as exc:
        return LLMResponse(json.dumps(SAFE_FALLBACK), 0, 0, int((time.monotonic() - t0) * 1000),
                            f"Rate limit exceeded: {exc}", None)
    except anthropic.APIConnectionError as exc:
        return LLMResponse(json.dumps(SAFE_FALLBACK), 0, 0, int((time.monotonic() - t0) * 1000),
                            f"Network error: {exc}", None)
    except anthropic.APIStatusError as exc:
        return LLMResponse(json.dumps(SAFE_FALLBACK), 0, 0, int((time.monotonic() - t0) * 1000),
                            f"Anthropic API error {exc.status_code}: {exc.message}", None)
    except Exception as exc:  # noqa: BLE001
        return LLMResponse(json.dumps(SAFE_FALLBACK), 0, 0, int((time.monotonic() - t0) * 1000),
                            f"Unexpected error: {type(exc).__name__}: {exc}", None)


def call_haiku(system_prompt: str, user_message: str, max_tokens: int = 1024,
               tools: list[dict] | None = None, tool_choice: dict | None = None) -> LLMResponse:
    return call_model(HAIKU_MODEL, system_prompt, user_message, max_tokens, tools, tool_choice)


def call_sonnet(system_prompt: str, user_message: str, max_tokens: int = 1536,
                 tools: list[dict] | None = None, tool_choice: dict | None = None) -> LLMResponse:
    return call_model(SONNET_MODEL, system_prompt, user_message, max_tokens, tools, tool_choice)
