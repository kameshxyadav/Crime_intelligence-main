"""
Zetaris SQL Investigation Service
=================================
Executes real SQL queries across the 5 tables registered in Zetaris NDP
to retrieve cross-station incident records and associated forensic, CCTV,
witness, and news evidence.

Strict Data Provenance:
- Uses actual SQL through Zetaris NDP.
- Bounded candidate retrieval (never sends all 10,000 records).
- Preserves all primary keys, station identifiers, data quality ratings,
  contradiction flags, and timestamps.
- Returns explicit errors if Zetaris is unavailable in live mode.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from app.config import Settings, settings
from app.services.zetaris_adapter import (
    ZetarisAdapter,
    ZetarisNotConfiguredError,
    ZetarisQueryError,
)

logger = logging.getLogger(__name__)


def _sanitize_term(term: str) -> str:
    """Strip SQL injection hazards and punctuation from search terms."""
    return re.sub(r"[^A-Za-z0-9_\- ]", "", term).strip()


def _parse_json_field(val: Any) -> Any:
    """Parse stringified JSON arrays or return as-is."""
    if isinstance(val, str):
        val_str = val.strip()
        if (val_str.startswith("[") and val_str.endswith("]")) or (val_str.startswith("{") and val_str.endswith("}")):
            try:
                return json.loads(val_str)
            except Exception:
                return val
    return val if val is not None else []


class ZetarisInvestigationService:
    """Service for running real SQL data retrieval for investigations."""

    def __init__(self, cfg: Optional[Settings] = None, adapter: Optional[ZetarisAdapter] = None) -> None:
        self._cfg = cfg or settings
        self._adapter = adapter or ZetarisAdapter(self._cfg)
        self.query_count = 0
        self.errors: List[str] = []   # per-source retrieval failures that were tolerated

    def _sql(self, sql: str) -> List[Dict[str, Any]]:
        """Single choke point for SQL so queries can be counted and traced."""
        self.query_count += 1
        return self._adapter.execute_sql(sql)

    def _ensure_connected(self) -> None:
        if not self._cfg.zetaris_configured:
            raise ZetarisNotConfiguredError(
                "Zetaris is not configured. Live investigations require active Zetaris NDP connection."
            )

    def search_candidate_incidents(
        self,
        keywords: Optional[List[str]] = None,
        crime_types: Optional[List[str]] = None,
        station_ids: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Query candidate police incidents across stations using parameterized SQL.
        """
        self._ensure_connected()
        table = self._cfg.table_fqn("police_incidents")

        conditions: List[str] = []

        if station_ids:
            clean_stations = [f"'{_sanitize_term(s)}'" for s in station_ids if _sanitize_term(s)]
            if clean_stations:
                conditions.append(f"station_id IN ({', '.join(clean_stations)})")

        if crime_types:
            clean_crimes = [f"'{_sanitize_term(c)}'" for c in crime_types if _sanitize_term(c)]
            if clean_crimes:
                conditions.append(f"crime_type IN ({', '.join(clean_crimes)})")

        if date_from:
            clean_df = _sanitize_term(date_from)
            conditions.append(f"reported_at >= '{clean_df}'")

        if date_to:
            clean_dt = _sanitize_term(date_to)
            conditions.append(f"reported_at <= '{clean_dt}'")

        if keywords:
            kw_clauses = []
            for kw in keywords:
                clean_kw = _sanitize_term(kw).lower()
                if clean_kw and len(clean_kw) >= 3:
                    kw_clauses.append(f"LOWER(method_description) LIKE '%{clean_kw}%'")
                    kw_clauses.append(f"LOWER(cast(property_involved as string)) LIKE '%{clean_kw}%'")
            if kw_clauses:
                conditions.append(f"({' OR '.join(kw_clauses)})")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM {table} {where_clause} ORDER BY reported_at DESC LIMIT {limit}"

        logger.info("Executing Zetaris candidate incidents SQL: %s", sql)
        rows = self._sql(sql)

        # Normalize parsed JSON fields
        for r in rows:
            r["property_involved"] = _parse_json_field(r.get("property_involved"))
            r["source_reference_ids"] = _parse_json_field(r.get("source_reference_ids"))

        return rows

    def get_incidents_by_ids(self, incident_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch specific police incidents by ID."""
        if not incident_ids:
            return []
        self._ensure_connected()
        table = self._cfg.table_fqn("police_incidents")

        clean_ids = [f"'{_sanitize_term(i)}'" for i in incident_ids if _sanitize_term(i)]
        if not clean_ids:
            return []

        sql = f"SELECT * FROM {table} WHERE incident_id IN ({', '.join(clean_ids)})"
        rows = self._sql(sql)
        for r in rows:
            r["property_involved"] = _parse_json_field(r.get("property_involved"))
            r["source_reference_ids"] = _parse_json_field(r.get("source_reference_ids"))
        return rows

    def get_incidents_by_locations(self, location_ids: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Other incidents recorded at the same locations (location/timeline comparison)."""
        clean = [f"'{_sanitize_term(l)}'" for l in location_ids if _sanitize_term(l)]
        if not clean:
            return []
        self._ensure_connected()
        table = self._cfg.table_fqn("police_incidents")
        rows = self._sql(f"SELECT * FROM {table} WHERE location_id IN ({', '.join(clean)}) ORDER BY reported_at DESC LIMIT {int(limit)}")
        for r in rows:
            r["property_involved"] = _parse_json_field(r.get("property_involved"))
            r["source_reference_ids"] = _parse_json_field(r.get("source_reference_ids"))
        return rows

    def retrieve_supporting_evidence(
        self,
        incident_ids: List[str],
        location_ids: List[str],
        limit_per_source: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query CCTV, witness, forensic, and newspaper records for the candidate incidents.

        Two bounded queries per source so that records carrying an explicit reference to a
        candidate incident are never crowded out by same-location noise:
          1. direct references (incident_id / related_incident_ids)  -> link_basis="direct_reference"
          2. same location_id (context only)                          -> link_basis="location_proximity"
        Every returned row carries ``link_basis`` as provenance.
        """
        self._ensure_connected()
        evidence: Dict[str, List[Dict[str, Any]]] = {
            "cctv_reports": [], "witness_reports": [], "forensic_reports": [], "newspaper_reports": [],
        }
        clean_incidents = [_sanitize_term(i) for i in incident_ids if _sanitize_term(i)]
        clean_locations = [_sanitize_term(l) for l in location_ids if _sanitize_term(l)]
        direct_limit = min(24, limit_per_source * max(1, (len(clean_incidents) + 1) // 2))
        context_limit = max(2, limit_per_source // 2)

        def like_refs(col: str) -> List[str]:
            return [f"LOWER(cast({col} as string)) LIKE '%{i.lower()}%'" for i in clean_incidents]

        def in_list(col: str, vals: List[str]) -> str:
            return f"{col} IN ({', '.join(repr(v) for v in vals)})"

        # (source key, table key, primary id column, direct-reference clauses, location clause, json fields)
        specs = [
            ("forensic_reports", "forensic_reports", "evidence_report_id",
             [in_list("incident_id", clean_incidents)] if clean_incidents else [],
             in_list("location_id", clean_locations) if clean_locations else None, ["compared_evidence_ids"]),
            ("cctv_reports", "cctv_reports", "cctv_report_id", like_refs("related_incident_ids"),
             in_list("location_id", clean_locations) if clean_locations else None, ["observed_entities", "related_incident_ids"]),
            ("witness_reports", "witness_reports", "witness_report_id", like_refs("related_incident_ids"),
             in_list("location_id", clean_locations) if clean_locations else None,
             ["observed_entities", "related_incident_ids", "contradiction_flags"]),
            ("newspaper_reports", "newspaper_reports", "news_id", like_refs("related_incident_ids"),
             " OR ".join(f"LOWER(cast(mentioned_location_ids as string)) LIKE '%{l.lower()}%'" for l in clean_locations) or None,
             ["crime_labels", "mentioned_property", "mentioned_location_ids", "related_incident_ids"]),
        ]
        for key, table_key, pk, direct, location, json_fields in specs:
            try:
                table = self._cfg.table_fqn(table_key)
                rows: List[Dict[str, Any]] = []
                seen: Set[Any] = set()
                for basis, clause, limit in (("direct_reference", " OR ".join(direct), direct_limit),
                                             ("location_proximity", location, context_limit)):
                    if not clause:
                        continue
                    for r in self._sql(f"SELECT * FROM {table} WHERE {clause} LIMIT {int(limit)}"):
                        if r.get(pk) in seen:
                            continue
                        seen.add(r.get(pk))
                        r["link_basis"] = basis
                        for f in json_fields:
                            r[f] = _parse_json_field(r.get(f))
                        rows.append(r)
                evidence[key] = rows
            except Exception as exc:
                logger.warning("Error querying %s from Zetaris: %s", key, exc)
                self.errors.append(f"{key}: " + str(exc)[:160])

        return evidence


zetaris_investigation_service = ZetarisInvestigationService()
