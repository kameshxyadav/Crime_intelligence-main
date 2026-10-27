"""
Nemotron Model Registry
=======================
Maps agent roles / retrieval operations to Nightshift model IDs, verifies each
configured ID against Nightshift's own ``GET /v1/models`` catalogue, and
records what actually handled every request.

Rules enforced here:
- A configured model that Nightshift does not list is reported UNAVAILABLE and
  the role runs on the verified fallback (Lightning) - never a made-up ID.
- A call that fails on its specialist model may retry once on the fallback; the
  call record says so (``fallback_used``) so reports cannot imply the
  specialist ran.
- The reported model comes from the response body, not from our request.
- Embedding and rerank are different operations from chat; they are probed on
  their own routes and are never sent through chat completions.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.config import Settings, settings
from app.services.nightshift_client import (
    NightshiftAuthError,
    NightshiftClient,
    NightshiftNotConfiguredError,
    NightshiftQueryError,
    NightshiftResponse,
    NightshiftTimeoutError,
)

logger = logging.getLogger(__name__)

CHAT_ROLES = ("planner", "finder", "skeptic", "reporter")
ALL_ROLES = (*CHAT_ROLES, "embedding", "rerank")

# Candidate assignments from the design brief; informational only.
CANDIDATES = {
    "scout_intent_llm": "Nemotron 3.5 Bolt E4B",
    "rerank": "Nemotron 3.5 Rerank 8B",
}


@dataclass
class RoleAssignment:
    role: str
    operation: str                       # chat | embeddings | rerank
    configured_model: Optional[str]
    effective_model: Optional[str]       # what we will request
    fallback_model: Optional[str]
    status: str                          # verified | fallback | unavailable | unverified
    reason: str = ""


@dataclass
class CallRecord:
    """What one model call actually did. Safe to log (no secrets, no prompts)."""
    role: str
    requested_model: str
    reported_model: Optional[str] = None
    provider: Optional[str] = None
    receipt_id: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    latency_ms: Optional[float] = None
    status: str = "ok"
    error: Optional[str] = None
    routed_as_requested: Optional[bool] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelRegistry:
    def __init__(self, cfg: Optional[Settings] = None, client: Optional[NightshiftClient] = None) -> None:
        self._cfg = cfg or settings
        self._client = client or NightshiftClient(self._cfg)
        self._catalog: Optional[List[str]] = None
        self._catalog_error: Optional[str] = None
        self._embedding_probe: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    # ── configuration ────────────────────────────────────────────────────
    def _configured(self, role: str) -> Optional[str]:
        return {
            "planner": self._cfg.nightshift_model_planner,
            "finder": self._cfg.nightshift_model_finder,
            "skeptic": self._cfg.nightshift_model_skeptic,
            "reporter": self._cfg.nightshift_model_reporter,
            "embedding": self._cfg.nightshift_model_embedding,
            "rerank": self._cfg.nightshift_model_rerank,
        }[role] or None

    @property
    def fallback_model(self) -> str:
        return self._cfg.fallback_model

    # ── catalogue ────────────────────────────────────────────────────────
    def catalog(self, refresh: bool = False) -> Optional[List[str]]:
        """Model IDs Nightshift lists, or None if it could not be queried."""
        with self._lock:
            if self._catalog is not None and not refresh:
                return self._catalog
            try:
                self._catalog = self._client.list_models()
                self._catalog_error = None
            except (NightshiftNotConfiguredError, NightshiftAuthError, NightshiftQueryError, NightshiftTimeoutError) as exc:
                self._catalog = None
                self._catalog_error = str(exc)
            return self._catalog

    def assignment(self, role: str) -> RoleAssignment:
        if role not in ALL_ROLES:
            raise ValueError(f"unknown role: {role}")
        operation = {"embedding": "embeddings", "rerank": "rerank"}.get(role, "chat")
        configured = self._configured(role)
        catalog = self.catalog()

        if operation == "rerank":
            if not configured:
                return RoleAssignment(role, operation, None, None, None, "unavailable",
                                      f"No rerank model configured; {CANDIDATES['rerank']} is not served by this Nightshift build.")
            listed = catalog is not None and configured in catalog
            return RoleAssignment(role, operation, configured, None, None, "unavailable",
                                  "Rerank has no verified Nightshift route in this build; not enabled."
                                  + ("" if listed else " Model is also not in /v1/models."))

        if operation == "embeddings":
            if not configured:
                return RoleAssignment(role, operation, None, None, None, "unavailable", "No embedding model configured.")
            if catalog is None:
                return RoleAssignment(role, operation, configured, configured, None, "unverified",
                                      f"Catalogue unavailable: {self._catalog_error}")
            if configured not in catalog:
                return RoleAssignment(role, operation, configured, None, None, "unavailable", "Model not listed by Nightshift.")
            probe = self._embedding_probe
            if probe is None:
                return RoleAssignment(role, operation, configured, configured, None, "unverified",
                                      "Listed by Nightshift; /v1/embeddings route not yet probed.")
            if not probe["ok"]:
                return RoleAssignment(role, operation, configured, None, None, "unavailable",
                                      f"Listed by Nightshift but /v1/embeddings failed: {probe['detail']}")
            return RoleAssignment(role, operation, configured, configured, None, "verified", "Embeddings route answered.")

        # chat roles
        fb = self.fallback_model
        if not configured or configured == fb:
            status = "verified" if (catalog is not None and fb in catalog) else "unverified"
            reason = "Lightning (default text model)." if status == "verified" else f"Catalogue check unavailable: {self._catalog_error or 'model not listed'}"
            return RoleAssignment(role, operation, configured, fb, fb, status, reason)
        if catalog is None:
            return RoleAssignment(role, operation, configured, configured, fb, "unverified",
                                  f"Catalogue unavailable ({self._catalog_error}); will attempt, fallback to {fb}.")
        if configured in catalog:
            return RoleAssignment(role, operation, configured, configured, fb, "verified", "Listed by Nightshift.")
        return RoleAssignment(role, operation, configured, fb, fb, "fallback",
                              f"{configured} is not listed by Nightshift; using fallback {fb}.")

    def probe_embeddings(self) -> Dict[str, Any]:
        """One real call to the embeddings route. Result cached for the process."""
        model = self._configured("embedding")
        if not model:
            self._embedding_probe = {"ok": False, "detail": "not configured"}
            return self._embedding_probe
        try:
            vecs = self._client.embed(["probe"], model)
            self._embedding_probe = {"ok": True, "detail": f"dim={len(vecs[0])}"}
        except (NightshiftQueryError, NightshiftTimeoutError, NightshiftAuthError, NightshiftNotConfiguredError) as exc:
            self._embedding_probe = {"ok": False, "detail": str(exc)[:160]}
        return self._embedding_probe

    def report(self, probe: bool = False) -> Dict[str, Any]:
        if probe:
            self.probe_embeddings()
        return {
            "catalog_checked": self.catalog() is not None,
            "catalog_error": self._catalog_error,
            "fallback_model": self.fallback_model,
            "roles": {r: asdict(self.assignment(r)) for r in ALL_ROLES},
            "not_served": {
                "bolt_e4b": "Not present in Nightshift /v1/models" if self.catalog() is not None and not any("bolt" in m.lower() for m in self.catalog() or []) else "unknown",
                "rerank_8b": "Not present in Nightshift /v1/models" if self.catalog() is not None and not any("rerank" in m.lower() for m in self.catalog() or []) else "unknown",
            },
        }

    # ── generation ───────────────────────────────────────────────────────
    def generate(
        self,
        role: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1200,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
    ) -> tuple[NightshiftResponse, CallRecord]:
        if role not in CHAT_ROLES:
            raise ValueError(f"role {role!r} is not a chat role")
        a = self.assignment(role)
        target = a.effective_model or self.fallback_model
        timeout = timeout_seconds
        if role == "skeptic" and timeout is None and target != self.fallback_model:
            timeout = float(self._cfg.nightshift_skeptic_timeout_seconds)

        rec = CallRecord(role=role, requested_model=target)
        if a.status == "fallback":
            rec.fallback_used = True
            rec.fallback_reason = a.reason

        def _call(model: str, retries: Optional[int]) -> NightshiftResponse:
            extra = None
            if model != self.fallback_model and timeout:
                # Nightshift's per-request cloud first-token limit (ms, max 300000); large specialist
                # models otherwise hit the default limit and are stopped (observed with Ultra 550B).
                extra = {"meterless-ttfb-ms": str(int(min(300000, timeout * 1000)))}
            return self._client.generate(
                messages=messages, model=model, max_tokens=max_tokens, temperature=temperature,
                timeout_seconds=timeout, max_retries=retries, extra_headers=extra,
            )

        try:
            # Specialist gets a single attempt so a slow/failed model falls back quickly.
            resp = _call(target, 1 if target != self.fallback_model else None)
        except (NightshiftQueryError, NightshiftTimeoutError) as exc:
            if target == self.fallback_model:
                rec.status, rec.error = "error", str(exc)[:200]
                raise
            logger.warning("Role %s: %s failed (%s); retrying on fallback %s", role, target, exc, self.fallback_model)
            rec.fallback_used = True
            rec.fallback_reason = f"{target} failed: {str(exc)[:120]}"
            rec.requested_model = self.fallback_model
            try:
                resp = _call(self.fallback_model, None)
            except Exception as exc2:
                rec.status, rec.error = "error", str(exc2)[:200]
                raise

        rec.reported_model = resp.model
        rec.provider = resp.provider
        rec.receipt_id = resp.receipt_id
        rec.latency_ms = resp.latency_ms
        rec.routed_as_requested = (resp.model == rec.requested_model)
        usage = resp.usage or {}
        rec.prompt_tokens, rec.completion_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
        return resp, rec


model_registry = ModelRegistry()
