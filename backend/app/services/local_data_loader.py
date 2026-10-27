"""
Local JSON data loader — used as the fallback when Zetaris is not configured.

Every public method in this module mirrors the interface expected by
dashboard_service.py so the service layer can swap backends transparently.

All responses are tagged data_mode='local_fallback'. The API surface ensures
callers always know which mode is active.

IMPORTANT: data/evaluation/ground_truth.json is intentionally excluded.
This loader must NEVER load, read, or expose ground_truth.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.config import Settings

logger = logging.getLogger(__name__)

# ── Source file registry ──────────────────────────────────────────────────────

SOURCE_FILES = {
    "police_incidents":   "police_incidents.json",
    "newspaper_reports":  "newspaper_reports.json",
    "witness_reports":    "witness_reports.json",
    "cctv_reports":       "cctv_reports.json",
    "forensic_reports":   "forensic_reports.json",
    # ground_truth.json is intentionally absent
}

SOURCE_PRIMARY_KEYS = {
    "police_incidents":  "incident_id",
    "newspaper_reports": "news_id",
    "witness_reports":   "witness_report_id",
    "cctv_reports":      "cctv_report_id",
    "forensic_reports":  "evidence_report_id",
}

SOURCE_LABELS = {
    "police_incidents":  "Police Incidents",
    "newspaper_reports": "Newspaper Reports",
    "witness_reports":   "Witness Reports",
    "cctv_reports":      "CCTV Reports",
    "forensic_reports":  "Forensic Reports",
}

SOURCE_DESCRIPTIONS = {
    "police_incidents":  "Formal police incident reports across NORTH, CENTRAL, and RIVERSIDE stations.",
    "newspaper_reports": "Public press coverage and police blotter entries.",
    "witness_reports":   "Eyewitness statements and suspect sighting reports.",
    "cctv_reports":      "Surveillance camera feeds and optical observations.",
    "forensic_reports":  "Physical, biological, chemical, and digital evidence lab analyses.",
}

# ── Cache ─────────────────────────────────────────────────────────────────────

_cache: dict[str, list[dict]] = {}


def _load(source: str, data_dir: Path) -> list[dict]:
    if source not in SOURCE_FILES:
        raise ValueError(f"Unknown source: {source!r}. Allowed: {list(SOURCE_FILES)}")

    if source in _cache:
        return _cache[source]

    path = data_dir / SOURCE_FILES[source]
    if not path.exists():
        raise FileNotFoundError(f"Local data file not found: {path}")

    logger.info("Loading local data: %s", path.name)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _cache[source] = data
    return data


def clear_cache() -> None:
    _cache.clear()


# ── Public interface ──────────────────────────────────────────────────────────


class LocalDataLoader:
    def __init__(self, settings: Settings) -> None:
        self._dir = settings.local_data_path

    def _get(self, source: str) -> list[dict]:
        return _load(source, self._dir)

    # ── Dashboard summary ─────────────────────────────────────────────────────

    def get_dashboard_summary(self) -> dict[str, Any]:
        incidents = self._get("police_incidents")

        by_station: dict[str, int] = {}
        by_crime: dict[str, int] = {}
        by_status: dict[str, int] = {}
        timeline: dict[str, int] = {}

        for inc in incidents:
            # station
            s = inc.get("station_id", "UNKNOWN")
            by_station[s] = by_station.get(s, 0) + 1
            # crime type
            c = inc.get("crime_type", "UNKNOWN")
            by_crime[c] = by_crime.get(c, 0) + 1
            # status
            st = inc.get("status", "UNKNOWN")
            by_status[st] = by_status.get(st, 0) + 1
            # timeline by month
            ts = inc.get("reported_at", "")
            if ts and len(ts) >= 7:
                month = ts[:7]  # "YYYY-MM"
                timeline[month] = timeline.get(month, 0) + 1

        by_source = []
        for src in SOURCE_FILES:
            recs = self._get(src)
            by_source.append({"source": src, "count": len(recs)})

        return {
            "total_incidents": len(incidents),
            "by_station": [{"station_id": k, "count": v} for k, v in sorted(by_station.items())],
            "by_crime_type": [{"crime_type": k, "count": v} for k, v in sorted(by_crime.items(), key=lambda x: -x[1])],
            "by_status": [{"status": k, "count": v} for k, v in sorted(by_status.items())],
            "by_source": by_source,
            "incident_timeline": [{"period": k, "count": v} for k, v in sorted(timeline.items())],
            "data_mode": "local_fallback",
        }

    # ── Incidents ─────────────────────────────────────────────────────────────

    def get_incidents(
        self,
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
        allowed_sort_fields = {
            "reported_at", "occurred_from", "crime_type",
            "station_id", "status", "estimated_loss",
        }
        if sort_by not in allowed_sort_fields:
            sort_by = "reported_at"

        records = list(self._get("police_incidents"))

        # filter
        if station:
            records = [r for r in records if r.get("station_id") == station.upper()]
        if crime_type:
            records = [r for r in records if r.get("crime_type") == crime_type.upper()]
        if status:
            records = [r for r in records if r.get("status") == status.upper()]
        if date_from:
            records = [r for r in records if (r.get("reported_at") or "") >= date_from]
        if date_to:
            records = [r for r in records if (r.get("reported_at") or "") <= date_to]
        if search:
            q = search.lower()
            records = [
                r for r in records
                if q in (r.get("location_description") or "").lower()
                or q in (r.get("method_description") or "").lower()
                or q in (r.get("incident_id") or "").lower()
                or q in (r.get("crime_type") or "").lower()
            ]

        # sort
        records.sort(key=lambda r: r.get(sort_by) or "", reverse=sort_desc)

        total = len(records)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        page_records = records[start:end]

        return {
            "items": page_records,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "data_mode": "local_fallback",
        }

    def get_incident_by_id(self, incident_id: str) -> Optional[dict]:
        for r in self._get("police_incidents"):
            if r.get("incident_id") == incident_id:
                return r
        return None

    # ── Source exploration ────────────────────────────────────────────────────

    def get_sources_info(self) -> list[dict]:
        result = []
        for src, filename in SOURCE_FILES.items():
            recs = self._get(src)
            result.append({
                "name": src,
                "label": SOURCE_LABELS[src],
                "record_count": len(recs),
                "primary_key_field": SOURCE_PRIMARY_KEYS[src],
                "description": SOURCE_DESCRIPTIONS[src],
            })
        return result

    def get_source_records(
        self,
        source: str,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
    ) -> dict[str, Any]:
        if source not in SOURCE_FILES:
            raise ValueError(f"Unknown source: {source!r}")

        records = list(self._get(source))
        pk = SOURCE_PRIMARY_KEYS[source]

        if search:
            q = search.lower()
            records = [
                r for r in records
                if any(q in str(v).lower() for v in r.values() if v)
            ]

        total = len(records)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        page_records = records[start:end]

        return {
            "source": source,
            "items": page_records,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "data_mode": "local_fallback",
        }

    def get_source_record_by_id(self, source: str, record_id: str) -> Optional[dict]:
        if source not in SOURCE_FILES:
            raise ValueError(f"Unknown source: {source!r}")
        pk = SOURCE_PRIMARY_KEYS[source]
        for r in self._get(source):
            if r.get(pk) == record_id:
                return r
        return None

    # ── Cross-source evidence ─────────────────────────────────────────────────

    def get_incident_evidence(self, incident_id: str) -> dict[str, Any]:
        incident = self.get_incident_by_id(incident_id)
        direct_links: list[dict] = []
        inferred_links: list[dict] = []

        # Collect direct references from police record
        source_ref_ids: set[str] = set(incident.get("source_reference_ids", [])) if incident else set()

        # Search all non-incident sources for direct links
        sources_to_search = {
            "newspaper_reports":  ("news_id",           "related_incident_ids"),
            "witness_reports":    ("witness_report_id",  "related_incident_ids"),
            "cctv_reports":       ("cctv_report_id",     "related_incident_ids"),
            "forensic_reports":   ("evidence_report_id", "incident_id"),
        }

        for src, (pk_field, link_field) in sources_to_search.items():
            for record in self._get(src):
                record_id = record.get(pk_field, "")
                link_val = record.get(link_field)

                is_direct = False
                # Check if it's directly referenced
                if isinstance(link_val, list) and incident_id in link_val:
                    is_direct = True
                elif isinstance(link_val, str) and link_val == incident_id:
                    is_direct = True
                elif record_id in source_ref_ids:
                    is_direct = True

                if is_direct:
                    direct_links.append({
                        "source": src,
                        "record_id": record_id,
                        "link_type": "direct_reference",
                        "link_basis": "Explicit ID reference in source or incident record",
                        "record": record,
                    })
                    continue

                # Inferred: same location_id and overlapping time window
                if incident and record.get("location_id") == incident.get("location_id"):
                    inc_from = incident.get("occurred_from") or incident.get("reported_at") or ""
                    inc_to = incident.get("occurred_to") or inc_from

                    rec_from = (
                        record.get("recorded_from")
                        or record.get("submitted_at")
                        or record.get("published_at")
                        or record.get("collected_at")
                        or ""
                    )
                    rec_to = (
                        record.get("recorded_to")
                        or record.get("observed_to")
                        or rec_from
                    )

                    if rec_from and inc_from and rec_from[:10] == inc_from[:10]:
                        inferred_links.append({
                            "source": src,
                            "record_id": record_id,
                            "link_type": "inferred_spatial_temporal",
                            "link_basis": (
                                "Same location_id and overlapping date. "
                                "This is an investigative lead — NOT a confirmed relationship."
                            ),
                            "record": record,
                        })

        return {
            "incident_id": incident_id,
            "incident": incident,
            "direct_links": direct_links,
            "inferred_links": inferred_links,
            "data_mode": "local_fallback",
            "caveat": (
                "Direct links are based on explicit ID references in source records. "
                "Inferred links are based on matching location and date — they are investigative leads only, "
                "not confirmed evidence relationships."
            ),
        }
