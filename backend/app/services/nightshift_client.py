"""
Nightshift + NVIDIA Nemotron AI Client
======================================
Dedicated client for model requests routed through Meterless Nightshift's
OpenAI-compatible REST API. All model calls go through Nightshift; direct
calls to upstream cloud providers are strictly prohibited.

The actual model used is inspected from the real API response and logged.
Credentials are never logged or returned in responses.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app.config import Settings, settings

logger = logging.getLogger(__name__)


class NightshiftNotConfiguredError(Exception):
    """Raised when Nightshift base URL or token is missing."""


class NightshiftAuthError(Exception):
    """Raised when Nightshift returns 401/403."""


class NightshiftQueryError(Exception):
    """Raised when Nightshift returns an error status code or malformed body."""


class NightshiftTimeoutError(Exception):
    """Raised when Nightshift request times out."""


@dataclass
class NightshiftResponse:
    """Structured response from Nightshift API with full routing metadata."""
    content: str
    model: str
    provider: str
    winning_route: Optional[Dict[str, Any]] = None
    receipt_id: Optional[str] = None
    latency_ms: Optional[float] = None
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


class NightshiftClient:
    """
    Client for Nightshift's OpenAI-compatible endpoint.
    Handles authentication, bounded retries with backoff, safe logging,
    and extraction of real model and routing metadata.
    """

    def __init__(self, cfg: Optional[Settings] = None, client: Optional[httpx.Client] = None) -> None:
        self._cfg = cfg or settings
        self._client = client

    def _get_headers(self) -> Dict[str, str]:
        token = self._cfg.resolved_nightshift_token
        if not token:
            raise NightshiftNotConfiguredError(
                "Nightshift auth token not found. Set NIGHTSHIFT_API_KEY in .env or ensure Nightshift proxy-token exists."
            )

        auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
        return {
            "Authorization": auth_header,
            "meterless-app": self._cfg.nightshift_app_name,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _guard(self) -> None:
        if not self._cfg.nightshift_configured:
            raise NightshiftNotConfiguredError(
                "Nightshift is not configured. Ensure NIGHTSHIFT_BASE_URL and auth token are set."
            )

    def _base_url(self) -> str:
        import os
        if (os.path.exists("/.dockerenv") or os.environ.get("IS_DOCKER")) and self._cfg.docker_nightshift_base_url:
            return self._cfg.docker_nightshift_base_url.rstrip("/")
        return self._cfg.nightshift_base_url.rstrip("/")

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        chat_template_kwargs: Optional[Dict[str, Any]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> NightshiftResponse:
        """
        Send a chat completion request to Nightshift with bounded retries.
        Extracts verified response content and actual model routing metadata.
        """
        self._guard()
        target_model = model or self._cfg.nightshift_model
        endpoint = f"{self._base_url()}/chat/completions"

        # By default disable thinking for Nemotron so content is returned directly
        # without empty_response error on local runtime
        kwargs = chat_template_kwargs if chat_template_kwargs is not None else {"enable_thinking": False}

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "chat_template_kwargs": kwargs,
        }
        if response_format:
            payload["response_format"] = response_format

        max_retries = max_retries if max_retries is not None else self._cfg.nightshift_max_retries
        timeout_s = float(timeout_seconds if timeout_seconds is not None else self._cfg.nightshift_timeout_seconds)
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            start_time = time.perf_counter()
            try:
                headers = {**self._get_headers(), **(extra_headers or {})}
                logger.debug(
                    "Calling Nightshift [%s] (attempt %d/%d, model: %s, messages: %d)",
                    endpoint, attempt, max_retries, target_model, len(messages)
                )

                if self._client:
                    resp = self._client.post(
                        endpoint,
                        headers=headers,
                        json=payload,
                        timeout=timeout_s,
                    )
                else:
                    with httpx.Client(timeout=timeout_s) as c:
                        resp = c.post(endpoint, headers=headers, json=payload)

                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                if resp.status_code == 401 or resp.status_code == 403:
                    raise NightshiftAuthError(f"Nightshift auth rejected (HTTP {resp.status_code}).")

                if resp.status_code in (429, 502, 503, 504):
                    # Transient error; retry
                    err_msg = f"Nightshift transient error (HTTP {resp.status_code}): {resp.text[:200]}"
                    logger.warning("%s — retrying (%d/%d)", err_msg, attempt, max_retries)
                    last_error = NightshiftQueryError(err_msg)
                    if attempt < max_retries:
                        time.sleep(0.5 * (2 ** (attempt - 1)))
                        continue
                    raise last_error

                if resp.status_code != 200:
                    raise NightshiftQueryError(
                        f"Nightshift returned error (HTTP {resp.status_code}): {resp.text[:300]}"
                    )

                body = resp.json()
                return self._parse_response(body, target_model, elapsed_ms)

            except (httpx.TimeoutException, TimeoutError) as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                last_error = NightshiftTimeoutError(
                    f"Nightshift call timed out after {timeout_s:g}s: {exc}"
                )
                logger.warning("Nightshift timeout on attempt %d/%d: %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                raise last_error from exc
            except (httpx.ConnectError, httpx.RequestError) as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                last_error = NightshiftQueryError(f"Nightshift connection error: {exc}")
                logger.warning("Nightshift connection failure on attempt %d/%d: %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                raise last_error from exc

        if last_error:
            raise last_error
        raise NightshiftQueryError("Failed to receive response from Nightshift.")

    def list_models(self) -> List[str]:
        """Return model IDs Nightshift reports at GET /v1/models."""
        self._guard()
        endpoint = f"{self._base_url()}/models"
        try:
            with httpx.Client(timeout=10.0) as c:
                resp = self._client.get(endpoint, headers=self._get_headers()) if self._client else c.get(endpoint, headers=self._get_headers())
        except httpx.TimeoutException as exc:
            raise NightshiftTimeoutError(f"Nightshift /models timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise NightshiftQueryError(f"Nightshift connection error: {exc}") from exc
        if resp.status_code in (401, 403):
            raise NightshiftAuthError(f"Nightshift auth rejected (HTTP {resp.status_code}).")
        if resp.status_code != 200:
            raise NightshiftQueryError(f"Nightshift /models returned HTTP {resp.status_code}")
        data = resp.json().get("data")
        if not isinstance(data, list):
            raise NightshiftQueryError("Nightshift /models response missing 'data' list")
        return [m["id"] for m in data if isinstance(m, dict) and m.get("id")]

    def embed(self, texts: List[str], model: str, timeout_seconds: float = 30.0) -> List[List[float]]:
        """
        OpenAI-style POST /v1/embeddings (schema per Nightshift's proxy source:
        {model, input}). Raises NightshiftQueryError (e.g. HTTP 404) when the
        running Nightshift build does not serve the route.
        """
        self._guard()
        endpoint = f"{self._base_url()}/embeddings"
        try:
            with httpx.Client(timeout=timeout_seconds) as c:
                post = self._client.post if self._client else c.post
                resp = post(endpoint, headers=self._get_headers(), json={"model": model, "input": texts})
        except httpx.TimeoutException as exc:
            raise NightshiftTimeoutError(f"Nightshift embeddings timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise NightshiftQueryError(f"Nightshift connection error: {exc}") from exc
        if resp.status_code in (401, 403):
            raise NightshiftAuthError(f"Nightshift auth rejected (HTTP {resp.status_code}).")
        if resp.status_code != 200:
            raise NightshiftQueryError(f"Nightshift embeddings returned HTTP {resp.status_code}: {resp.text[:120]}")
        body = resp.json()
        data = body.get("data")
        if not isinstance(data, list) or len(data) != len(texts) or not all(
            isinstance(d.get("embedding"), list) and d["embedding"] for d in data
        ):
            raise NightshiftQueryError("Nightshift embeddings response malformed")
        return [d["embedding"] for d in data]

    def _parse_response(self, body: Dict[str, Any], requested_model: str, elapsed_ms: float) -> NightshiftResponse:
        choices = body.get("choices")
        if not choices or not isinstance(choices, list):
            raise NightshiftQueryError(f"Nightshift response missing valid 'choices': {list(body.keys())}")

        first_choice = choices[0]
        message = first_choice.get("message", {})
        content = message.get("content", "")

        reported_model = body.get("model") or requested_model
        meterless_meta = body.get("meterless") or {}
        winning_route = meterless_meta.get("winning_route") or {}
        provider = winning_route.get("provider") or ("nvidia" if "nvidia" in reported_model.lower() else "unknown")
        receipt_id = meterless_meta.get("receipt_id")
        usage = body.get("usage")

        logger.info(
            "Nightshift response received: reported_model=%s, provider=%s, latency=%.1fms, chars=%d",
            reported_model, provider, elapsed_ms, len(content)
        )

        return NightshiftResponse(
            content=content,
            model=reported_model,
            provider=provider,
            winning_route=winning_route if winning_route else None,
            receipt_id=receipt_id,
            latency_ms=elapsed_ms,
            usage=usage,
            finish_reason=first_choice.get("finish_reason"),
            raw_metadata={
                "reported_model": reported_model,
                "provider": provider,
                "meterless_meta": {
                    k: v for k, v in meterless_meta.items()
                    if k in ("request_id", "winning_route", "receipt_id", "status", "summary")
                },
            },
        )

    def diagnostic_check(self) -> Dict[str, Any]:
        """
        Lightweight diagnostic check that makes a small verification call.
        Reports real provider and model metadata without revealing secrets.
        """
        if not self._cfg.nightshift_configured:
            return {
                "status": "not_configured",
                "configured": False,
                "message": "Nightshift is not configured. Provide NIGHTSHIFT_BASE_URL and auth token.",
                "provider": None,
                "model": None,
                "latency_ms": None,
                "error_detail": None,
            }

        try:
            start_t = time.perf_counter()
            resp = self.generate(
                messages=[{"role": "user", "content": "Respond with the single word: ONLINE"}],
                max_tokens=20,
            )
            latency = (time.perf_counter() - start_t) * 1000.0
            return {
                "status": "connected",
                "configured": True,
                "message": "Nightshift model call succeeded.",
                "provider": resp.provider,
                "model": resp.model,
                "winning_route": resp.winning_route,
                "latency_ms": round(latency, 1),
                "error_detail": None,
            }
        except NightshiftNotConfiguredError as exc:
            return {
                "status": "not_configured",
                "configured": False,
                "message": str(exc),
                "provider": None,
                "model": None,
                "latency_ms": None,
                "error_detail": None,
            }
        except NightshiftAuthError as exc:
            return {
                "status": "auth_failed",
                "configured": True,
                "message": "Nightshift authentication failed. Check token.",
                "provider": None,
                "model": None,
                "latency_ms": None,
                "error_detail": str(exc),
            }
        except (NightshiftTimeoutError, NightshiftQueryError) as exc:
            return {
                "status": "call_failed",
                "configured": True,
                "message": f"Nightshift query failed: {exc}",
                "provider": None,
                "model": None,
                "latency_ms": None,
                "error_detail": str(exc),
            }
