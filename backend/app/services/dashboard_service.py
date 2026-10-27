"""
Dashboard service layer.
Routes queries to ZetarisAdapter (when configured) or LocalDataLoader (fallback).

When Zetaris is active every method issues real SQL against the registered Lightning
tables and returns data_mode='zetaris_live'.  When Zetaris is not configured the
LocalDataLoader is used and data_mode='local_fallback' is returned.

Array columns (property_involved, source_reference_ids, …) are stored in Zetaris as
JSON strings — this layer parses them back to Python lists before returning.
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Optional

from app.config import settings
from app.services.local_data_loader import (
    SOURCE_DESCRIPTIONS,
    SOURCE_LABELS,
    SOURCE_PRIMARY_KEYS,
    LocalDataLoader,
)
from app.services.zetaris_adapter import (
    ZetarisAdapter,
    ZetarisNotConfiguredError,
)

logger = logging.getLogger(__name__)

_loader = LocalDataLoader(settings)
_zetaris = ZetarisAdapter(settings)
_zetaris_tables_ready: Optional[bool] = None


def check_zetaris_tables_ready(force_recheck: bool = False) -> bool:
    global _zetaris_tables_ready
    if not settings.zetaris_configured:
        return False
    if _zetaris_tables_ready is not None and not force_recheck:
        return _zetaris_tables_ready
    try:
        ns = settings.zetaris_namespace or "lightning.ndp_filestore"
        rows = _zetaris.execute_sql(f"SHOW TABLES IN {ns}")
        found = {r.get("table_identifier") for r in rows if isinstance(r, dict)}
        tbl = settings.zetaris_table_police_incidents
        if tbl in found or f"{ns}.{tbl}" in found:
            _zetaris_tables_ready = True
            return True
        _zetaris_tables_ready = False
        return False
    except Exception as exc:
        logger.info("Zetaris is connected but tables are not yet registered: %s", exc)
        _zetaris_tables_ready = False
        return False


def _use_zetaris() -> bool:
    return settings.zetaris_configured and check_zetaris_tables_ready()


# ── Array-column helpers ──────────────────────────────────────────────────────

# Columns that Zetaris stores as JSON-serialised strings
_ARRAY_COLS: set[str] = {
    "property_involved",
    "source_reference_ids",
    "crime_labels",
    "mentioned_location_ids",
    "mentioned_property",
    "related_incident_ids",
    "observed_entities",
    "contradiction_flags",
    "compared_evidence_ids",
}


def _parse_row(row: dict) -> dict:
    """Parse JSON-string array columns back to Python lists.

    Zetaris may return array columns as:
    - A native Python list (ARRAY<STRING> columns) — leave as-is.
    - A JSON-serialised string (when stored as plain STRING) — parse with json.loads.
    """
    out = dict(row)
    for col in _ARRAY_COLS:
        if col in out and isinstance(out[col], str):
            try:
                out[col] = json.loads(out[col])
            except (json.JSONDecodeError, TypeError):
                out[col] = []
        # Already a list from Zetaris native ARRAY type — nothing to do
    # Cast numeric strings
    if "estimated_loss" in out and out["estimated_loss"] is not None:
        try:
            out["estimated_loss"] = float(out["estimated_loss"])
        except (TypeError, ValueError):
            pass
    if "observation_confidence" in out and out["observation_confidence"] is not None:
        try:
            out["observation_confidence"] = float(out["observation_confidence"])
        except (TypeError, ValueError):
            pass
    return out


def _parse_rows(rows: list[dict]) -> list[dict]:
    return [_parse_row(r) for r in rows]


def _paginate(total: int, page: int, page_size: int) -> dict:
    total_pages = max(1, math.ceil(total / page_size))
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


# ── Dashboard summary ─────────────────────────────────────────────────────────


def get_dashboard_summary() -> dict[str, Any]:
    if not _use_zetaris():
        return _loader.get_dashboard_summary()

    fqn = settings.table_fqn("police_incidents")

    # Total count
    total_rows = _zetaris.execute_sql(f"SELECT COUNT(*) AS cnt FROM {fqn}")
    total = int(total_rows[0]["cnt"]) if total_rows else 0

    # By station
    station_rows = _zetaris.execute_sql(
        f"SELECT station_id, COUNT(*) AS cnt FROM {fqn} GROUP BY station_id ORDER BY station_id"
    )
    by_station = [{"station_id": r["station_id"], "count": int(r["cnt"])} for r in station_rows]

    # By crime type (top 20)
    crime_rows = _zetaris.execute_sql(
        f"SELECT crime_type, COUNT(*) AS cnt FROM {fqn} GROUP BY crime_type ORDER BY cnt DESC LIMIT 20"
    )
    by_crime_type = [{"crime_type": r["crime_type"], "count": int(r["cnt"])} for r in crime_rows]

    # By status
    status_rows = _zetaris.execute_sql(
        f"SELECT status, COUNT(*) AS cnt FROM {fqn} GROUP BY status ORDER BY status"
    )
    by_status = [{"status": r["status"], "count": int(r["cnt"])} for r in status_rows]

    # By source (record counts from all 5 tables)
    by_source = []
    for key in ["police_incidents", "newspaper_reports", "witness_reports", "cctv_reports", "forensic_reports"]:
        count_rows = _zetaris.execute_sql(
            f"SELECT COUNT(*) AS cnt FROM {settings.table_fqn(key)}"
        )
        cnt = int(count_rows[0]["cnt"]) if count_rows else 0
        by_source.append({"source": key, "count": cnt})

    # Incident timeline by month (YYYY-MM) — use SUBSTR on reported_at string
    timeline_rows = _zetaris.execute_sql(
        f"""
        SELECT SUBSTR(reported_at, 1, 7) AS period, COUNT(*) AS cnt
        FROM {fqn}
        WHERE reported_at IS NOT NULL
        GROUP BY SUBSTR(reported_at, 1, 7)
        ORDER BY period
        """
    )
    incident_timeline = [{"period": r["period"], "count": int(r["cnt"])} for r in timeline_rows]

    return {
        "total_incidents": total,
        "by_station": by_station,
        "by_crime_type": by_crime_type,
        "by_status": by_status,
        "by_source": by_source,
        "incident_timeline": incident_timeline,
        "data_mode": "zetaris_live",
    }


# ── Incidents ─────────────────────────────────────────────────────────────────

_ALLOWED_SORT = {
    "reported_at", "occurred_from", "crime_type",
    "station_id", "status", "estimated_loss",
}


def get_incidents(
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    station: Optional[str] = None,
    crime_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "reported_at",
    sort_desc: bool = True,
) -> dict[str, Any]:
    if not _use_zetaris():
        return _loader.get_incidents(
            page=page, page_size=page_size, search=search,
            station=station, crime_type=crime_type, status=status,
            date_from=date_from, date_to=date_to,
            sort_by=sort_by, sort_desc=sort_desc,
        )

    if sort_by not in _ALLOWED_SORT:
        sort_by = "reported_at"
    order_dir = "DESC" if sort_desc else "ASC"
    fqn = settings.table_fqn("police_incidents")

    # Build WHERE clauses (no user values interpolated unsafely — all are
    # controlled enums or ISO date strings validated by Pydantic at the router)
    where: list[str] = []
    if station:
        where.append(f"station_id = '{station.upper()}'")
    if crime_type:
        where.append(f"crime_type = '{crime_type.upper()}'")
    if status:
        where.append(f"status = '{status.upper()}'")
    if date_from:
        where.append(f"reported_at >= '{date_from}'")
    if date_to:
        where.append(f"reported_at <= '{date_to}'")
    if search:
        q = search.replace("'", "''")  # basic SQL escaping
        where.append(
            f"(LOWER(location_description) LIKE '%{q.lower()}%' "
            f"OR LOWER(method_description) LIKE '%{q.lower()}%' "
            f"OR LOWER(incident_id) LIKE '%{q.lower()}%' "
            f"OR LOWER(crime_type) LIKE '%{q.lower()}%')"
        )

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    # Count total matching rows
    count_rows = _zetaris.execute_sql(
        f"SELECT COUNT(*) AS cnt FROM {fqn} {where_sql}"
    )
    total = int(count_rows[0]["cnt"]) if count_rows else 0

    # Fetch page
    offset = (page - 1) * page_size
    data_rows = _zetaris.execute_sql(
        f"""
        SELECT * FROM {fqn}
        {where_sql}
        ORDER BY {sort_by} {order_dir}
        LIMIT {page_size} OFFSET {offset}
        """
    )

    return {
        "items": _parse_rows(data_rows),
        "pagination": _paginate(total, page, page_size),
        "data_mode": "zetaris_live",
    }


def get_incident_by_id(incident_id: str) -> Optional[dict]:
    if not _use_zetaris():
        return _loader.get_incident_by_id(incident_id)

    fqn = settings.table_fqn("police_incidents")
    iid = incident_id.replace("'", "''")
    rows = _zetaris.execute_sql(
        f"SELECT * FROM {fqn} WHERE incident_id = '{iid}' LIMIT 1"
    )
    return _parse_row(rows[0]) if rows else None


# ── Sources ───────────────────────────────────────────────────────────────────


def get_sources_info() -> list[dict]:
    if not _use_zetaris():
        return _loader.get_sources_info()

    result = []
    for key in ["police_incidents", "newspaper_reports", "witness_reports",
                "cctv_reports", "forensic_reports"]:
        count_rows = _zetaris.execute_sql(
            f"SELECT COUNT(*) AS cnt FROM {settings.table_fqn(key)}"
        )
        cnt = int(count_rows[0]["cnt"]) if count_rows else 0
        result.append({
            "name": key,
            "label": SOURCE_LABELS[key],
            "record_count": cnt,
            "primary_key_field": SOURCE_PRIMARY_KEYS[key],
            "description": SOURCE_DESCRIPTIONS[key],
        })
    return result


def get_source_records(
    source: str,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
) -> dict[str, Any]:
    if not _use_zetaris():
        return _loader.get_source_records(source, page=page, page_size=page_size, search=search)

    fqn = settings.table_fqn(source)

    where_sql = ""
    if search:
        q = search.replace("'", "''").lower()
        pk = SOURCE_PRIMARY_KEYS.get(source, "")
        # Search in primary key field for a fast targeted filter
        where_sql = f"WHERE LOWER({pk}) LIKE '%{q}%'"

    count_rows = _zetaris.execute_sql(f"SELECT COUNT(*) AS cnt FROM {fqn} {where_sql}")
    total = int(count_rows[0]["cnt"]) if count_rows else 0

    offset = (page - 1) * page_size
    data_rows = _zetaris.execute_sql(
        f"SELECT * FROM {fqn} {where_sql} LIMIT {page_size} OFFSET {offset}"
    )

    return {
        "source": source,
        "items": _parse_rows(data_rows),
        "pagination": _paginate(total, page, page_size),
        "data_mode": "zetaris_live",
    }


def get_source_record_by_id(source: str, record_id: str) -> Optional[dict]:
    if not _use_zetaris():
        return _loader.get_source_record_by_id(source, record_id)

    fqn = settings.table_fqn(source)
    pk = SOURCE_PRIMARY_KEYS.get(source, "id")
    rid = record_id.replace("'", "''")
    rows = _zetaris.execute_sql(
        f"SELECT * FROM {fqn} WHERE {pk} = '{rid}' LIMIT 1"
    )
    return _parse_row(rows[0]) if rows else None


# ── Cross-source evidence ─────────────────────────────────────────────────────


def get_incident_evidence(incident_id: str) -> dict[str, Any]:
    """
    Return direct and inferred links across all source tables for one incident.

    Direct links  — rows that explicitly reference this incident_id.
    Inferred links — rows at the same location_id on the same calendar date.
    """
    if not _use_zetaris():
        return _loader.get_incident_evidence(incident_id)

    iid = incident_id.replace("'", "''")

    # Fetch the anchor incident
    incident_rows = _zetaris.execute_sql(
        f"SELECT * FROM {settings.table_fqn('police_incidents')} "
        f"WHERE incident_id = '{iid}' LIMIT 1"
    )
    incident = _parse_row(incident_rows[0]) if incident_rows else None

    direct_links: list[dict] = []
    inferred_links: list[dict] = []

    # Source tables and their link/PK fields
    sources_cfg = {
        "newspaper_reports": ("news_id",           "related_incident_ids", None),
        "witness_reports":   ("witness_report_id",  "related_incident_ids", None),
        "cctv_reports":      ("cctv_report_id",     "related_incident_ids", None),
        "forensic_reports":  ("evidence_report_id", "incident_id",          "incident_id"),
    }

    inc_location = incident.get("location_id") if incident else None
    inc_date = (incident.get("occurred_from") or incident.get("reported_at") or "")[:10] if incident else ""

    for src, (pk_field, link_field, exact_field) in sources_cfg.items():
        fqn = settings.table_fqn(src)

        # ── Direct: exact string match (forensic_reports.incident_id) ─────────
        if exact_field:
            direct_rows = _zetaris.execute_sql(
                f"SELECT * FROM {fqn} WHERE {exact_field} = '{iid}' LIMIT 50"
            )
            for r in _parse_rows(direct_rows):
                direct_links.append({
                    "source": src,
                    "record_id": r.get(pk_field, ""),
                    "link_type": "direct_reference",
                    "link_basis": "Explicit incident_id match in forensic record",
                    "record": r,
                })

        # ── Direct: JSON-array column contains this incident_id ───────────────
        # Zetaris stores these as native ARRAY<STRING> — use ARRAY_CONTAINS.
        else:
            direct_rows = _zetaris.execute_sql(
                f"SELECT * FROM {fqn} "
                f"WHERE ARRAY_CONTAINS({link_field}, '{iid}') LIMIT 50"
            )
            for r in _parse_rows(direct_rows):
                direct_links.append({
                    "source": src,
                    "record_id": r.get(pk_field, ""),
                    "link_type": "direct_reference",
                    "link_basis": "Explicit ID reference in source record",
                    "record": r,
                })

        # ── Inferred: same location on same date ──────────────────────────────
        # Each table uses different column names for location and date.
        # newspaper_reports has no scalar location_id — skip inferred for it.
        inferred_cfg = {
            "witness_reports":  ("location_id", "submitted_at"),
            "cctv_reports":     ("location_id", "recorded_from"),
            "forensic_reports": ("location_id", "collected_at"),
        }
        if inc_location and inc_date and src in inferred_cfg:
            loc_col, date_col = inferred_cfg[src]
            loc = inc_location.replace("'", "''")
            inferred_rows = _zetaris.execute_sql(
                f"SELECT * FROM {fqn} "
                f"WHERE {loc_col} = '{loc}' "
                f"AND SUBSTR(COALESCE({date_col}, ''), 1, 10) = '{inc_date}' "
                f"LIMIT 20"
            )
            direct_ids = {lnk["record_id"] for lnk in direct_links if lnk["source"] == src}
            for r in _parse_rows(inferred_rows):
                if r.get(pk_field) not in direct_ids:
                    inferred_links.append({
                        "source": src,
                        "record_id": r.get(pk_field, ""),
                        "link_type": "inferred_spatial_temporal",
                        "link_basis": (
                            "Same location_id and overlapping date. "
                            "This is an investigative lead — NOT a confirmed relationship."
                        ),
                        "record": r,
                    })

    return {
        "incident_id": incident_id,
        "incident": incident,
        "direct_links": direct_links,
        "inferred_links": inferred_links,
        "data_mode": "zetaris_live",
        "caveat": (
            "Direct links are based on explicit ID references in source records. "
            "Inferred links are based on matching location and date — they are investigative leads only, "
            "not confirmed evidence relationships."
        ),
    }


# ── Health ────────────────────────────────────────────────────────────────────


def get_zetaris_health() -> dict[str, Any]:
    return _zetaris.health_check()
