"""
Zetaris NDP REST API Adapter
============================
This module isolates all Zetaris-specific connectivity from the rest of the
application. It authenticates against the Zetaris NDP REST API, executes
read-only parameterized SQL queries, and normalises results.

STATUS: NOT CONFIGURED
-----------------------
The integration interface is complete. To activate live Zetaris queries:

1. Copy backend/.env.example → backend/.env
2. Set ZETARIS_ENABLED=true
3. Fill in ZETARIS_BASE_URL, ZETARIS_USERNAME, ZETARIS_PASSWORD
4. Register the five JSON files in Zetaris NDP File Store and set the
   ZETARIS_TABLE_* variables to the actual registered table names.
5. Restart the backend.

When ZETARIS_ENABLED=false (the default), every query method raises
ZetarisNotConfiguredError. The application then falls back to the local
JSON loader. Fallback mode is clearly labelled in every API response via
the `data_mode` field and in the /api/health/zetaris endpoint.

Credentials are never logged or exposed to frontend responses.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

# ── Custom exceptions ─────────────────────────────────────────────────────────


class ZetarisNotConfiguredError(Exception):
    """Raised when Zetaris credentials/URL are not set in environment."""


class ZetarisAuthError(Exception):
    """Raised when authentication against NDP fails."""


class ZetarisQueryError(Exception):
    """Raised when a SQL query against NDP returns an error."""


class ZetarisConnectionError(Exception):
    """Raised when the NDP endpoint is unreachable."""


# ── Auth token cache ──────────────────────────────────────────────────────────


class _TokenCache:
    def __init__(self) -> None:
        self.id_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def clear(self) -> None:
        self.id_token = None
        self.refresh_token = None


_token_cache = _TokenCache()


# ── Adapter ───────────────────────────────────────────────────────────────────


class ZetarisAdapter:
    """
    Thin, stateless adapter for the Zetaris NDP REST API.

    Connection Method
    -----------------
    Zetaris NDP exposes a REST API that accepts SQL queries and returns JSON
    result sets. Authentication uses a bearer-token flow:

      POST {base_url}/api/v1/auth/login
        Body: {"email": "...", "password": "..."}
        Returns: {"idToken": "...", "refreshToken": "..."}

      POST {base_url}/api/v1/query
        Header: Authorization: Bearer {idToken}
        Body: {"query": "SELECT ...", "engineId": "..."}
        Returns: [{col: val, ...}, ...]   (or a Zetaris-specific envelope)

    These endpoint paths are derived from public Zetaris documentation and
    hackathon integration guides. If your specific NDP deployment uses different
    paths (e.g. /api/v1.0/query or a proxy path), update AUTH_PATH and
    QUERY_PATH constants below.

    Required Configuration
    ----------------------
    ZETARIS_BASE_URL   – e.g. https://myorg.zetaris.app.com
    ZETARIS_USERNAME   – NDP login email
    ZETARIS_PASSWORD   – NDP login password
    ZETARIS_ENGINE_ID  – Optional compute engine ID
    ZETARIS_NAMESPACE  – e.g. lightning.ndp_filestore
    ZETARIS_TABLE_*    – Actual table names registered in NDP File Store
    """

    # Verified endpoints (local Docker, port 8888)
    # GET  /api/v1.0/auth/login  — Basic auth → {"idToken": "..."}
    # POST /api/v1.0/sql-editor/sqls/run-query  — Bearer token, X-Org-ID required
    AUTH_PATH = "/api/v1.0/auth/login"  # lives on port 8888, NOT 8889
    QUERY_PATH = "/api/v1.0/sql-editor/sqls/run-query"  # verified: 405 on GET, 400 on POST without X-Org-ID
    REFRESH_PATH = "/api/v1.0/auth/refresh"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _guard(self) -> None:
        """Raise immediately if Zetaris is not configured."""
        if not self._settings.zetaris_configured:
            raise ZetarisNotConfiguredError(
                "Zetaris integration is not configured. "
                "Set ZETARIS_ENABLED=true and provide BASE_URL / credentials in .env"
            )

    def _base_url(self) -> str:
        import os
        if (os.path.exists("/.dockerenv") or os.environ.get("IS_DOCKER")) and self._settings.docker_zetaris_base_url:
            return self._settings.docker_zetaris_base_url.rstrip("/")
        return self._settings.zetaris_base_url.rstrip("/")

    def _auth_url(self) -> str:
        # Auth (GET /api/v1.0/auth/login) is served on the same port as the API (8888).
        # The separate port 8889 is not used for this endpoint.
        return self._base_url()

    # ── Authentication ────────────────────────────────────────────────────────

    def _authenticate(self) -> str:
        """
        Authenticate against NDP and cache the bearer/api token.
        Returns the token. Credentials are never logged.
        """
        self._guard()

        # If a pre-generated token was configured directly, use it
        if self._settings.zetaris_api_token:
            return self._settings.zetaris_api_token

        if _token_cache.id_token:
            return _token_cache.id_token

        import base64
        import uuid

        # Check local Docker legacy login first
        auth_url = f"{self._auth_url()}{self.AUTH_PATH}"
        logger.info("Authenticating with Zetaris NDP (credentials redacted from logs)")

        user_pass = f"{self._settings.zetaris_username}:{self._settings.zetaris_password}"
        b64_creds = base64.b64encode(user_pass.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {b64_creds}",
            # Header name is X-Org-ID (capital ID) — the API returns 400 for X-Org-Id
            "X-Org-ID": str(self._settings.zetaris_org_id),
            "X-Request-ID": str(uuid.uuid4()),
            "Accept": "application/json",
        }

        try:
            resp = httpx.get(
                auth_url,
                headers=headers,
                timeout=self._settings.zetaris_timeout_seconds,
            )
            # If 404/405, fallback to standard JSON POST login
            if resp.status_code in (404, 405):
                resp = httpx.post(
                    f"{self._base_url()}/api/v1/auth/login",
                    json={
                        "email": self._settings.zetaris_username,
                        "password": self._settings.zetaris_password,
                    },
                    headers={"X-Org-ID": str(self._settings.zetaris_org_id)},
                    timeout=self._settings.zetaris_timeout_seconds,
                )
        except httpx.ConnectError as exc:
            raise ZetarisConnectionError(
                f"Cannot reach Zetaris NDP at {self._base_url()} or {self._auth_url()}. "
                "Check ZETARIS_BASE_URL and verify local Docker containers are running."
            ) from exc

        if resp.status_code != 200:
            _token_cache.clear()
            raise ZetarisAuthError(
                f"NDP authentication failed (HTTP {resp.status_code}). "
                "Check credentials in .env."
            )

        data = resp.json()
        _token_cache.id_token = (
            data.get("token")
            or data.get("idToken")
            or data.get("id_token")
            or data.get("apiToken")
            or (data.get("data") and data["data"].get("token"))
        )
        _token_cache.refresh_token = data.get("refreshToken") or data.get("refresh_token")

        if not _token_cache.id_token:
            _token_cache.clear()
            raise ZetarisAuthError(
                "NDP returned HTTP 200 but no token found in response. "
                f"Response keys received: {list(data.keys())}"
            )

        logger.info("Zetaris NDP authentication succeeded (token cached)")
        return _token_cache.id_token

    # ── Query execution ───────────────────────────────────────────────────────

    def execute_sql(self, sql: str) -> list[dict[str, Any]]:
        """
        Execute a read-only SQL statement against NDP.
        Returns a list of row dicts. Raises on any error.
        The full SQL is logged at DEBUG level only (no credentials).
        """
        self._guard()
        logger.debug("Zetaris SQL: %s", sql)

        token = self._authenticate()
        url = f"{self._base_url()}{self.QUERY_PATH}"
        # Key must be "sql" — the run-query endpoint rejects "query"
        payload: dict[str, Any] = {"sql": sql}
        if self._settings.zetaris_engine_id:
            payload["engineId"] = self._settings.zetaris_engine_id

        import uuid
        auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
        req_headers = {
            "Authorization": auth_header,
            # Header name is X-Org-ID (capital ID) — API returns 400 "missing" for X-Org-Id
            "X-Org-ID": str(self._settings.zetaris_org_id),
            "X-Request-ID": str(uuid.uuid4()),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            resp = httpx.post(
                url,
                json=payload,
                headers=req_headers,
                timeout=self._settings.zetaris_timeout_seconds,
            )
        except httpx.ConnectError as exc:
            _token_cache.clear()
            raise ZetarisConnectionError("Lost connection to Zetaris NDP.") from exc
        except httpx.TimeoutException as exc:
            raise ZetarisQueryError("Zetaris query timed out.") from exc

        if resp.status_code == 401:
            # Token may have expired — clear cache and retry once
            _token_cache.clear()
            token = self._authenticate()
            req_headers["Authorization"] = token if token.startswith("Bearer ") else f"Bearer {token}"
            req_headers["X-Request-ID"] = str(uuid.uuid4())
            resp = httpx.post(
                url,
                json=payload,
                headers=req_headers,
                timeout=self._settings.zetaris_timeout_seconds,
            )

        if resp.status_code != 200:
            raise ZetarisQueryError(
                f"Zetaris query failed (HTTP {resp.status_code}). "
                f"Detail: {resp.text[:500]}"
            )

        body = resp.json()
        # Verified response envelope: {"headers": ["col1", ...], "data": [[val, ...], ...], "total": N, "timeUsed": ms}
        # Convert columnar format → list of row dicts
        if isinstance(body, dict) and "headers" in body and "data" in body:
            cols = body["headers"]
            return [dict(zip(cols, row)) for row in body["data"]]
        # Fallback: plain list of dicts (older API variants)
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            for key in ("data", "rows", "results", "records"):
                if key in body and isinstance(body[key], list):
                    return body[key]
        raise ZetarisQueryError(
            f"Unexpected Zetaris response shape. Keys: {list(body.keys()) if isinstance(body, dict) else type(body)}"
        )

    # ── Connectivity test ─────────────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        """
        Attempt authentication and a trivial query.
        Returns a structured health dict; never raises publicly.
        """
        if not self._settings.zetaris_configured:
            return {
                "status": "not_configured",
                "mode": "local_fallback",
                "configured": False,
                "message": (
                    "Zetaris integration is NOT CONFIGURED. "
                    "Copy backend/.env.example to backend/.env, set ZETARIS_ENABLED=true, "
                    "and provide ZETARIS_BASE_URL, ZETARIS_USERNAME, and ZETARIS_PASSWORD."
                ),
                "tables_verified": None,
                "error_detail": None,
            }

        try:
            # Test authentication and connection first with a lightweight query
            self.execute_sql("SELECT 1")
            tables_ok: list[str] = []
            try:
                ns = self._settings.zetaris_namespace or "lightning.ndp_filestore"
                rows = self.execute_sql(f"SHOW TABLES IN {ns}")
                found = {r.get("table_identifier") for r in rows if isinstance(r, dict)}
                for key in ["police_incidents", "newspaper_reports", "witness_reports", "cctv_reports", "forensic_reports"]:
                    tbl = getattr(self._settings, f"zetaris_table_{key}", key)
                    if tbl in found or f"{ns}.{tbl}" in found:
                        tables_ok.append(self._settings.table_fqn(key))
            except Exception:
                pass

            return {
                "status": "connected",
                "mode": "zetaris_live" if tables_ok else "local_fallback",
                "configured": True,
                "message": (
                    "Zetaris NDP connection and test query succeeded." if tables_ok
                    else "Zetaris NDP authenticated successfully. (Tables pending in File Store; local fallback active)."
                ),
                "tables_verified": tables_ok,
                "error_detail": None if tables_ok else "Tables not yet registered in NDP File Store",
            }
        except ZetarisNotConfiguredError as exc:
            return {
                "status": "not_configured",
                "mode": "local_fallback",
                "configured": False,
                "message": str(exc),
                "tables_verified": None,
                "error_detail": None,
            }
        except ZetarisAuthError as exc:
            return {
                "status": "connection_failed",
                "mode": "local_fallback",
                "configured": True,
                "message": "Zetaris authentication failed. Check credentials.",
                "tables_verified": None,
                "error_detail": str(exc),
            }
        except (ZetarisConnectionError, ZetarisQueryError) as exc:
            return {
                "status": "query_failed",
                "mode": "local_fallback",
                "configured": True,
                "message": "Zetaris is configured but the test query failed.",
                "tables_verified": None,
                "error_detail": str(exc),
            }
