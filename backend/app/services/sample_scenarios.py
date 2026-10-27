"""
Sample Mode Scenarios & Execution
=================================
Provides deterministic, isolated sample scenarios for offline exploration,
testing, and demonstrations.

Requirements:
- Clearly labelled as sample data (data_mode='sample_mode', is_sample=True).
- Never claims Zetaris, Nightshift, or Meterless Engine ran if they did not.
- Isolated from live integration path.
- Includes 3 distinct cross-station scenarios.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

SAMPLE_SCENARIOS = {
    "crowbar_safe_cracking": {
        "scenario_id": "crowbar_safe_cracking",
        "title": "Commercial Crowbar Safe Cracking Syndicate",
        "query": "Investigate safe burglaries in North industrial park and Central downtown involving crowbar prying",
        "target_stations": ["NORTH", "CENTRAL"],
        "crime_type": "BURGLARY",
        "candidate_incidents": [
            {
                "incident_id": "INC-NORTH-0042",
                "station_id": "NORTH",
                "reported_at": "2025-03-12T04:15:00Z",
                "crime_type": "BURGLARY",
                "location_id": "LOC-NORTH-01",
                "location_description": "Apex Logistics Hub, Warehouse Bay 4",
                "method_description": "Forced entry through rear loading door. Safe door peeled using 36mm heavy chisel-tip pry tool. Alarm wires bypassed.",
                "property_involved": ["Commercial Safe", "USD Cash", "Logistics Scanner"],
                "estimated_loss": 34500.0,
                "status": "OPEN",
                "source_reference_ids": ["FOR-0089", "CCTV-0112"],
                "data_quality": "HIGH",
            },
            {
                "incident_id": "INC-CENTRAL-0118",
                "station_id": "CENTRAL",
                "reported_at": "2025-03-18T03:40:00Z",
                "crime_type": "BURGLARY",
                "location_id": "LOC-CEN-04",
                "location_description": "Grand Plaza Diamond Exchange, Suite 210",
                "method_description": "Second-floor balcony access via portable ladder. Reinforced safe door pried using wide chisel tool with distinctive 36mm striations.",
                "property_involved": ["Commercial Vault Box", "Estate Jewelry"],
                "estimated_loss": 89000.0,
                "status": "UNDER_INVESTIGATION",
                "source_reference_ids": ["FOR-0142", "WIT-0105"],
                "data_quality": "HIGH",
            },
        ],
        "supporting_evidence": {
            "forensic_reports": [
                {
                    "evidence_report_id": "FOR-0089",
                    "incident_id": "INC-NORTH-0042",
                    "evidence_item_id": "EVD-2025-0089",
                    "location_id": "LOC-NORTH-01",
                    "evidence_type": "TOOLMARK",
                    "description": "Toolmark impressions on heavy safe door lock box",
                    "result_summary": "Comparison microscopy revealed distinctive 36mm curved chisel-tip striations with microscopic nick on left edge.",
                    "result_status": "MATCH_CONFIRMED",
                    "confidence_level": "HIGH",
                    "compared_evidence_ids": ["EVD-2025-0142"],
                },
                {
                    "evidence_report_id": "FOR-0142",
                    "incident_id": "INC-CENTRAL-0118",
                    "evidence_item_id": "EVD-2025-0142",
                    "location_id": "LOC-CEN-04",
                    "evidence_type": "TOOLMARK",
                    "description": "Tool impressions on pried vault locking pins",
                    "result_summary": "Toolmark striations correspond exactly with 36mm chisel tool observed in EVD-2025-0089.",
                    "result_status": "MATCH_CONFIRMED",
                    "confidence_level": "HIGH",
                    "compared_evidence_ids": ["EVD-2025-0089"],
                },
            ],
            "cctv_reports": [
                {
                    "cctv_report_id": "CCTV-0112",
                    "location_id": "LOC-NORTH-01",
                    "recorded_from": "2025-03-12T03:52:00Z",
                    "vehicle_description": "Dark grey Dodge Grand Caravan minivan with dented rear tailgate",
                    "partial_plate": "7XK***",
                    "movement_description": "Vehicle entered alley without headlights, waited 18 minutes, fled north at high speed.",
                    "related_incident_ids": ["INC-NORTH-0042"],
                    "observation_confidence": 0.88,
                }
            ],
            "witness_reports": [
                {
                    "witness_report_id": "WIT-0105",
                    "location_id": "LOC-CEN-04",
                    "submitted_at": "2025-03-18T04:10:00Z",
                    "observation_text": "Witness observed two individuals loading heavy duffle bags into a dark red four-door sedan parked on side street.",
                    "vehicle_description": "dark red four-door sedan",
                    "contradiction_flags": ["vehicle_model_discrepancy"],
                    "confidence_level": "MEDIUM",
                    "related_incident_ids": ["INC-CENTRAL-0118"],
                }
            ],
            "newspaper_reports": [
                {
                    "news_id": "NEWS-0064",
                    "headline": "Safe-Crackers Strike Downtown Commercial District",
                    "publication_name": "Metro Daily Gazette",
                    "published_at": "2025-03-19T08:00:00Z",
                    "article_text": "Police are investigating similarities between yesterday's diamond exchange break-in and an unsolved burglary in the northern logistics corridor last week.",
                    "related_incident_ids": ["INC-CENTRAL-0118", "INC-NORTH-0042"],
                }
            ],
        },
        "candidate_links": [
            {
                "link_id": "LINK-SAMPLE-01",
                "source_incident_id": "INC-NORTH-0042",
                "target_incident_id": "INC-CENTRAL-0118",
                "stations_involved": ["NORTH", "CENTRAL"],
                "similarity_basis": "Identical 36mm chisel-tip safe door prying toolmarks (FOR-0089 and FOR-0142 confirmed match).",
                "confidence_score": 0.86,
                "confidence_rationale": "High physical evidence correlation via laboratory comparison microscopy across precincts, supported by temporal proximity.",
                "supporting_evidence_ids": ["FOR-0089", "FOR-0142", "CCTV-0112", "NEWS-0064"],
                "contradictions": [
                    {
                        "source_id": "WIT-0105",
                        "description": "Eyewitness reported a dark red sedan fleeing Central incident, contradicting CCTV-0112 recording a dark grey minivan with dented tailgate at North scene.",
                        "flag": "vehicle_model_discrepancy",
                    }
                ],
            }
        ],
        "contradictions_and_limitations": [
            "Eyewitness in Central (WIT-0105) reported a dark red sedan, whereas CCTV in North (CCTV-0112) recorded a dark grey minivan (7XK***). This may indicate two separate vehicles, a vehicle change, or an erroneous witness observation.",
            "CCTV-0112 has partial plate 7XK*** only; full plate registration is unverified.",
            "No DNA or fingerprint evidence was recovered at either scene; link is grounded in toolmark comparison microscopy.",
        ],
        "unresolved_questions": [
            "Query DMV registry for dark grey minivans matching partial plate 7XK*** in county records.",
            "Inspect traffic camera feeds along the North-Central expressway corridor between 03:00 and 05:00 on March 18.",
            "Cross-reference recent tool purchases or pawn shop logs for 36mm heavy cold-steel chisels.",
        ],
        "follow_up_actions": [
            "Coordinate joint interview of witness WIT-0105 with photo lineup of candidate vehicles.",
            "Issue multi-agency alert to Central and North patrol units for grey minivan partial plate 7XK***.",
            "Submit toolmark striations to regional forensic ballistics and toolmark database.",
        ],
    },
    "catalytic_converter": {
        "scenario_id": "catalytic_converter",
        "title": "Commuter Rail Catalytic Converter Syndicate",
        "query": "Identify links between catalytic converter thefts at Central rail parking and Riverside docks commuter lots",
        "target_stations": ["CENTRAL", "RIVERSIDE"],
        "crime_type": "VEHICLE_THEFT",
        "candidate_incidents": [
            {
                "incident_id": "INC-CENTRAL-0455",
                "station_id": "CENTRAL",
                "reported_at": "2025-04-02T19:30:00Z",
                "crime_type": "VEHICLE_THEFT",
                "location_id": "LOC-CEN-08",
                "location_description": "Central Station South Commuter Lot",
                "method_description": "Rapid undercarriage cut of Toyota Prius exhaust manifold using reciprocating saw. Total duration under 90 seconds.",
                "property_involved": ["Catalytic Converter", "Exhaust Manifold Assembly"],
                "estimated_loss": 2800.0,
                "status": "OPEN",
                "source_reference_ids": ["FOR-0322", "CCTV-0410"],
                "data_quality": "HIGH",
            },
            {
                "incident_id": "INC-RIVERSIDE-0812",
                "station_id": "RIVERSIDE",
                "reported_at": "2025-04-05T18:45:00Z",
                "crime_type": "VEHICLE_THEFT",
                "location_id": "LOC-RIV-03",
                "location_description": "Riverside Ferry Terminal Long-Term Lot",
                "method_description": "Multiple catalytic converters severed using specialized carbide-tipped reciprocating saw. Cut angle matches Central series.",
                "property_involved": ["Catalytic Converter x3"],
                "estimated_loss": 7500.0,
                "status": "UNDER_INVESTIGATION",
                "source_reference_ids": ["FOR-0589", "WIT-0388"],
                "data_quality": "HIGH",
            },
        ],
        "supporting_evidence": {
            "forensic_reports": [
                {
                    "evidence_report_id": "FOR-0322",
                    "incident_id": "INC-CENTRAL-0455",
                    "evidence_item_id": "EVD-2025-0322",
                    "evidence_type": "CHEMICAL_RESIDUE",
                    "result_summary": "GC-MS analysis of kerf cut shavings revealed titanium carbonitride blade coating residue matching Diablo Steel Demon series.",
                    "result_status": "MATCH_CONFIRMED",
                    "compared_evidence_ids": ["EVD-2025-0589"],
                },
                {
                    "evidence_report_id": "FOR-0589",
                    "incident_id": "INC-RIVERSIDE-0812",
                    "evidence_item_id": "EVD-2025-0589",
                    "evidence_type": "CHEMICAL_RESIDUE",
                    "result_summary": "Identical titanium carbonitride metallurgical fingerprint identified on severed exhaust piping.",
                    "result_status": "MATCH_CONFIRMED",
                    "compared_evidence_ids": ["EVD-2025-0322"],
                },
            ],
            "cctv_reports": [
                {
                    "cctv_report_id": "CCTV-0410",
                    "location_id": "LOC-CEN-08",
                    "recorded_from": "2025-04-02T19:15:00Z",
                    "vehicle_description": "Silver Honda Civic hatchback with missing front hubcap",
                    "movement_description": "Passenger slid on wheeled mechanics creeper beneath parked hybrid vehicles.",
                    "observation_confidence": 0.92,
                }
            ],
            "witness_reports": [
                {
                    "witness_report_id": "WIT-0388",
                    "location_id": "LOC-RIV-03",
                    "submitted_at": "2025-04-05T19:05:00Z",
                    "observation_text": "Witness heard loud grinding saw noise, saw two men throw metal cylinders into silver hatchback.",
                    "vehicle_description": "silver compact hatchback",
                    "contradiction_flags": [],
                    "confidence_level": "HIGH",
                }
            ],
            "newspaper_reports": [],
        },
        "candidate_links": [
            {
                "link_id": "LINK-SAMPLE-02",
                "source_incident_id": "INC-CENTRAL-0455",
                "target_incident_id": "INC-RIVERSIDE-0812",
                "stations_involved": ["CENTRAL", "RIVERSIDE"],
                "similarity_basis": "Chemical residue and blade metallurgy (titanium carbonitride) identical across cut surfaces; vehicle description (silver hatchback) consistent across scenes.",
                "confidence_score": 0.89,
                "confidence_rationale": "High metallurgical precision via GC-MS corroborating consistent MO and surveillance video.",
                "supporting_evidence_ids": ["FOR-0322", "FOR-0589", "CCTV-0410", "WIT-0388"],
                "contradictions": [],
            }
        ],
        "contradictions_and_limitations": [
            "Blade metallurgy proves identical coating type, which is commercially distributed; not unique to a single specific blade.",
            "License plate not captured due to headlight glare in CCTV-0410.",
        ],
        "unresolved_questions": [
            "Check local scrap metal recyclers in Riverside and Central county for bulk converter intakes in April 2025.",
            "Review automated license plate reader (ALPR) hits for silver Honda Civics with front hubcap missing near commuter corridors.",
        ],
        "follow_up_actions": [
            "Conduct inter-precinct surveillance on commuter rail park-and-ride lots during weekday evening peak hours.",
            "Inspect recent purchases of Diablo Titanium Carbonitride blades at regional hardware outlets.",
        ],
    },
    "keyless_suv_relay": {
        "scenario_id": "keyless_suv_relay",
        "title": "Keyless Luxury SUV Relay Attack Ring",
        "query": "Investigate keyless vehicle thefts of high-end SUVs in North residential estates and Riverside marina",
        "target_stations": ["NORTH", "RIVERSIDE"],
        "crime_type": "VEHICLE_THEFT",
        "candidate_incidents": [
            {
                "incident_id": "INC-NORTH-0610",
                "station_id": "NORTH",
                "reported_at": "2025-05-10T02:30:00Z",
                "crime_type": "VEHICLE_THEFT",
                "location_id": "LOC-NORTH-14",
                "location_description": "Pinecrest Executive Estates, Residence Driveway",
                "method_description": "Keyless relay attack. Two suspects: one waved antenna loop near front door, second opened Lexus LX600 door and pushed start button without physical damage.",
                "property_involved": ["2024 Lexus LX600 SUV", "Golf Clubs"],
                "estimated_loss": 125000.0,
                "status": "OPEN",
                "source_reference_ids": ["FOR-0740", "CCTV-0899"],
                "data_quality": "HIGH",
            },
            {
                "incident_id": "INC-RIVERSIDE-1120",
                "station_id": "RIVERSIDE",
                "reported_at": "2025-05-16T03:15:00Z",
                "crime_type": "VEHICLE_THEFT",
                "location_id": "LOC-RIV-11",
                "location_description": "Bayside Yacht Club Gated Lot",
                "method_description": "Keyless entry relay attack targeting parked Range Rover. Digital telematics log showed CAN-bus injection spoofing smart key fob.",
                "property_involved": ["2024 Range Rover Autobiography"],
                "estimated_loss": 160000.0,
                "status": "UNDER_INVESTIGATION",
                "source_reference_ids": ["FOR-0911"],
                "data_quality": "HIGH",
            },
        ],
        "supporting_evidence": {
            "forensic_reports": [
                {
                    "evidence_report_id": "FOR-0740",
                    "incident_id": "INC-NORTH-0610",
                    "evidence_item_id": "EVD-2025-0740",
                    "evidence_type": "DIGITAL_FOOTPRINT",
                    "result_summary": "Extracted telematics ECU log recorded 315MHz/433MHz dual-frequency amplifier handshake spoof with 14ms latency signature.",
                    "result_status": "MATCH_CONFIRMED",
                    "compared_evidence_ids": ["EVD-2025-0911"],
                },
                {
                    "evidence_report_id": "FOR-0911",
                    "incident_id": "INC-RIVERSIDE-1120",
                    "evidence_item_id": "EVD-2025-0911",
                    "evidence_type": "DIGITAL_FOOTPRINT",
                    "result_summary": "CAN-bus gateway log recorded identical 14ms amplification latency and transceiver signature.",
                    "result_status": "MATCH_CONFIRMED",
                    "compared_evidence_ids": ["EVD-2025-0740"],
                },
            ],
            "cctv_reports": [
                {
                    "cctv_report_id": "CCTV-0899",
                    "location_id": "LOC-NORTH-14",
                    "recorded_from": "2025-05-10T02:22:00Z",
                    "movement_description": "Suspect carrying oversized backpack with flexible copper loop antenna approach front porch, signaling second suspect by vehicle.",
                    "observation_confidence": 0.95,
                }
            ],
            "witness_reports": [],
            "newspaper_reports": [],
        },
        "candidate_links": [
            {
                "link_id": "LINK-SAMPLE-03",
                "source_incident_id": "INC-NORTH-0610",
                "target_incident_id": "INC-RIVERSIDE-1120",
                "stations_involved": ["NORTH", "RIVERSIDE"],
                "similarity_basis": "Identical RF digital relay signature (14ms response delay) and dual-frequency 315/433MHz amplifier footprint on onboard ECU logs.",
                "confidence_score": 0.91,
                "confidence_rationale": "High digital forensic match between distinct vehicle manufacturers utilizing identical proprietary attack device.",
                "supporting_evidence_ids": ["FOR-0740", "FOR-0911", "CCTV-0899"],
                "contradictions": [],
            }
        ],
        "contradictions_and_limitations": [
            "Attack methodology utilizes specialized black-box relay hardware that may be cloned or sold online to multiple crews.",
            "Vehicles have not been recovered; suspected containerized for export at marine freight terminal.",
        ],
        "unresolved_questions": [
            "Check shipping container manifests at Riverside Port intermodal yards for containers destined for overseas auto resale.",
            "Inspect cellular tower dump data for transient IMEI numbers present at both locations during the early morning hours.",
        ],
        "follow_up_actions": [
            "Request customs hold and X-ray scanning on all containerized vehicle exports leaving Riverside docks.",
            "Issue intelligence advisory to luxury vehicle dealerships regarding antenna loop relay countermeasures.",
        ],
    },
}


def get_sample_investigation(scenario_id: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve one of the 3 sample scenarios, formatted as a complete investigation result.
    Always clearly marked as sample data.
    """
    if not scenario_id and query:
        q_lower = query.lower()
        if "catalytic" in q_lower or "saw" in q_lower or "converter" in q_lower:
            scenario_id = "catalytic_converter"
        elif "relay" in q_lower or "keyless" in q_lower or "suv" in q_lower:
            scenario_id = "keyless_suv_relay"
        else:
            scenario_id = "crowbar_safe_cracking"
    elif not scenario_id:
        scenario_id = "crowbar_safe_cracking"

    scenario = SAMPLE_SCENARIOS.get(scenario_id, SAMPLE_SCENARIOS["crowbar_safe_cracking"])

    run_id = f"sample-{scenario_id}"
    return {
        "investigation_id": run_id,
        "is_sample": True,
        "data_mode": "sample_mode",
        "scenario_id": scenario["scenario_id"],
        "title": scenario["title"],
        "query": scenario["query"],
        "stations_involved": scenario["target_stations"],
        "candidate_incidents": scenario["candidate_incidents"],
        "supporting_evidence": scenario["supporting_evidence"],
        "candidate_links": scenario["candidate_links"],
        "contradictions_and_limitations": scenario["contradictions_and_limitations"],
        "unresolved_questions": scenario["unresolved_questions"],
        "follow_up_actions": scenario["follow_up_actions"],
        "executive_summary": (
            f"SAMPLE INVESTIGATION REPORT: {scenario['title']}. Identified potential multi-station links "
            f"spanning {', '.join(scenario['target_stations'])} with supporting forensic and surveillance evidence. "
            f"All findings represent synthetic investigative leads requiring independent operational verification."
        ),
        "integration_status": {
            "zetaris": {"status": "simulated", "mode": "sample_mode", "note": "Sample mode active; live Zetaris was not queried"},
            "nightshift_nemotron": {"status": "simulated", "mode": "sample_mode", "model": "sample/nemotron-simulated"},
            "meterless_engine": {"status": "simulated", "mode": "sample_mode", "feature": "world_model_simulated"},
        },
        "retrieval_and_analysis_status": "completed_sample",
        "trace_file": None,
        "timestamp": time.time(),
    }
