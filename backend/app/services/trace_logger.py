"""
Investigation Structured Trace Logger
=====================================
Records execution events to structured JSONL files: logs/trace-<run_id>.jsonl
Contains safe, non-secret telemetry for auditability and reproducibility:
- Run ID and timestamps
- Agent identity and workflow step
- Safe SQL query descriptions and returned row counts
- Provider and actual reported model metadata
- Meterless World Model operations and statistics
- Evaluator verification decisions and contradictions
- Evidence IDs cited and validated
- Final outcome and errors
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TraceLogger:
    """Manages appending trace events to logs/trace-<run_id>.jsonl."""

    def __init__(self, run_id: str, base_dir: Optional[Path] = None) -> None:
        self.run_id = run_id
        if base_dir:
            self.logs_dir = base_dir
        else:
            # cross_station_crime_intelligence/logs
            self.logs_dir = Path(__file__).resolve().parent.parent.parent.parent / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.logs_dir / f"trace-{self.run_id}.jsonl"

    def log_event(
        self,
        step: str,
        agent: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        provider_meta: Optional[Dict[str, Any]] = None,
        engine_meta: Optional[Dict[str, Any]] = None,
        sql_meta: Optional[Dict[str, Any]] = None,
        status: str = "ok",
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a single structured trace event."""
        event: Dict[str, Any] = {
            "run_id": self.run_id,
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "step": step,
            "agent": agent,
            "action": action,
            "status": status,
        }

        if details:
            event["details"] = details
        if provider_meta:
            event["provider_meta"] = provider_meta
        if engine_meta:
            event["engine_meta"] = engine_meta
        if sql_meta:
            event["sql_meta"] = sql_meta
        if error:
            event["error"] = error

        try:
            line = json.dumps(event) + "\n"
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:
            logger.warning("Failed to write to trace log %s: %s", self.log_file, exc)

        return event

    def get_events(self) -> List[Dict[str, Any]]:
        """Read back all events logged for this run."""
        if not self.log_file.exists():
            return []
        events = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as exc:
            logger.warning("Failed to read trace log %s: %s", self.log_file, exc)
        return events
