"""
Deterministic Evidence Verifier
===============================
Pure-Python checks that run beside model reasoning. Wherever the retrieved
Zetaris records allow a direct check, this module decides - not an LLM.

Per proposed link it returns a ``ClaimValidation`` with structured checks:
  ids_exist          cited incident / evidence IDs are in the retrieved set
  id_source_types    ID prefix matches the record's source table
  evidence_linked    cited evidence is tied to the link's incidents (by
                     incident reference or shared location)
  quotes             quoted text appears verbatim in the cited record
  attributes         claimed shared attributes appear in the cited records,
                     and in records tied to BOTH incidents
  station_consistency / timeline  stations and times are compatible
  independence       duplicate or derivative reports are not counted twice
  contradictions     contradictory observations stay visible

Link status: SUPPORTED (>=2 independent corroborating sources, no failed
check), WEAK (passes, fewer than 2), UNSUPPORTED (a hard check failed).
Contradictions never change a status silently - they are reported alongside.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

PREFIX_TYPES = (
    ("INC-", "police_incident"),
    ("CCTV-", "cctv"),
    ("WIT-", "witness"),
    ("FOR-", "forensic"),
    ("EVD-", "forensic"),
    ("NEWS-", "newspaper"),
)
NON_PROBATIVE_FORENSIC = {"INCONCLUSIVE", "PENDING_REFERENCE"}
COLORS = ("white", "black", "green", "silver", "grey", "gray", "red", "blue", "yellow", "brown", "orange", "tan", "beige", "gold")
DISTANT_DAYS = 90


def source_type_of(record_id: str) -> Optional[str]:
    for prefix, kind in PREFIX_TYPES:
        if str(record_id).startswith(prefix):
            return kind
    return None


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _as_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else ([] if v in (None, "") else [v])


def _flatten_text(rec: Dict[str, Any], skip: Iterable[str] = ()) -> str:
    parts: List[str] = []
    for k, v in rec.items():
        if k in skip or v is None:
            continue
        if isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
        elif isinstance(v, (str, int, float)):
            parts.append(str(v))
    return _norm(" ".join(parts))


@dataclass
class Check:
    check: str
    status: str            # pass | fail | warn | indeterminate
    explanation: str


@dataclass
class ClaimValidation:
    claim_id: str
    source_ids: List[str]
    status: str            # SUPPORTED | WEAK | UNSUPPORTED
    explanation: str
    checks: List[Check] = field(default_factory=list)
    independent_source_count: int = 0
    corroborating_ids: List[str] = field(default_factory=list)
    duplicate_groups: List[List[str]] = field(default_factory=list)
    contextual_ids: List[str] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    verified_evidence_ids: List[str] = field(default_factory=list)
    rejected_ids: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceIndex:
    """Every retrieved Zetaris record, addressable by every ID it carries."""

    def __init__(self) -> None:
        self.by_id: Dict[str, Dict[str, Any]] = {}
        self.incidents: Dict[str, Dict[str, Any]] = {}

    def add_incidents(self, rows: Iterable[Dict[str, Any]]) -> None:
        for r in rows:
            if r.get("incident_id"):
                self.incidents[r["incident_id"]] = r
                self.by_id[r["incident_id"]] = {"type": "police_incident", "rec": r, "primary": r["incident_id"]}

    def add_evidence(self, evidence: Dict[str, List[Dict[str, Any]]]) -> None:
        for r in evidence.get("forensic_reports", []):
            for key in ("evidence_report_id", "evidence_item_id"):
                if r.get(key):
                    self.by_id[r[key]] = {"type": "forensic", "rec": r, "primary": r.get("evidence_report_id") or r[key]}
        for key, idf, typ in (("cctv_reports", "cctv_report_id", "cctv"),
                              ("witness_reports", "witness_report_id", "witness"),
                              ("newspaper_reports", "news_id", "newspaper")):
            for r in evidence.get(key, []):
                if r.get(idf):
                    self.by_id[r[idf]] = {"type": typ, "rec": r, "primary": r[idf]}

    def has(self, rid: str) -> bool:
        return rid in self.by_id

    def get(self, rid: str) -> Optional[Dict[str, Any]]:
        return self.by_id.get(rid)

    def text_of(self, rid: str) -> str:
        e = self.by_id.get(rid)
        return _flatten_text(e["rec"]) if e else ""

    def evidence_ids(self) -> Set[str]:
        return {i for i, e in self.by_id.items() if e["type"] != "police_incident"}

    def incident_ids(self) -> Set[str]:
        return set(self.incidents)

    def incidents_of_evidence(self, rid: str) -> Set[str]:
        e = self.by_id.get(rid)
        if not e or e["type"] == "police_incident":
            return {rid} if e else set()
        r = e["rec"]
        ids = set(_as_list(r.get("related_incident_ids")))
        if r.get("incident_id"):
            ids.add(r["incident_id"])
        return ids

    def is_directly_referenced(self, rid: str, incident_ids: Iterable[str]) -> bool:
        """The record explicitly cites one of the incidents (incident_id / related_incident_ids)."""
        refs = self.incidents_of_evidence(rid)
        return any(i in refs for i in incident_ids)

    def is_linked_to(self, rid: str, incident_ids: Iterable[str]) -> bool:
        """Tied to one of the incidents by explicit reference or shared location."""
        incs = [self.incidents[i] for i in incident_ids if i in self.incidents]
        if any(i in self.incidents_of_evidence(rid) for i in incident_ids):
            return True
        e = self.by_id.get(rid)
        if not e:
            return False
        loc = e["rec"].get("location_id")
        locs = set(_as_list(e["rec"].get("mentioned_location_ids"))) | ({loc} if loc else set())
        return any(i.get("location_id") in locs for i in incs if i.get("location_id"))


def _interval(inc: Dict[str, Any]) -> Optional[Tuple[datetime, datetime]]:
    start = _parse_ts(inc.get("occurred_from"))
    if not start:
        return None
    end = _parse_ts(inc.get("occurred_to")) or start
    return (start, max(start, end))


def _window(rec: Dict[str, Any], a: str, b: str) -> Optional[Tuple[datetime, datetime]]:
    start = _parse_ts(rec.get(a))
    if not start:
        return None
    return (start, max(start, _parse_ts(rec.get(b)) or start))


def _overlap(x: Optional[Tuple[datetime, datetime]], y: Optional[Tuple[datetime, datetime]]) -> bool:
    return bool(x and y and x[0] <= y[1] and y[0] <= x[1])


def cluster_independent(ids: List[str], index: EvidenceIndex, incident_ids: Iterable[str]) -> Tuple[Dict[str, List[str]], List[List[str]]]:
    """
    Group cited evidence by underlying source so repeats are not double counted.
      - newspaper reports about a police incident derive from the police report
      - CCTV from the same camera with overlapping recording windows
      - witness reports at one location with the same observation start, or identical text
      - forensic reports on the same evidence item
    Returns (cluster_key -> member ids, groups with more than one member).
    """
    clusters: Dict[str, List[str]] = {}
    incident_ids = set(incident_ids)
    seen_cctv: List[Tuple[str, Tuple[datetime, datetime], str]] = []
    seen_wit: Dict[Tuple[Any, Any], str] = {}
    seen_text: Dict[str, str] = {}

    def put(key: str, rid: str) -> None:
        clusters.setdefault(key, []).append(rid)

    for rid in ids:
        e = index.get(rid)
        if not e:
            continue
        r, typ = e["rec"], e["type"]
        if typ == "police_incident":
            put(f"police:{rid}", rid)
        elif typ == "newspaper":
            about = [i for i in _as_list(r.get("related_incident_ids")) if i in incident_ids]
            put(f"police:{about[0]}" if about else f"news:{rid}", rid)
        elif typ == "forensic":
            put(f"forensic:{r.get('evidence_item_id') or rid}", rid)
        elif typ == "cctv":
            win = _window(r, "recorded_from", "recorded_to")
            key = None
            for cam, w, k in seen_cctv:
                if cam == r.get("camera_id") and _overlap(win, w):
                    key = k
                    break
            key = key or f"cctv:{rid}"
            if win:
                seen_cctv.append((r.get("camera_id"), win, key))
            put(key, rid)
        elif typ == "witness":
            tkey = _norm(r.get("observation_text"))
            wkey = (r.get("location_id"), r.get("observed_from"))
            key = seen_wit.get(wkey) if r.get("observed_from") else None
            key = key or (seen_text.get(tkey) if tkey else None) or f"witness:{rid}"
            if r.get("observed_from"):
                seen_wit[wkey] = key
            if tkey:
                seen_text[tkey] = key
            put(key, rid)
    dupes = [m for m in clusters.values() if len(m) > 1]
    return clusters, dupes


def _colors_in(text: str) -> Set[str]:
    return {("grey" if c == "gray" else c) for c in COLORS if re.search(rf"\b{c}\b", text)}


def detect_contradictions(ids: List[str], index: EvidenceIndex) -> List[Dict[str, Any]]:
    """Contradictory observations among cited records, from source fields only."""
    out: List[Dict[str, Any]] = []
    cctv_colors: Dict[str, str] = {}
    wit_colors: Dict[str, Set[str]] = {}
    for rid in ids:
        e = index.get(rid)
        if not e:
            continue
        r, typ = e["rec"], e["type"]
        if typ == "witness":
            for flag in _as_list(r.get("contradiction_flags")):
                out.append({"type": "source_flag", "source_ids": [rid], "flag": flag,
                            "description": f"{rid} carries source contradiction flag '{flag}'."})
            cols = _colors_in(_norm(r.get("vehicle_description")))
            if cols:
                wit_colors[rid] = cols
        elif typ == "cctv" and r.get("vehicle_color"):
            cctv_colors[rid] = _norm(r["vehicle_color"]).replace("gray", "grey")
        elif typ == "forensic" and r.get("result_status") == "EXCLUSION":
            out.append({"type": "forensic_exclusion", "source_ids": [rid], "flag": "EXCLUSION",
                        "description": f"{rid} reports an EXCLUSION result for evidence item {r.get('evidence_item_id')}."})
    for cid, col in cctv_colors.items():
        for wid, cols in wit_colors.items():
            if col not in cols:
                out.append({"type": "vehicle_color_conflict", "source_ids": [cid, wid], "flag": "vehicle_color_conflict",
                            "description": f"CCTV {cid} records a {col} vehicle; witness {wid} describes {'/'.join(sorted(cols))}."})
    return out


def verify_link(link: Dict[str, Any], index: EvidenceIndex) -> ClaimValidation:
    """Verify one Finder link dict against retrieved records."""
    claim_id = str(link.get("link_id") or "LINK-?")
    src, tgt = link.get("source_incident_id"), link.get("target_incident_id")
    cited = [str(i) for i in _as_list(link.get("supporting_evidence_ids"))]
    checks: List[Check] = []
    incident_pair = [i for i in (src, tgt) if i]
    all_ids = [*incident_pair, *cited]

    # 1 ── IDs exist & have the expected source type
    missing = [i for i in all_ids if not index.has(i)]
    bad_type = [i for i in all_ids if index.has(i) and (source_type_of(i) != index.get(i)["type"])]
    unknown_prefix = [i for i in all_ids if source_type_of(i) is None]
    rejected = sorted(set(missing) | set(bad_type) | set(unknown_prefix))
    inc_missing = [i for i in incident_pair if not index.has(i) or index.get(i)["type"] != "police_incident"]
    if src == tgt or len(incident_pair) < 2:
        checks.append(Check("ids_exist", "fail", "A link needs two distinct incident IDs."))
    elif inc_missing:
        checks.append(Check("ids_exist", "fail", f"Incident ID(s) not in retrieved Zetaris records: {inc_missing}"))
    elif missing:
        checks.append(Check("ids_exist", "warn", f"Evidence ID(s) not in retrieved records (dropped): {missing}"))
    else:
        checks.append(Check("ids_exist", "pass", "All cited IDs exist in retrieved records."))
    if bad_type or unknown_prefix:
        checks.append(Check("id_source_types", "warn", f"ID prefix does not match record source type: {sorted(set(bad_type) | set(unknown_prefix))}"))
    else:
        checks.append(Check("id_source_types", "pass", "ID prefixes match source tables."))

    valid_evidence = [i for i in cited if index.has(i) and i not in rejected and index.get(i)["type"] != "police_incident"]
    hard_fail = any(c.status == "fail" for c in checks)

    # 2 ── Evidence actually tied to this link's incidents. Only records that explicitly cite one of
    #      the incidents corroborate; same-location records are context and are not counted.
    linked = [i for i in valid_evidence if index.is_directly_referenced(i, incident_pair)]
    contextual = [i for i in valid_evidence if i not in linked and index.is_linked_to(i, incident_pair)]
    unlinked = [i for i in valid_evidence if i not in linked and i not in contextual]
    if unlinked:
        checks.append(Check("evidence_linked", "warn",
                            f"Cited evidence not tied to either incident by reference or location (not counted): {unlinked}"))
    if contextual:
        checks.append(Check("evidence_linked", "warn",
                            f"Cited records share a location with an incident but do not cite it; context only, not counted: {contextual}"))
    if not unlinked and not contextual:
        checks.append(Check("evidence_linked", "pass", "Cited evidence explicitly references the link's incidents."))

    # 3 ── Quotations
    quote_fail: List[str] = []
    for q in _as_list(link.get("quotes")):
        if not isinstance(q, dict):
            continue
        sid, qt = q.get("source_id"), _norm(q.get("text"))
        if not qt or not sid or not index.has(sid) or qt not in index.text_of(sid):
            quote_fail.append(str(sid))
    if _as_list(link.get("quotes")):
        checks.append(Check("quotes", "fail" if quote_fail else "pass",
                            f"Quotation not found verbatim in: {quote_fail}" if quote_fail else "All quotations match source text."))

    # 4 ── Shared attributes must appear in cited records, on both sides
    attr_unsupported: List[str] = []
    attr_one_sided: List[str] = []
    for a in _as_list(link.get("shared_attributes")):
        if not isinstance(a, dict) or not a.get("value"):
            continue
        value = _norm(a["value"])
        sids = [s for s in _as_list(a.get("source_ids")) if index.has(s)]
        hits = [s for s in sids if value in index.text_of(s)]
        label = f"{a.get('attribute', 'attribute')}={a['value']}"
        if not hits:
            attr_unsupported.append(label)
            continue
        sides = {i for i in incident_pair if any(i in index.incidents_of_evidence(h) or index.is_linked_to(h, [i]) for h in hits)}
        if len(sides) < 2:
            attr_one_sided.append(label)
    if attr_unsupported:
        checks.append(Check("attributes", "fail", f"Claimed shared attribute(s) absent from cited records: {attr_unsupported}"))
    elif attr_one_sided:
        checks.append(Check("attributes", "warn", f"Attribute(s) evidenced for only one incident, so not shown to be shared: {attr_one_sided}"))
    elif _as_list(link.get("shared_attributes")):
        checks.append(Check("attributes", "pass", "Shared attributes appear in cited records tied to both incidents."))
    else:
        checks.append(Check("attributes", "warn", "No shared attributes stated, so the similarity claim is unsupported by specifics."))

    # 5 ── Stations & timeline
    s_rec, t_rec = index.incidents.get(src or ""), index.incidents.get(tgt or "")
    contradictions: List[Dict[str, Any]] = []
    if s_rec and t_rec:
        actual = {s_rec.get("station_id"), t_rec.get("station_id")}
        claimed = set(_as_list(link.get("stations_involved")))
        if claimed and claimed != actual:
            checks.append(Check("station_consistency", "fail", f"Claimed stations {sorted(claimed)} differ from records {sorted(actual)}."))
        else:
            checks.append(Check("station_consistency", "pass", f"Stations {sorted(actual)} match records."))
        a_iv, b_iv = _interval(s_rec), _interval(t_rec)
        if not a_iv or not b_iv:
            checks.append(Check("timeline", "indeterminate", "One or both incidents lack an occurrence time; timeline compatibility cannot be assessed."))
        elif actual and len(actual) > 1 and _overlap(a_iv, b_iv) and s_rec.get("location_id") != t_rec.get("location_id"):
            msg = "Occurrence windows overlap at different stations/locations; one actor at both is not supported."
            checks.append(Check("timeline", "warn", msg))
            contradictions.append({"type": "incompatible_timeline", "source_ids": [src, tgt], "flag": "incompatible_timeline", "description": msg})
        else:
            gap = abs((b_iv[0] - a_iv[1]).total_seconds()) / 86400 if b_iv[0] >= a_iv[1] else abs((a_iv[0] - b_iv[1]).total_seconds()) / 86400
            note = f" ({gap:.0f} days apart; weak temporal proximity)" if gap > DISTANT_DAYS else ""
            checks.append(Check("timeline", "pass" if gap <= DISTANT_DAYS else "warn", f"Occurrence windows are compatible{note}."))
    else:
        hard_fail = True

    # 6 ── Independence
    probative = []
    for i in linked:
        e = index.get(i)
        if e["type"] == "forensic" and e["rec"].get("result_status") in NON_PROBATIVE_FORENSIC:
            continue
        if e["type"] == "forensic" and e["rec"].get("result_status") == "EXCLUSION":
            continue
        probative.append(i)
    clusters, dupes = cluster_independent(probative, index, incident_pair)
    # A newspaper article about a police-recorded incident derives from that report
    # (cluster "police:<id>"), so it never adds an independent source.
    independent_keys = [k for k in clusters if not k.startswith("police:")]
    independent = len(independent_keys)
    if dupes:
        checks.append(Check("independence", "warn", f"Duplicate/derivative reports collapsed to one source each: {dupes}"))
    checks.append(Check("independence", "pass" if independent >= 2 else "warn",
                        f"{independent} independent corroborating source(s) among {len(probative)} probative linked record(s)."))

    # 7 ── Contradictions (kept visible, never merged away)
    contradictions += detect_contradictions([*incident_pair, *valid_evidence], index)
    if contradictions:
        checks.append(Check("contradictions", "warn", f"{len(contradictions)} contradictory observation(s) retained."))

    fails = [c for c in checks if c.status == "fail"]
    if hard_fail or fails:
        status = "UNSUPPORTED"
        explanation = "; ".join(c.explanation for c in fails) or "Incident records missing."
    elif independent >= 2:
        status, explanation = "SUPPORTED", f"{independent} independent sources; all hard checks pass."
    else:
        status, explanation = "WEAK", f"Passes hard checks but only {independent} independent corroborating source(s)."

    return ClaimValidation(
        claim_id=claim_id,
        source_ids=[*incident_pair, *cited],
        status=status,
        explanation=explanation,
        checks=checks,
        independent_source_count=independent,
        corroborating_ids=probative,
        contextual_ids=contextual,
        duplicate_groups=dupes,
        contradictions=contradictions,
        verified_evidence_ids=linked,
        rejected_ids=rejected,
    )


def verify_cited_ids(ids: Iterable[str], index: EvidenceIndex) -> Dict[str, List[str]]:
    """Split IDs into those present in retrieved records and those that are not."""
    valid, invalid = [], []
    for i in ids:
        (valid if index.has(str(i)) else invalid).append(str(i))
    return {"valid": valid, "invalid": invalid}
