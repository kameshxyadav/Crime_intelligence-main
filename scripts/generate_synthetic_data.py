#!/usr/bin/env python3
"""
Synthetic Data Generator for Cross-Station Crime Intelligence
Open Agent Hackathon 2026

Generates exactly 10,000 synthetic records across 5 JSON datasets:
1. data/generated/police_incidents.json   (3,000 records)
2. data/generated/newspaper_reports.json (1,500 records)
3. data/generated/witness_reports.json   (2,000 records)
4. data/generated/cctv_reports.json      (2,000 records)
5. data/generated/forensic_reports.json  (1,500 records)

Also produces offline evaluation ground truth:
data/evaluation/ground_truth.json
"""

import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# Alias for JSON-style literal convenience
null = None

# Configuration
RANDOM_SEED = 42
TARGET_COUNTS = {
    "police_incidents": 3000,
    "newspaper_reports": 1500,
    "witness_reports": 2000,
    "cctv_reports": 2000,
    "forensic_reports": 1500,
}

BASE_START_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
BASE_END_TIME = datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc)

STATIONS = ["NORTH", "CENTRAL", "RIVERSIDE"]

LOCATIONS = {
    "NORTH": [
        ("LOC-NORTH-01", "Northgate Logistics Park, Warehouse 4B"),
        ("LOC-NORTH-02", "Pinnacle Tech Campus, Building B"),
        ("LOC-NORTH-03", "Silver Lake Residential Estate, Maple Drive"),
        ("LOC-NORTH-04", "North Ridge Shopping Plaza, Unit 12"),
        ("LOC-NORTH-05", "Highway 10 Northbound Rest Area"),
        ("LOC-NORTH-06", "Oakridge Industrial Depot, Bay 7"),
        ("LOC-NORTH-07", "Crestview Heights, Hilltop Way"),
        ("LOC-NORTH-08", "Northern Distribution Hub, Freight Terminal"),
        ("LOC-NORTH-09", "Valley View Apartments, Parking Structure"),
        ("LOC-NORTH-10", "Glenwood Strip Mall, Pharmacy Suite"),
        ("LOC-NORTH-11", "North Suburbia Medical Clinic, Lot A"),
        ("LOC-NORTH-12", "Evergreen Elementary School Perimeter"),
        ("LOC-NORTH-13", "Quarry Industrial Access Road"),
        ("LOC-NORTH-14", "Highland Park Community Center"),
        ("LOC-NORTH-15", "Northgate Rail Freight Sidings"),
        ("LOC-NORTH-16", "Birchwood Luxury Condos, Driveway"),
        ("LOC-NORTH-17", "Northstar Self-Storage, Row G"),
        ("LOC-NORTH-18", "Boreal Forest Trailhead Parking"),
        ("LOC-NORTH-19", "Timberline Commercial Center"),
        ("LOC-NORTH-20", "Northside Auto Salvage, Yard 2"),
    ],
    "CENTRAL": [
        ("LOC-CEN-01", "Downtown Financial Plaza, East Tower"),
        ("LOC-CEN-02", "Central City Rail Terminal, North Concourse"),
        ("LOC-CEN-03", "Grand Avenue Luxury Jewellers Arcade"),
        ("LOC-CEN-04", "Civic Center Underground Parking, Level P2"),
        ("LOC-CEN-05", "Metropolitan Arts Quarter, Gallery Row"),
        ("LOC-CEN-06", "Crown Electronics Superstore, Market Street"),
        ("LOC-CEN-07", "St. Jude Hospital Public Car Park"),
        ("LOC-CEN-08", "Midtown Commercial Hub, Suite 300"),
        ("LOC-CEN-09", "Broadway Theater District Alleyway"),
        ("LOC-CEN-10", "Union Bank Vault Facility, Rear Entrance"),
        ("LOC-CEN-11", "Central Public Library Steps"),
        ("LOC-CEN-12", "Market Square Farmers Pavilion"),
        ("LOC-CEN-13", "Old Town Heritage Lane, Antique Mall"),
        ("LOC-CEN-14", "University Science Complex, Lab 3"),
        ("LOC-CEN-15", "City Hall Annex, South Delivery Ramp"),
        ("LOC-CEN-16", "Grand Hotel Valet Station"),
        ("LOC-CEN-17", "Mercantile Exchange Building, Atrium"),
        ("LOC-CEN-18", "Exchange Park Fountain Walk"),
        ("LOC-CEN-19", "Midtown Bus Interchange, Platform 4"),
        ("LOC-CEN-20", "St. Peter Cathedral Courtyard"),
    ],
    "RIVERSIDE": [
        ("LOC-RIV-01", "Riverside Cargo Terminal, Pier 9"),
        ("LOC-RIV-02", "Harbor View Marina, Dock B"),
        ("LOC-RIV-03", "Rivergate Freight Exchange, Logistics Way"),
        ("LOC-RIV-04", "Southbank Commuter Rail Station, Lot C"),
        ("LOC-RIV-05", "Waterfront Container Yard 3"),
        ("LOC-RIV-06", "Old Port Industrial Park, Warehouse 11"),
        ("LOC-RIV-07", "Bayside Commercial Fishery Office"),
        ("LOC-RIV-08", "Riverview Promenade, West Boardwalk"),
        ("LOC-RIV-09", "Delta Cold Storage Facility, Gate 2"),
        ("LOC-RIV-10", "Riverside Automotive Yard, East Perimeter"),
        ("LOC-RIV-11", "Anchor Point Ferry Terminal"),
        ("LOC-RIV-12", "Wharfside Seafood Market, Service Bay"),
        ("LOC-RIV-13", "Seaport Fuel Depot, Pump Station 4"),
        ("LOC-RIV-14", "River Bend Public Boat Ramp"),
        ("LOC-RIV-15", "Lighthouse Point Recreation Area"),
        ("LOC-RIV-16", "South Riverside Metal Recycling Plant"),
        ("LOC-RIV-17", "Drydock Marine Repair Slipway 2"),
        ("LOC-RIV-18", "Harbor Promenade Bicycle Path"),
        ("LOC-RIV-19", "Riverside Power Substation 5"),
        ("LOC-RIV-20", "Pier 14 Fish Packing Facility"),
    ],
}

ALL_LOCATIONS = [loc for sublist in LOCATIONS.values() for loc in sublist]
LOCATION_MAP = {loc[0]: loc[1] for loc in ALL_LOCATIONS}
LOCATION_STATION_MAP = {}
for station, locs in LOCATIONS.items():
    for loc_id, _ in locs:
        LOCATION_STATION_MAP[loc_id] = station

CAMERAS_BY_LOCATION = {}
for loc_id, _ in ALL_LOCATIONS:
    prefix = loc_id.replace("LOC-", "CAM-")
    CAMERAS_BY_LOCATION[loc_id] = [f"{prefix}-{i:02d}" for i in range(1, 4)]

CRIME_TYPES = [
    "BURGLARY",
    "VEHICLE_THEFT",
    "ROBBERY",
    "SHOPLIFTING",
    "VANDALISM",
    "FRAUD",
    "CARGO_THEFT",
    "BICYCLE_THEFT",
    "PROPERTY_DAMAGE",
    "IDENTITY_THEFT",
]

NEWSPAPERS = [
    ("Metro Daily Gazette", "HIGH"),
    ("Central City Chronicle", "HIGH"),
    ("Riverside Wharf News", "MEDIUM"),
    ("Northern Courier", "MEDIUM"),
    ("The Daily Herald", "HIGH"),
    ("Metropolitan Crime & Law Review", "HIGH"),
    ("City News Bulletin", "MEDIUM"),
    ("The Riverside Observer", "LOW"),
]

METHODS = {
    "BURGLARY": [
        "Forced rear door entry using heavy 36mm pry bar",
        "Pried open ground floor sliding window latch",
        "Smashed glass panel on side emergency exit",
        "Picked deadbolt lock on rear storage entrance",
        "Bypassed magnetic strike lock using plastic shim",
        "Cut roof skylight flashing and descended with ladder",
    ],
    "VEHICLE_THEFT": [
        "Keyless relay attack using RF signal amplifier on key fob",
        "Exhaust manifold severed with battery reciprocating saw for catalytic converter",
        "CAN-bus gateway injection via headlight wiring harness",
        "Punched ignition cylinder and hotwired column harness",
        "Towed target vehicle onto flatbed with forged municipal parking notice",
    ],
    "ROBBERY": [
        "Perpetrators brandished concealed handgun demanding safe contents",
        "Sprayed commercial pepper spray at clerk before seizing register tray",
        "Reversed vehicle into store display window in smash-and-grab ram raid",
        "Cornered victim in parking structure demanding luxury wristwatch",
    ],
    "SHOPLIFTING": [
        "Concealed high-end fragrance bottles in foil-lined booster bag",
        "Removed magnetic security ink tags using neodymium rare-earth magnet",
        "Swapped price barcodes with low-cost clearance items at self-checkout",
        "Distracted cashier with cash change scam while partner walked out with designer coats",
    ],
    "VANDALISM": [
        "Graffiti spray paint tagging on perimeter retaining walls",
        "Shattered glass bus shelter panels using ceramic spark plug fragments",
        "Acid etching on exterior display showroom windows",
        "Punctured delivery vehicle tires with steel construction nails",
    ],
    "FRAUD": [
        "Impersonated municipal water utility inspector to enter home and steal jewelry",
        "Submitted counterfeit electronic bill of lading to release palletized shipment",
        "Presented fake identification and returned stolen store merchandise for cash gift cards",
        "Compromised point-of-sale terminal with hidden Bluetooth skimming overlay",
    ],
    "CARGO_THEFT": [
        "Cut security bolt seal on 40ft container and offloaded palletized electronics",
        "Diverted refrigerated trailer using forged digital dispatch manifest",
        "Hooked unattended logistics tractor unit and departed facility without clearance",
        "Pried padlock on freight boxcar during scheduled railway junction pause",
    ],
    "BICYCLE_THEFT": [
        "Cut hardened steel U-lock with cordless angle grinder in 40 seconds",
        "Unbolted municipal bicycle rack fastener from concrete base",
        "Snapped cable lock using heavy 24-inch bolt cutters",
    ],
    "PROPERTY_DAMAGE": [
        "Intentionally rammed warehouse chain-link security gate with utility truck",
        "Flooded commercial basement by severing municipal water inlet pipe",
        "Poured abrasive quartz sand into fuel filler neck of heavy excavators",
    ],
    "IDENTITY_THEFT": [
        "Stole residential curbside mail containing bank cards and tax filings",
        "Intercepted replacement corporate credit card from office reception mailbox",
    ],
}

PROPERTIES = {
    "BURGLARY": [
        ["commercial safe", "cash", "payroll vouchers"],
        ["unlocked laptops", "high-end tablets", "server drives"],
        ["diamond rings", "luxury gold watches", "loose gems"],
        ["contractor power tools", "copper pipes", "brass fittings"],
        ["designer handbags", "cash drawer float"],
    ],
    "VEHICLE_THEFT": [
        ["OEM platinum-rhodium catalytic converter"],
        ["Lexus RX luxury SUV", "factory transponder key"],
        ["Range Rover Sport", "vehicle registration documents"],
        ["Honda Civic sedan", "personal tool kit in trunk"],
        ["Toyota Prius exhaust catalytic assembly"],
    ],
    "ROBBERY": [
        ["Rolex Submariner wristwatch", "leather wallet", "smart phone"],
        ["cash register contents", "lottery scratch tickets"],
        ["high-end retail jewelry", "gemstone necklaces"],
        ["night deposit bank bag", "cash receipts"],
    ],
    "SHOPLIFTING": [
        ["designer fragrance bottles", "cosmetics"],
        ["high-end winter jackets", "cashmere sweaters"],
        ["portable Bluetooth speakers", "noise-canceling headphones"],
        ["infant nutritional formula cases", "otc pharmaceuticals"],
    ],
    "VANDALISM": [
        ["tempered glass showroom windows", "display signage"],
        ["exterior brick facade", "concrete support columns"],
        ["commercial delivery van windshield", "side mirrors"],
    ],
    "FRAUD": [
        ["heirloom diamond earrings", "cash savings envelope"],
        ["counterfeit commercial store refund cards"],
        ["palletized pharmaceutical supplies"],
        ["cloned credit card transactions"],
    ],
    "CARGO_THEFT": [
        ["palletized consumer electronics", "smart televisions"],
        ["refrigerated biopharmaceutical vaccines", "temperature loggers"],
        ["industrial copper wire spools", "aluminum ingots"],
        ["designer athletic sneakers", "cartons of branded apparel"],
    ],
    "BICYCLE_THEFT": [
        ["carbon fiber road bicycle", "integrated GPS computer"],
        ["electric cargo commuter bicycle", "lithium battery pack"],
        ["mountain bike", "hydraulic disc brakes"],
    ],
    "PROPERTY_DAMAGE": [
        ["automated security gate arm", "perimeter fence"],
        ["industrial air conditioning compressor unit"],
    ],
    "IDENTITY_THEFT": [
        ["unactivated credit cards", "social security records"],
    ],
}

VEHICLES = [
    ("dark grey minivan with dented rear tailgate", "grey", "7XK***", "Dodge Grand Caravan"),
    ("silver compact sedan with black passenger door", "silver", "88M***", "Honda Civic"),
    ("white unmarked cargo van with roof ladder rack", "white", "3TJ***", "Ford Transit"),
    ("dark blue midnight pickup truck", "blue", "5WY***", "Chevrolet Silverado"),
    ("black luxury SUV with tinted windows", "black", "9PL***", "Lexus RX"),
    ("faded red hatchback with loud exhaust", "red", "2BC***", "Toyota Corolla"),
    ("matte dark sedan with smoked license plate", "black", null, "Audi A6"),
    ("cream-colored box delivery truck", "white", "4NV***", "Freightliner Box Truck"),
    ("dark green station wagon", "green", "6TR***", "Subaru Outback"),
]

FORENSIC_METHODS = {
    "TOOLMARK": ("COMPARISON_MICROSCOPY", "Striation comparison against reference tool database"),
    "DNA": ("STR_PROFILING", "Short tandem repeat capillary electrophoresis profiling"),
    "FINGERPRINT": ("AFIS_LATENT_SCAN", "Automated fingerprint identification latent minutiae search"),
    "BALLISTICS": ("IBIS_OPTICAL_SCAN", "Integrated Ballistics Identification System breech face comparison"),
    "DIGITAL_FOOTPRINT": ("LOG_AND_SIGNAL_ANALYSIS", "Telematics CAN-bus / RF packet injection diagnostic extraction"),
    "FIBER": ("POLARIZED_LIGHT_MICROSCOPY", "Micro-spectrophotometry fiber cross-section and dye analysis"),
    "CHEMICAL_RESIDUE": ("GC_MS", "Gas chromatography-mass spectrometry residue separation"),
    "TIRE_IMPRESSION": ("TREAD_PHOTOGRAMMETRY", "3D photogrammetric tread pitch and sipe pattern comparison"),
}


def to_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    # Ensure timestamp falls strictly within synthetic period 2025-2026
    if dt < BASE_START_TIME:
        dt = BASE_START_TIME
    elif dt > BASE_END_TIME:
        dt = BASE_END_TIME
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def random_date_between(start_dt: datetime, end_dt: datetime) -> datetime:
    delta_seconds = int((end_dt - start_dt).total_seconds())
    offset = random.randint(0, max(0, delta_seconds))
    return start_dt + timedelta(seconds=offset)


def create_planted_scenarios() -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Creates comprehensive cross-station planted scenarios, including:
    - Multi-station serial rings
    - Cross-source multi-view single incidents
    - Inconclusive/contradictory records
    - Distractors / false leads
    """
    ground_truth = []
    planted_records = {
        "police_incidents": [],
        "newspaper_reports": [],
        "witness_reports": [],
        "cctv_reports": [],
        "forensic_reports": [],
    }

    # 1. SCENARIO 1: Crowbar Safe Burglary Syndicate (NORTH & CENTRAL)
    inc_p1 = "INC-NORTH-0042"
    inc_p2 = "INC-CEN-0118"
    inc_p3 = "INC-NORTH-0294"
    dt1 = datetime(2025, 2, 14, 2, 15, 0, tzinfo=timezone.utc)
    dt2 = datetime(2025, 2, 22, 2, 45, 0, tzinfo=timezone.utc)
    dt3 = datetime(2025, 3, 9, 3, 10, 0, tzinfo=timezone.utc)

    # Incident 1 (North)
    planted_records["police_incidents"].append({
        "incident_id": inc_p1,
        "station_id": "NORTH",
        "reported_at": to_iso_utc(dt1 + timedelta(minutes=45)),
        "occurred_from": to_iso_utc(dt1),
        "occurred_to": to_iso_utc(dt1 + timedelta(minutes=30)),
        "crime_type": "BURGLARY",
        "location_id": "LOC-NORTH-01",
        "location_description": "Northgate Logistics Park, Warehouse 4B rear delivery bay",
        "method_description": "Forced rear fire door entry using 36mm chisel-tip heavy pry bar; targeted office drop safe",
        "property_involved": ["commercial drop safe", "cash float $18,400", "courier gas cards"],
        "estimated_loss": 18400.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-0105", "CCTV-0112"],
        "data_quality": "HIGH",
    })

    # Incident 2 (Central)
    planted_records["police_incidents"].append({
        "incident_id": inc_p2,
        "station_id": "CENTRAL",
        "reported_at": to_iso_utc(dt2 + timedelta(minutes=35)),
        "occurred_from": to_iso_utc(dt2),
        "occurred_to": to_iso_utc(dt2 + timedelta(minutes=25)),
        "crime_type": "BURGLARY",
        "location_id": "LOC-CEN-03",
        "location_description": "Grand Avenue Luxury Jewellers Arcade, Service corridor",
        "method_description": "Heavy pry tool applied to reinforced steel security frame; internal cash locker breached",
        "property_involved": ["loose diamonds", "custom watch cases", "cash vault $34,000"],
        "estimated_loss": 85000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-0240", "CCTV-0310"],
        "data_quality": "HIGH",
    })

    # Incident 3 (North)
    planted_records["police_incidents"].append({
        "incident_id": inc_p3,
        "station_id": "NORTH",
        "reported_at": to_iso_utc(dt3 + timedelta(minutes=50)),
        "occurred_from": to_iso_utc(dt3),
        "occurred_to": to_iso_utc(dt3 + timedelta(minutes=35)),
        "crime_type": "BURGLARY",
        "location_id": "LOC-NORTH-06",
        "location_description": "Oakridge Industrial Depot, Bay 7",
        "method_description": "Rear steel strike plate pried with distinctive 36mm striated tool; office cash safe removed",
        "property_involved": ["fireproof lockbox", "payroll cash $12,500"],
        "estimated_loss": 15000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": [],
        "data_quality": "HIGH",
    })

    # Witnesses for Scenario 1
    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0105",
        "submitted_at": to_iso_utc(dt1 + timedelta(hours=2)),
        "observed_from": to_iso_utc(dt1 + timedelta(minutes=15)),
        "observed_to": to_iso_utc(dt1 + timedelta(minutes=28)),
        "location_id": "LOC-NORTH-01",
        "observation_text": "Saw two figures in dark coveralls carrying a heavy rectangular metal box into a dark grey minivan. Tailgate had a deep horizontal dent.",
        "observed_entities": ["two masked individuals in coveralls", "dark grey minivan with dented tailgate"],
        "vehicle_description": "dark grey Dodge Caravan with dented tailgate",
        "direction_of_travel": "Southbound towards Central expressway",
        "confidence_level": "HIGH",
        "related_incident_ids": [inc_p1],
        "contradiction_flags": [],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0240",
        "submitted_at": to_iso_utc(dt2 + timedelta(hours=3)),
        "observed_from": to_iso_utc(dt2 + timedelta(minutes=10)),
        "observed_to": to_iso_utc(dt2 + timedelta(minutes=22)),
        "location_id": "LOC-CEN-03",
        "observation_text": "Heard metallic screech in alley. Observed two men loading heavy sacks into a grey SUV or van. Noticed dent on rear gate.",
        "observed_entities": ["two men carrying heavy duffle bags"],
        "vehicle_description": "grey SUV or large minivan with rear damage",
        "direction_of_travel": "Turned onto Market Street heading north",
        "confidence_level": "MEDIUM",
        "related_incident_ids": [inc_p2],
        "contradiction_flags": ["vehicle_model_discrepancy_suv_vs_minivan"],
        "data_quality": "MEDIUM",
    })

    # CCTV for Scenario 1
    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0112",
        "camera_id": "CAM-NORTH-01-01",
        "location_id": "LOC-NORTH-01",
        "recorded_from": to_iso_utc(dt1),
        "recorded_to": to_iso_utc(dt1 + timedelta(minutes=30)),
        "observed_entities": ["two subjects in high-vis jackets over dark hoodies", "dark grey minivan"],
        "vehicle_description": "dark grey minivan with damaged rear tailgate",
        "vehicle_color": "grey",
        "partial_plate": "7XK***",
        "movement_description": "Minivan backed into loading bay; subjects loaded rectangular item; departed south at high speed",
        "image_quality": "MODERATE",
        "observation_confidence": 0.88,
        "related_incident_ids": [inc_p1],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0310",
        "camera_id": "CAM-CEN-03-02",
        "location_id": "LOC-CEN-03",
        "recorded_from": to_iso_utc(dt2),
        "recorded_to": to_iso_utc(dt2 + timedelta(minutes=25)),
        "observed_entities": ["two unidentified subjects", "36-inch crowbar", "dark minivan"],
        "vehicle_description": "dark grey passenger minivan",
        "vehicle_color": "grey",
        "partial_plate": "7XK***",
        "movement_description": "Vehicle idled in alleyway with lights extinguished; departed north towards North precinct line",
        "image_quality": "NIGHT_IR_LOW_RES",
        "observation_confidence": 0.74,
        "related_incident_ids": [inc_p2],
        "data_quality": "MEDIUM",
    })

    # Forensics for Scenario 1
    evd_1 = "EVD-2025-0089"
    evd_2 = "EVD-2025-0195"
    evd_3 = "EVD-2025-0342"
    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0089",
        "incident_id": inc_p1,
        "evidence_item_id": evd_1,
        "collected_at": to_iso_utc(dt1 + timedelta(hours=4)),
        "location_id": "LOC-NORTH-01",
        "evidence_type": "TOOLMARK",
        "description": "Striated impressions and paint scrapings lifted from rear warehouse fire door strike plate",
        "examination_method": "COMPARISON_MICROSCOPY",
        "result_summary": "Distinctive 36mm chisel tip toolmark with asymmetric microscopic edge notch",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_2, evd_3],
        "limitations": "Reference physical tool has not yet been recovered",
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0195",
        "incident_id": inc_p2,
        "evidence_item_id": evd_2,
        "collected_at": to_iso_utc(dt2 + timedelta(hours=5)),
        "location_id": "LOC-CEN-03",
        "evidence_type": "TOOLMARK",
        "description": "Toolmark impressions from jewellers arcade exterior security door jam",
        "examination_method": "COMPARISON_MICROSCOPY",
        "result_summary": "100% microscopic striated congruence with EVD-2025-0089, demonstrating same pry tool",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_1],
        "limitations": null,
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0342",
        "incident_id": inc_p3,
        "evidence_item_id": evd_3,
        "collected_at": to_iso_utc(dt3 + timedelta(hours=3)),
        "location_id": "LOC-NORTH-06",
        "evidence_type": "TOOLMARK",
        "description": "Steel door frame impression castings from Oakridge industrial depot break-in",
        "examination_method": "COMPARISON_MICROSCOPY",
        "result_summary": "Matching 36mm striated toolmark profile identical to EVD-2025-0089 and EVD-2025-0195",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_1, evd_2],
        "limitations": null,
        "data_quality": "HIGH",
    })

    # Newspaper for Scenario 1
    planted_records["newspaper_reports"].append({
        "news_id": "NEWS-0064",
        "publication_name": "Metro Daily Gazette",
        "published_at": to_iso_utc(dt2 + timedelta(days=2)),
        "headline": "Midnight Safe Heists Strike North and Central Warehouses",
        "article_text": "Detectives across North and Central station jurisdictions are investigating a pattern of overnight break-ins targeting commercial safes. Witnesses reported seeing a grey minivan fleeing the scene with rear tailgate damage.",
        "mentioned_date_from": to_iso_utc(dt1),
        "mentioned_date_to": to_iso_utc(dt2),
        "mentioned_location_ids": ["LOC-NORTH-01", "LOC-CEN-03"],
        "crime_labels": ["BURGLARY", "ORGANIZED_THEFT"],
        "mentioned_property": ["commercial safes", "cash", "loose diamonds"],
        "related_incident_ids": [inc_p1, inc_p2],
        "source_reliability": "HIGH",
        "data_quality": "HIGH",
    })

    ground_truth.append({
        "relationship_id": "REL-SERIES-001",
        "title": "Cross-Station Commercial Safe Burglary Syndicate (North & Central)",
        "scenario_type": "SERIAL_BURGLARY",
        "stations_involved": ["NORTH", "CENTRAL"],
        "incident_ids": [inc_p1, inc_p2, inc_p3],
        "source_record_ids": {
            "witness_reports": ["WIT-0105", "WIT-0240"],
            "cctv_reports": ["CCTV-0112", "CCTV-0310"],
            "forensic_reports": ["FOR-0089", "FOR-0195", "FOR-0342"],
            "newspaper_reports": ["NEWS-0064"],
        },
        "why_related": "Cross-station organized burglary ring targeting commercial office safes using identical 36mm chisel-tip pry bar and a dark grey Dodge Caravan with dented tailgate (plate 7XK***).",
        "supporting_evidence": [
            "Forensic toolmark microscopic striations match exactly between FOR-0089, FOR-0195, and FOR-0342",
            "CCTV-0112 and CCTV-0310 both capture dark grey minivan with identical partial plate '7XK***' and tailgate dent",
            "Consistent early morning weekend timeframes (02:15 to 03:10 UTC)",
        ],
        "contradictions_and_limitations": [
            "WIT-0240 observed vehicle as an SUV while WIT-0105 and CCTV confirmed minivan (tailgate dent matches)",
            "CCTV-0310 suffered from night-IR glare preventing facial identification",
        ],
        "confidence_label": "HIGH",
    })

    # 2. SCENARIO 2: Catalytic Converter Theft Ring (CENTRAL & RIVERSIDE)
    inc_cat1 = "INC-CEN-0450"
    inc_cat2 = "INC-RIV-0182"
    inc_cat3 = "INC-RIV-0305"
    dt_cat1 = datetime(2025, 4, 11, 3, 30, 0, tzinfo=timezone.utc)
    dt_cat2 = datetime(2025, 4, 18, 4, 10, 0, tzinfo=timezone.utc)
    dt_cat3 = datetime(2025, 5, 2, 3, 50, 0, tzinfo=timezone.utc)

    planted_records["police_incidents"].append({
        "incident_id": inc_cat1,
        "station_id": "CENTRAL",
        "reported_at": to_iso_utc(dt_cat1 + timedelta(hours=3)),
        "occurred_from": to_iso_utc(dt_cat1),
        "occurred_to": to_iso_utc(dt_cat1 + timedelta(minutes=20)),
        "crime_type": "VEHICLE_THEFT",
        "location_id": "LOC-CEN-04",
        "location_description": "Civic Center Underground Parking, Level P2 commuter section",
        "method_description": "Exhaust pipes severed with carbide reciprocating saw; 3 Toyota Prius converters removed",
        "property_involved": ["3 OEM Toyota catalytic converters"],
        "estimated_loss": 7500.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-0412", "CCTV-0480"],
        "data_quality": "HIGH",
    })

    planted_records["police_incidents"].append({
        "incident_id": inc_cat2,
        "station_id": "RIVERSIDE",
        "reported_at": to_iso_utc(dt_cat2 + timedelta(hours=2)),
        "occurred_from": to_iso_utc(dt_cat2),
        "occurred_to": to_iso_utc(dt_cat2 + timedelta(minutes=15)),
        "crime_type": "VEHICLE_THEFT",
        "location_id": "LOC-RIV-04",
        "location_description": "Southbank Commuter Rail Station, Lot C overnight parking",
        "method_description": "Rapid jack-and-saw operation targeting hybrid vehicles; severed exhaust tubing recovered",
        "property_involved": ["2 hybrid catalytic converters"],
        "estimated_loss": 5000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-0628"],
        "data_quality": "HIGH",
    })

    planted_records["police_incidents"].append({
        "incident_id": inc_cat3,
        "station_id": "RIVERSIDE",
        "reported_at": to_iso_utc(dt_cat3 + timedelta(hours=4)),
        "occurred_from": to_iso_utc(dt_cat3),
        "occurred_to": to_iso_utc(dt_cat3 + timedelta(minutes=25)),
        "crime_type": "VEHICLE_THEFT",
        "location_id": "LOC-RIV-10",
        "location_description": "Riverside Automotive Yard, East Perimeter",
        "method_description": "Catalytic converters stripped from parked fleet vehicles using high-speed cordless saw",
        "property_involved": ["4 fleet vehicle catalytic converters"],
        "estimated_loss": 9200.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["CCTV-0690"],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0412",
        "submitted_at": to_iso_utc(dt_cat1 + timedelta(hours=2)),
        "observed_from": to_iso_utc(dt_cat1 + timedelta(minutes=5)),
        "observed_to": to_iso_utc(dt_cat1 + timedelta(minutes=18)),
        "location_id": "LOC-CEN-04",
        "observation_text": "Heard loud motorized screeching sound echoing through underground garage. Saw a silver sedan idling with headlights off. One person in a red work jacket slid out from under a Prius with an exhaust pipe.",
        "observed_entities": ["individual in red jacket", "silver sedan"],
        "vehicle_description": "silver Honda Civic with black passenger door",
        "direction_of_travel": "Exited garage toward South Riverside Bridge",
        "confidence_level": "HIGH",
        "related_incident_ids": [inc_cat1],
        "contradiction_flags": [],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0628",
        "submitted_at": to_iso_utc(dt_cat2 + timedelta(hours=1)),
        "observed_from": to_iso_utc(dt_cat2 + timedelta(minutes=8)),
        "observed_to": to_iso_utc(dt_cat2 + timedelta(minutes=14)),
        "location_id": "LOC-RIV-04",
        "observation_text": "Commuter walking dog saw someone jacking up a car. Suspect was wearing all black with a dark hoodie, not red. Silver car was parked next to it.",
        "observed_entities": ["suspect in dark hoodie", "silver sedan"],
        "vehicle_description": "silver compact sedan",
        "direction_of_travel": "South on Logistics Way",
        "confidence_level": "MEDIUM",
        "related_incident_ids": [inc_cat2],
        "contradiction_flags": ["suspect_clothing_color_black_vs_red"],
        "data_quality": "MEDIUM",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0480",
        "camera_id": "CAM-CEN-04-01",
        "location_id": "LOC-CEN-04",
        "recorded_from": to_iso_utc(dt_cat1),
        "recorded_to": to_iso_utc(dt_cat1 + timedelta(minutes=25)),
        "observed_entities": ["silver sedan with mismatched black passenger door", "jack stand", "sparks from undercarriage"],
        "vehicle_description": "silver sedan with black passenger door",
        "vehicle_color": "silver",
        "partial_plate": "88M***",
        "movement_description": "Silver sedan circled lot; stopped adjacent to victim vehicle; passenger exited with jack and power saw; operation concluded in 85 seconds",
        "image_quality": "CLEAR",
        "observation_confidence": 0.94,
        "related_incident_ids": [inc_cat1],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0690",
        "camera_id": "CAM-RIV-10-02",
        "location_id": "LOC-RIV-10",
        "recorded_from": to_iso_utc(dt_cat3),
        "recorded_to": to_iso_utc(dt_cat3 + timedelta(minutes=30)),
        "observed_entities": ["silver compact car", "rapid cutting activity"],
        "vehicle_description": "silver compact car with contrasting dark passenger side panel",
        "vehicle_color": "silver",
        "partial_plate": "88M***",
        "movement_description": "Vehicle entered perimeter through gap in chainlink fence; departed westbound",
        "image_quality": "MODERATE",
        "observation_confidence": 0.82,
        "related_incident_ids": [inc_cat3],
        "data_quality": "HIGH",
    })

    evd_cat1 = "EVD-2025-0380"
    evd_cat2 = "EVD-2025-0512"
    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0380",
        "incident_id": inc_cat1,
        "evidence_item_id": evd_cat1,
        "collected_at": to_iso_utc(dt_cat1 + timedelta(hours=5)),
        "location_id": "LOC-CEN-04",
        "evidence_type": "CHEMICAL_RESIDUE",
        "description": "Metal tooth fragments and tungsten-carbide blade coating residue vacuumed from concrete beneath cut exhaust",
        "examination_method": "GC_MS",
        "result_summary": "Tungsten carbide alloy with distinctive titanium carbonitride coating matching 9-TPI Milwaukee Torch blade",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_cat2],
        "limitations": null,
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0512",
        "incident_id": inc_cat2,
        "evidence_item_id": evd_cat2,
        "collected_at": to_iso_utc(dt_cat2 + timedelta(hours=4)),
        "location_id": "LOC-RIV-04",
        "evidence_type": "CHEMICAL_RESIDUE",
        "description": "Exhaust pipe cut metal shavings collected at Southbank rail lot",
        "examination_method": "GC_MS",
        "result_summary": "Identical tungsten-carbide metallurgical matrix and titanium carbonitride trace matching EVD-2025-0380",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_cat1],
        "limitations": null,
        "data_quality": "HIGH",
    })

    planted_records["newspaper_reports"].append({
        "news_id": "NEWS-0215",
        "publication_name": "Riverside Wharf News",
        "published_at": to_iso_utc(dt_cat2 + timedelta(days=1)),
        "headline": "Commuter Rail Parking Lots Targeted by Rapid Catalytic Converter Thieves",
        "article_text": "Police warn commuters after another overnight theft at Southbank Station. Similar incidents were reported in Central parking structures, pointing to an organized crew operating across regional boundaries.",
        "mentioned_date_from": to_iso_utc(dt_cat1),
        "mentioned_date_to": to_iso_utc(dt_cat2),
        "mentioned_location_ids": ["LOC-CEN-04", "LOC-RIV-04"],
        "crime_labels": ["VEHICLE_THEFT", "ORGANIZED_THEFT"],
        "mentioned_property": ["catalytic converters"],
        "related_incident_ids": [inc_cat1, inc_cat2],
        "source_reliability": "MEDIUM",
        "data_quality": "HIGH",
    })

    ground_truth.append({
        "relationship_id": "REL-SERIES-002",
        "title": "Cross-Station Commuter Catalytic Converter Syndicate (Central & Riverside)",
        "scenario_type": "SERIAL_THEFT",
        "stations_involved": ["CENTRAL", "RIVERSIDE"],
        "incident_ids": [inc_cat1, inc_cat2, inc_cat3],
        "source_record_ids": {
            "witness_reports": ["WIT-0412", "WIT-0628"],
            "cctv_reports": ["CCTV-0480", "CCTV-0690"],
            "forensic_reports": ["FOR-0380", "FOR-0512"],
            "newspaper_reports": ["NEWS-0215"],
        },
        "why_related": "Coordinated theft crew using silver Honda Civic with black passenger door (partial plate 88M***) and tungsten-carbide saw blades to sever catalytic converters at commuter parking facilities in Central and Riverside.",
        "supporting_evidence": [
            "Forensic GC-MS blade coating residue matches identically between FOR-0380 and FOR-0512",
            "CCTV-0480 and CCTV-0690 both depict silver sedan with distinct black passenger door and plate 88M***",
            "Matching sub-90-second jack-and-cut methodology across both station jurisdictions",
        ],
        "contradictions_and_limitations": [
            "Clothing color contradiction: WIT-0412 reported red work jacket while WIT-0628 reported dark hoodie (suggests 2 crew members or outfit change)",
        ],
        "confidence_label": "HIGH",
    })

    # 3. SCENARIO 3: Keyless Luxury SUV Relay Ring (NORTH & RIVERSIDE)
    inc_suv1 = "INC-NORTH-0720"
    inc_suv2 = "INC-RIV-0590"
    dt_suv1 = datetime(2025, 6, 8, 3, 15, 0, tzinfo=timezone.utc)
    dt_suv2 = datetime(2025, 6, 17, 3, 40, 0, tzinfo=timezone.utc)

    planted_records["police_incidents"].append({
        "incident_id": inc_suv1,
        "station_id": "NORTH",
        "reported_at": to_iso_utc(dt_suv1 + timedelta(hours=4)),
        "occurred_from": to_iso_utc(dt_suv1),
        "occurred_to": to_iso_utc(dt_suv1 + timedelta(minutes=10)),
        "crime_type": "VEHICLE_THEFT",
        "location_id": "LOC-NORTH-03",
        "location_description": "Silver Lake Residential Estate, Maple Drive private residence",
        "method_description": "Keyless relay attack; RF signal intercepted from front hall key fob; 2024 Lexus RX driven away without breaking glass",
        "property_involved": ["2024 Lexus RX 350 SUV", "garage remote"],
        "estimated_loss": 68000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-0785", "CCTV-0810"],
        "data_quality": "HIGH",
    })

    planted_records["police_incidents"].append({
        "incident_id": inc_suv2,
        "station_id": "RIVERSIDE",
        "reported_at": to_iso_utc(dt_suv2 + timedelta(hours=3)),
        "occurred_from": to_iso_utc(dt_suv2),
        "occurred_to": to_iso_utc(dt_suv2 + timedelta(minutes=12)),
        "crime_type": "VEHICLE_THEFT",
        "location_id": "LOC-RIV-02",
        "location_description": "Harbor View Marina, Dock B residential slips access road",
        "method_description": "Relay amplifier device used against Range Rover Sport; vehicle driven directly into port container staging lane",
        "property_involved": ["2023 Range Rover Sport", "golf clubs in cargo bay"],
        "estimated_loss": 92000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-0890", "CCTV-0955"],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0785",
        "submitted_at": to_iso_utc(dt_suv1 + timedelta(hours=2)),
        "observed_from": to_iso_utc(dt_suv1 + timedelta(minutes=2)),
        "observed_to": to_iso_utc(dt_suv1 + timedelta(minutes=8)),
        "location_id": "LOC-NORTH-03",
        "observation_text": "Neighbor saw two men standing by victim's porch holding a large messenger bag against the front door. Lexus headlights flashed and vehicle started silently.",
        "observed_entities": ["two men carrying large antenna shoulder bag"],
        "vehicle_description": "2024 Lexus RX (stolen vehicle)",
        "direction_of_travel": "Headed toward Highway 10 connector",
        "confidence_level": "HIGH",
        "related_incident_ids": [inc_suv1],
        "contradiction_flags": [],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0890",
        "submitted_at": to_iso_utc(dt_suv2 + timedelta(hours=1)),
        "observed_from": to_iso_utc(dt_suv2 + timedelta(minutes=10)),
        "observed_to": to_iso_utc(dt_suv2 + timedelta(minutes=20)),
        "location_id": "LOC-RIV-02",
        "observation_text": "Night watchman observed Range Rover driving rapidly past marina gates without lights on, convoying behind an Audi sedan.",
        "observed_entities": ["Range Rover driving dark", "dark Audi sedan escort"],
        "vehicle_description": "stolen Range Rover and dark Audi sedan",
        "direction_of_travel": "Entering Pier 9 container gates",
        "confidence_level": "MEDIUM",
        "related_incident_ids": [inc_suv2],
        "contradiction_flags": [],
        "data_quality": "MEDIUM",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0810",
        "camera_id": "CAM-NORTH-03-01",
        "location_id": "LOC-NORTH-03",
        "recorded_from": to_iso_utc(dt_suv1),
        "recorded_to": to_iso_utc(dt_suv1 + timedelta(minutes=15)),
        "observed_entities": ["two figures holding loop antenna", "victim Lexus SUV"],
        "vehicle_description": "Lexus RX 350",
        "vehicle_color": "black",
        "partial_plate": null,
        "movement_description": "Subjects waved loop antenna near front door; vehicle exterior lights pulsed; driver side unlocked; vehicle exited driveway in under 45 seconds",
        "image_quality": "CLEAR",
        "observation_confidence": 0.91,
        "related_incident_ids": [inc_suv1],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0955",
        "camera_id": "CAM-RIV-01-03",
        "location_id": "LOC-RIV-01",
        "recorded_from": to_iso_utc(dt_suv2 + timedelta(minutes=15)),
        "recorded_to": to_iso_utc(dt_suv2 + timedelta(minutes=30)),
        "observed_entities": ["luxury Range Rover", "dark Audi sedan"],
        "vehicle_description": "Range Rover Sport followed by dark Audi sedan",
        "vehicle_color": "black",
        "partial_plate": "9PL***",
        "movement_description": "Convey entered Pier 9 freight staging lane and turned into warehouse bay",
        "image_quality": "DEGRADED",
        "observation_confidence": 0.68,
        "related_incident_ids": [inc_suv2],
        "data_quality": "MEDIUM",
    })

    evd_suv1 = "EVD-2025-0640"
    evd_suv2 = "EVD-2025-0775"
    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0640",
        "incident_id": inc_suv1,
        "evidence_item_id": evd_suv1,
        "collected_at": to_iso_utc(dt_suv1 + timedelta(hours=6)),
        "location_id": "LOC-NORTH-03",
        "evidence_type": "DIGITAL_FOOTPRINT",
        "description": "Recovered telematics OEM server handshake logs for stolen Lexus",
        "examination_method": "LOG_AND_SIGNAL_ANALYSIS",
        "result_summary": "Extracted RF handshake packet payload confirms 315MHz carrier frequency relay attack packet injection with cloned session token",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_suv2],
        "limitations": "Physical relay device not recovered",
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0775",
        "incident_id": inc_suv2,
        "evidence_item_id": evd_suv2,
        "collected_at": to_iso_utc(dt_suv2 + timedelta(hours=8)),
        "location_id": "LOC-RIV-02",
        "evidence_type": "DIGITAL_FOOTPRINT",
        "description": "Vehicle gateway controller telematics dump from recovered Range Rover telematics ping",
        "examination_method": "LOG_AND_SIGNAL_ANALYSIS",
        "result_summary": "Identical RF session token injection signature and crypto handshake bypass matching EVD-2025-0640",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_suv1],
        "limitations": null,
        "data_quality": "HIGH",
    })

    planted_records["newspaper_reports"].append({
        "news_id": "NEWS-0340",
        "publication_name": "Metropolitan Crime & Law Review",
        "published_at": to_iso_utc(dt_suv2 + timedelta(days=2)),
        "headline": "Sophisticated Relay Thieves Intercept Luxury SUVs Across North Suburbs and Waterfront",
        "article_text": "High-end vehicle owners are urged to store key fobs in Faraday pouches after synchronized keyless thefts in Silver Lake and Riverside Marina. Investigators suspect vehicles are funneled through port shipping containers.",
        "mentioned_date_from": to_iso_utc(dt_suv1),
        "mentioned_date_to": to_iso_utc(dt_suv2),
        "mentioned_location_ids": ["LOC-NORTH-03", "LOC-RIV-02"],
        "crime_labels": ["VEHICLE_THEFT", "ORGANIZED_THEFT"],
        "mentioned_property": ["luxury SUVs", "Lexus RX", "Range Rover Sport"],
        "related_incident_ids": [inc_suv1, inc_suv2],
        "source_reliability": "HIGH",
        "data_quality": "HIGH",
    })

    ground_truth.append({
        "relationship_id": "REL-SERIES-003",
        "title": "Cross-Station Luxury SUV Keyless Relay Syndicate (North & Riverside)",
        "scenario_type": "ORGANIZED_VEHICLE_THEFT",
        "stations_involved": ["NORTH", "RIVERSIDE"],
        "incident_ids": [inc_suv1, inc_suv2],
        "source_record_ids": {
            "witness_reports": ["WIT-0785", "WIT-0890"],
            "cctv_reports": ["CCTV-0810", "CCTV-0955"],
            "forensic_reports": ["FOR-0640", "FOR-0775"],
            "newspaper_reports": ["NEWS-0340"],
        },
        "why_related": "Professional automotive theft ring using advanced RF loop-antenna relay hardware to steal push-to-start luxury SUVs in North residential areas and transfer them to Riverside container piers.",
        "supporting_evidence": [
            "Identical digital RF relay handshake exploit packet signature verified in FOR-0640 and FOR-0775",
            "CCTV-0810 records exact 45-second keyless loop antenna attack method",
            "CCTV-0955 and WIT-0890 trace stolen luxury convoy into Riverside Pier 9 container staging lanes",
        ],
        "contradictions_and_limitations": [
            "CCTV-0955 captured convoy at distance under degraded port lighting; partial plate 9PL*** captured",
        ],
        "confidence_label": "HIGH",
    })

    # 4. SCENARIO 4: Impostor Utility Water Worker Distraction Burglary (CENTRAL & NORTH)
    inc_w1 = "INC-CEN-0812"
    inc_w2 = "INC-NORTH-1104"
    dt_w1 = datetime(2025, 7, 15, 14, 0, 0, tzinfo=timezone.utc)
    dt_w2 = datetime(2025, 7, 24, 15, 30, 0, tzinfo=timezone.utc)

    planted_records["police_incidents"].append({
        "incident_id": inc_w1,
        "station_id": "CENTRAL",
        "reported_at": to_iso_utc(dt_w1 + timedelta(hours=3)),
        "occurred_from": to_iso_utc(dt_w1),
        "occurred_to": to_iso_utc(dt_w1 + timedelta(minutes=45)),
        "crime_type": "FRAUD",
        "location_id": "LOC-CEN-07",
        "location_description": "Residential row near St. Jude Hospital, Central",
        "method_description": "Suspects posed as municipal water inspectors claiming urgent water main leak; one suspect led elderly homeowner to basement while accomplice searched master bedroom",
        "property_involved": ["vintage gold watches", "diamond jewelry box", "$4,800 cash savings"],
        "estimated_loss": 26000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-1020", "CCTV-1130"],
        "data_quality": "HIGH",
    })

    planted_records["police_incidents"].append({
        "incident_id": inc_w2,
        "station_id": "NORTH",
        "reported_at": to_iso_utc(dt_w2 + timedelta(hours=2)),
        "occurred_from": to_iso_utc(dt_w2),
        "occurred_to": to_iso_utc(dt_w2 + timedelta(minutes=40)),
        "crime_type": "FRAUD",
        "location_id": "LOC-NORTH-07",
        "location_description": "Crestview Heights, Hilltop Way residential dwelling",
        "method_description": "Pair posing as municipal water utility crew wearing fluorescent vests and fake identification badges; ransacked upstairs while homeowner ran kitchen taps",
        "property_involved": ["heirloom diamond earrings", "family coin collection"],
        "estimated_loss": 31000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-1180", "CCTV-1310"],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-1020",
        "submitted_at": to_iso_utc(dt_w1 + timedelta(hours=2)),
        "observed_from": to_iso_utc(dt_w1),
        "observed_to": to_iso_utc(dt_w1 + timedelta(minutes=40)),
        "location_id": "LOC-CEN-07",
        "observation_text": "Victim reported two men in orange vests claiming to be with 'City Water Department'. One had a clipboard and told victim to keep basement valves open.",
        "observed_entities": ["two men in high-vis vests with clipboard and fake badges"],
        "vehicle_description": "white Ford Transit van with roof ladder rack",
        "direction_of_travel": "Drove north toward Highland corridor",
        "confidence_level": "HIGH",
        "related_incident_ids": [inc_w1],
        "contradiction_flags": [],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-1180",
        "submitted_at": to_iso_utc(dt_w2 + timedelta(hours=1)),
        "observed_from": to_iso_utc(dt_w2),
        "observed_to": to_iso_utc(dt_w2 + timedelta(minutes=35)),
        "location_id": "LOC-NORTH-07",
        "observation_text": "Victim stated two men wore yellow vests and claimed badge was from 'Metro Water Works', not City Water. One held a brass pipe wrench.",
        "observed_entities": ["two men with yellow utility vests and clipboards"],
        "vehicle_description": "white utility van with ladder rack",
        "direction_of_travel": "Headed downhill toward Highway 10",
        "confidence_level": "MEDIUM",
        "related_incident_ids": [inc_w2],
        "contradiction_flags": ["impostor_badge_name_and_vest_color_discrepancy"],
        "data_quality": "MEDIUM",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-1130",
        "camera_id": "CAM-CEN-07-01",
        "location_id": "LOC-CEN-07",
        "recorded_from": to_iso_utc(dt_w1 - timedelta(minutes=10)),
        "recorded_to": to_iso_utc(dt_w1 + timedelta(minutes=50)),
        "observed_entities": ["white Ford Transit van", "two males with clipboards"],
        "vehicle_description": "white Ford Transit van with ladder rack on roof and orange safety beacon",
        "vehicle_color": "white",
        "partial_plate": "3TJ***",
        "movement_description": "Van parked curbside; two men exited with clipboards; departed calmly 42 minutes later",
        "image_quality": "CLEAR",
        "observation_confidence": 0.95,
        "related_incident_ids": [inc_w1],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-1310",
        "camera_id": "CAM-NORTH-07-02",
        "location_id": "LOC-NORTH-07",
        "recorded_from": to_iso_utc(dt_w2 - timedelta(minutes=15)),
        "recorded_to": to_iso_utc(dt_w2 + timedelta(minutes=45)),
        "observed_entities": ["white cargo van with ladder rack", "two men in safety vests"],
        "vehicle_description": "white commercial van with roof ladder rack",
        "vehicle_color": "white",
        "partial_plate": "3TJ***",
        "movement_description": "Van matched Central vehicle; entered Hilltop Way cul-de-sac; departed north",
        "image_quality": "MODERATE",
        "observation_confidence": 0.86,
        "related_incident_ids": [inc_w2],
        "data_quality": "HIGH",
    })

    evd_w1 = "EVD-2025-0890"
    evd_w2 = "EVD-2025-1025"
    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0890",
        "incident_id": inc_w1,
        "evidence_item_id": evd_w1,
        "collected_at": to_iso_utc(dt_w1 + timedelta(hours=4)),
        "location_id": "LOC-CEN-07",
        "evidence_type": "FINGERPRINT",
        "description": "Latent palm print lifted from polished mahogany dresser drawer handle",
        "examination_method": "AFIS_LATENT_SCAN",
        "result_summary": "High-clarity latent palm print with 14 identifiable ridge bifurcations and minutiae points",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_w2],
        "limitations": "Subject has no prior record in state AFIS database",
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-1025",
        "incident_id": inc_w2,
        "evidence_item_id": evd_w2,
        "collected_at": to_iso_utc(dt_w2 + timedelta(hours=5)),
        "location_id": "LOC-NORTH-07",
        "evidence_type": "FINGERPRINT",
        "description": "Latent fingerprint lifted from jewelry box lid at Crestview Heights residence",
        "examination_method": "AFIS_LATENT_SCAN",
        "result_summary": "Minutiae match confirms identical individual responsible for EVD-2025-0890 palm friction ridge sequence",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_w1],
        "limitations": null,
        "data_quality": "HIGH",
    })

    planted_records["newspaper_reports"].append({
        "news_id": "NEWS-0480",
        "publication_name": "Central City Chronicle",
        "published_at": to_iso_utc(dt_w2 + timedelta(days=1)),
        "headline": "Bogus Water Inspectors Target Elderly Residents in Cross-Precinct Scam",
        "article_text": "Central and North station detectives issued an urgent public alert regarding impostor water utility workers. The suspects claim pipe contamination to distract homeowners while stealing cash and heirlooms.",
        "mentioned_date_from": to_iso_utc(dt_w1),
        "mentioned_date_to": to_iso_utc(dt_w2),
        "mentioned_location_ids": ["LOC-CEN-07", "LOC-NORTH-07"],
        "crime_labels": ["FRAUD", "BURGLARY"],
        "mentioned_property": ["jewelry", "cash", "heirloom earrings"],
        "related_incident_ids": [inc_w1, inc_w2],
        "source_reliability": "HIGH",
        "data_quality": "HIGH",
    })

    ground_truth.append({
        "relationship_id": "REL-SERIES-004",
        "title": "Cross-Station Distraction Burglary Scam Ring (Central & North)",
        "scenario_type": "DISTRACTION_BURGLARY_FRAUD",
        "stations_involved": ["CENTRAL", "NORTH"],
        "incident_ids": [inc_w1, inc_w2],
        "source_record_ids": {
            "witness_reports": ["WIT-1020", "WIT-1180"],
            "cctv_reports": ["CCTV-1130", "CCTV-1310"],
            "forensic_reports": ["FOR-0890", "FOR-1025"],
            "newspaper_reports": ["NEWS-0480"],
        },
        "why_related": "Two-man team impersonating municipal water utility inspectors across Central and North stations to conduct distraction burglaries using a white Ford Transit van with ladder rack (partial plate 3TJ***).",
        "supporting_evidence": [
            "Forensic AFIS latent print match between FOR-0890 and FOR-1025 proves identical perpetrator handled victim property",
            "CCTV-1130 and CCTV-1310 verify identical white Ford Transit van with roof ladder rack and plate 3TJ***",
            "Identical MO involving fake water leak/contamination story requiring basement or kitchen water tap running",
        ],
        "contradictions_and_limitations": [
            "Witnesses reported slight badge name variation ('City Water Dept' vs 'Metro Water Works') and vest color (orange vs yellow), indicating varied props used by suspects",
        ],
        "confidence_label": "HIGH",
    })

    # 5. SCENARIO 5: Grand Avenue Jewellers Ram-Raid (CENTRAL - Multi-source single incident deep dive)
    inc_ram = "INC-CEN-0005"
    dt_ram = datetime(2025, 1, 18, 1, 10, 0, tzinfo=timezone.utc)

    planted_records["police_incidents"].append({
        "incident_id": inc_ram,
        "station_id": "CENTRAL",
        "reported_at": to_iso_utc(dt_ram + timedelta(minutes=8)),
        "occurred_from": to_iso_utc(dt_ram),
        "occurred_to": to_iso_utc(dt_ram + timedelta(minutes=5)),
        "crime_type": "ROBBERY",
        "location_id": "LOC-CEN-03",
        "location_description": "Grand Avenue Luxury Jewellers Arcade, streetfront facade",
        "method_description": "Stolen blue pickup truck reversed into reinforced security storefront window; 3 masked subjects entered with sledgehammers, clearing display cabinets in 180 seconds before abandoning truck and fleeing in black sedan",
        "property_involved": ["luxury swiss watches", "platinum gemstone rings", "gold necklaces"],
        "estimated_loss": 340000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-0012", "WIT-0015", "CCTV-0020", "CCTV-0024", "FOR-0010", "FOR-0014"],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0012",
        "submitted_at": to_iso_utc(dt_ram + timedelta(minutes=25)),
        "observed_from": to_iso_utc(dt_ram),
        "observed_to": to_iso_utc(dt_ram + timedelta(minutes=4)),
        "location_id": "LOC-CEN-03",
        "observation_text": "Late night pedestrian heard massive crash. A dark blue pickup truck was embedded in the display window. Three men in balaclavas were throwing trays into large bags.",
        "observed_entities": ["three masked individuals in balaclavas", "dark blue pickup truck"],
        "vehicle_description": "dark blue pickup truck",
        "direction_of_travel": "Fled into a black sedan waiting around the corner",
        "confidence_level": "HIGH",
        "related_incident_ids": [inc_ram],
        "contradiction_flags": [],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0015",
        "submitted_at": to_iso_utc(dt_ram + timedelta(hours=1)),
        "observed_from": to_iso_utc(dt_ram + timedelta(minutes=3)),
        "observed_to": to_iso_utc(dt_ram + timedelta(minutes=7)),
        "location_id": "LOC-CEN-03",
        "observation_text": "Taxi driver saw three men leap into a black sedan that ran a red light heading toward Riverside waterfront. Thought the pickup truck was black, not blue.",
        "observed_entities": ["three running men", "black getaway sedan"],
        "vehicle_description": "black Audi or BMW sedan",
        "direction_of_travel": "Southbound speeding towards Riverside waterfront",
        "confidence_level": "MEDIUM",
        "related_incident_ids": [inc_ram],
        "contradiction_flags": ["ram_truck_color_perceived_black_vs_blue"],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0020",
        "camera_id": "CAM-CEN-03-01",
        "location_id": "LOC-CEN-03",
        "recorded_from": to_iso_utc(dt_ram - timedelta(minutes=2)),
        "recorded_to": to_iso_utc(dt_ram + timedelta(minutes=8)),
        "observed_entities": ["Chevrolet Silverado pickup truck", "three perpetrators with sledgehammers", "jewelry trays"],
        "vehicle_description": "midnight dark blue Chevrolet Silverado pickup truck",
        "vehicle_color": "blue",
        "partial_plate": "5WY***",
        "movement_description": "Truck reversed at 20 mph through display facade; three masked subjects cleared front cases; abandoned truck idling; ran to corner",
        "image_quality": "CLEAR",
        "observation_confidence": 0.98,
        "related_incident_ids": [inc_ram],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0024",
        "camera_id": "CAM-CEN-03-03",
        "location_id": "LOC-CEN-03",
        "recorded_from": to_iso_utc(dt_ram + timedelta(minutes=2)),
        "recorded_to": to_iso_utc(dt_ram + timedelta(minutes=10)),
        "observed_entities": ["black sedan getaway car", "three passengers entering"],
        "vehicle_description": "black sedan with smoked license plate cover",
        "vehicle_color": "black",
        "partial_plate": null,
        "movement_description": "Black sedan accelerated rapidly south toward Riverside district line",
        "image_quality": "MODERATE",
        "observation_confidence": 0.84,
        "related_incident_ids": [inc_ram],
        "data_quality": "HIGH",
    })

    evd_ram1 = "EVD-2025-0010"
    evd_ram2 = "EVD-2025-0014"
    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0010",
        "incident_id": inc_ram,
        "evidence_item_id": evd_ram1,
        "collected_at": to_iso_utc(dt_ram + timedelta(hours=2)),
        "location_id": "LOC-CEN-03",
        "evidence_type": "CHEMICAL_RESIDUE",
        "description": "Paint smear transfer and shattered security glass analysis from arcade entry",
        "examination_method": "GC_MS",
        "result_summary": "Confirmed dark midnight blue OEM automotive acrylic enamel matching recovered Silverado tailgate",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [],
        "limitations": null,
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0014",
        "incident_id": inc_ram,
        "evidence_item_id": evd_ram2,
        "collected_at": to_iso_utc(dt_ram + timedelta(hours=3)),
        "location_id": "LOC-CEN-03",
        "evidence_type": "DNA",
        "description": "Biological epithelial swab lifted from deployed driver airbag and steering wheel of abandoned ramming truck",
        "examination_method": "STR_PROFILING",
        "result_summary": "Single source male DNA profile obtained with 16 complete STR loci",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [],
        "limitations": "No direct suspect reference profile match currently in local police index",
        "data_quality": "HIGH",
    })

    planted_records["newspaper_reports"].append({
        "news_id": "NEWS-0008",
        "publication_name": "The Daily Herald",
        "published_at": to_iso_utc(dt_ram + timedelta(hours=14)),
        "headline": "Midnight Ram-Raid Shatters Grand Avenue Luxury Arcade",
        "article_text": "A brazen three-minute heist saw a stolen pickup truck smash into Grand Avenue Luxury Jewellers. The perpetrators escaped in a high-powered black getaway car with hundreds of thousands in luxury timepieces.",
        "mentioned_date_from": to_iso_utc(dt_ram),
        "mentioned_date_to": to_iso_utc(dt_ram + timedelta(minutes=15)),
        "mentioned_location_ids": ["LOC-CEN-03"],
        "crime_labels": ["ROBBERY", "RAM_RAID"],
        "mentioned_property": ["luxury swiss watches", "diamond rings"],
        "related_incident_ids": [inc_ram],
        "source_reliability": "HIGH",
        "data_quality": "HIGH",
    })

    ground_truth.append({
        "relationship_id": "REL-CROSS-SINGLE-005",
        "title": "Comprehensive Multi-Source Investigation: Grand Avenue Jewellers Ram-Raid (Central)",
        "scenario_type": "MULTI_SOURCE_SINGLE_INCIDENT",
        "stations_involved": ["CENTRAL"],
        "incident_ids": [inc_ram],
        "source_record_ids": {
            "witness_reports": ["WIT-0012", "WIT-0015"],
            "cctv_reports": ["CCTV-0020", "CCTV-0024"],
            "forensic_reports": ["FOR-0010", "FOR-0014"],
            "newspaper_reports": ["NEWS-0008"],
        },
        "why_related": "All records corroborate different facets of the major smash-and-grab ram raid at Grand Avenue Luxury Jewellers on 2025-01-18.",
        "supporting_evidence": [
            "Synchronized chronological evidence spanning impact, escape, forensic DNA extraction, and public reporting",
            "CCTV-0020 captures impact and truck plate 5WY***; FOR-0010 chemical paint analysis verifies truck paint transfer",
            "FOR-0014 secures clean single-source male DNA profile from driver airbag",
        ],
        "contradictions_and_limitations": [
            "Witness WIT-0015 initially perceived the midnight blue truck as black due to dim arcade street lighting; CCTV-0020 and forensic paint confirmed dark blue",
            "Getaway black sedan utilized smoked plate cover obscuring registration",
        ],
        "confidence_label": "HIGH",
    })

    # 6. SCENARIO 6: Distractor / False Lead - Legitimate Commercial Plumber Van (CENTRAL)
    # Similar white utility van to Scenario 4, but forensically and temporally proven unrelated.
    inc_false1 = "INC-CEN-1680"
    dt_false1 = datetime(2025, 7, 26, 11, 0, 0, tzinfo=timezone.utc)

    planted_records["police_incidents"].append({
        "incident_id": inc_false1,
        "station_id": "CENTRAL",
        "reported_at": to_iso_utc(dt_false1 + timedelta(hours=1)),
        "occurred_from": to_iso_utc(dt_false1),
        "occurred_to": to_iso_utc(dt_false1 + timedelta(minutes=30)),
        "crime_type": "FRAUD",
        "location_id": "LOC-CEN-08",
        "location_description": "Midtown Commercial Hub, Suite 300",
        "method_description": "Suspicious person call regarding white van with ladders; tenant feared water utility impostor syndicate; verified as licensed municipal plumbing contractor responding to genuine pipe burst",
        "property_involved": [],
        "estimated_loss": null,
        "status": "CLOSED",
        "source_reference_ids": ["WIT-1620", "CCTV-1750", "FOR-1390"],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-1620",
        "submitted_at": to_iso_utc(dt_false1 + timedelta(minutes=45)),
        "observed_from": to_iso_utc(dt_false1),
        "observed_to": to_iso_utc(dt_false1 + timedelta(minutes=20)),
        "location_id": "LOC-CEN-08",
        "observation_text": "Anxious resident called dispatch believing the 'water inspector fraud gang' had arrived at Midtown Commercial Hub in a white van with ladders.",
        "observed_entities": ["white utility van", "two workers in safety jackets"],
        "vehicle_description": "white Ford van with ladder rack",
        "direction_of_travel": "Parked in service alley",
        "confidence_level": "LOW",
        "related_incident_ids": [inc_false1],
        "contradiction_flags": ["false_alarm_suspected_scam_actually_legitimate_plumber"],
        "data_quality": "MEDIUM",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-1750",
        "camera_id": "CAM-CEN-08-01",
        "location_id": "LOC-CEN-08",
        "recorded_from": to_iso_utc(dt_false1 - timedelta(minutes=5)),
        "recorded_to": to_iso_utc(dt_false1 + timedelta(minutes=35)),
        "observed_entities": ["white cargo van", "licensed contractor company logo 'Apex Municipal Plumbing LLC'"],
        "vehicle_description": "white commercial van with Apex Municipal Plumbing logo",
        "vehicle_color": "white",
        "partial_plate": "1PL***",
        "movement_description": "Van parked legitimately; workers offloaded copper pipe repair joints and commercial drainage pump; valid work order displayed on dashboard",
        "image_quality": "CLEAR",
        "observation_confidence": 0.96,
        "related_incident_ids": [inc_false1],
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-1390",
        "incident_id": inc_false1,
        "evidence_item_id": "EVD-2025-1390",
        "collected_at": to_iso_utc(dt_false1 + timedelta(hours=2)),
        "location_id": "LOC-CEN-08",
        "evidence_type": "TIRE_IMPRESSION",
        "description": "Tire tread impression cast from alley dust compared against suspect impostor van profile",
        "examination_method": "TREAD_PHOTOGRAMMETRY",
        "result_summary": "Tire tread is Michelin Agilis commercial rib pattern; completely excludes Firestone Transforce pattern used by impostor van in INC-NORTH-1104",
        "result_status": "EXCLUSION",
        "confidence_level": "HIGH",
        "compared_evidence_ids": ["EVD-2025-1025"],
        "limitations": "Incident confirmed non-criminal service call",
        "data_quality": "HIGH",
    })

    ground_truth.append({
        "relationship_id": "REL-DISTRACTOR-006",
        "title": "Known False Lead: Legitimate Commercial Plumber Excluded from Distraction Scam Ring",
        "scenario_type": "FALSE_LEAD_EXCLUSION",
        "stations_involved": ["CENTRAL"],
        "incident_ids": [inc_false1],
        "source_record_ids": {
            "witness_reports": ["WIT-1620"],
            "cctv_reports": ["CCTV-1750"],
            "forensic_reports": ["FOR-1390"],
            "newspaper_reports": [],
        },
        "why_related": "Reported as a potential continuation of the impostor water utility scam (REL-SERIES-004), but definitively proven to be a benign false alarm and investigative distractor.",
        "supporting_evidence": [
            "Forensic tire impression FOR-1390 confirms complete exclusion against suspect syndicate vehicle tread pattern",
            "CCTV-1750 reveals legitimate commercial business lettering ('Apex Municipal Plumbing LLC') and plate 1PL***",
            "Valid emergency municipal repair invoice verified by property manager",
        ],
        "contradictions_and_limitations": [
            "WIT-1620 filed report due to heightened public anxiety following newspaper coverage NEWS-0480",
        ],
        "confidence_label": "EXCLUSION",
    })

    # 7. SCENARIO 7: Dockside Pharmaceutical Cold-Storage Diversion (RIVERSIDE & CENTRAL)
    inc_pharma1 = "INC-RIV-0880"
    inc_pharma2 = "INC-CEN-1420"
    dt_pharma1 = datetime(2025, 9, 4, 22, 15, 0, tzinfo=timezone.utc)
    dt_pharma2 = datetime(2025, 9, 14, 21, 45, 0, tzinfo=timezone.utc)

    planted_records["police_incidents"].append({
        "incident_id": inc_pharma1,
        "station_id": "RIVERSIDE",
        "reported_at": to_iso_utc(dt_pharma1 + timedelta(hours=3)),
        "occurred_from": to_iso_utc(dt_pharma1),
        "occurred_to": to_iso_utc(dt_pharma1 + timedelta(minutes=50)),
        "crime_type": "CARGO_THEFT",
        "location_id": "LOC-RIV-09",
        "location_description": "Delta Cold Storage Facility, Gate 2",
        "method_description": "Forged digital bill of lading presented with stolen dispatch cryptographic token; fraudulent release of 4 refrigerated pallets of oncology medication",
        "property_involved": ["palletized oncology pharmaceuticals", "digital temperature monitoring loggers"],
        "estimated_loss": 520000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["WIT-1340", "CCTV-1420"],
        "data_quality": "HIGH",
    })

    planted_records["police_incidents"].append({
        "incident_id": inc_pharma2,
        "station_id": "CENTRAL",
        "reported_at": to_iso_utc(dt_pharma2 + timedelta(hours=2)),
        "occurred_from": to_iso_utc(dt_pharma2),
        "occurred_to": to_iso_utc(dt_pharma2 + timedelta(minutes=45)),
        "crime_type": "CARGO_THEFT",
        "location_id": "LOC-CEN-15",
        "location_description": "City Hall Annex Medical Supply, South Delivery Ramp",
        "method_description": "Identical fraudulent electronic consignment note used to divert high-potency biotherapeutic inventory into private refrigerated box truck",
        "property_involved": ["biotherapeutic refrigerated medication pallets"],
        "estimated_loss": 380000.0,
        "status": "UNDER_INVESTIGATION",
        "source_reference_ids": ["CCTV-1580"],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-1340",
        "submitted_at": to_iso_utc(dt_pharma1 + timedelta(hours=2)),
        "observed_from": to_iso_utc(dt_pharma1 + timedelta(minutes=15)),
        "observed_to": to_iso_utc(dt_pharma1 + timedelta(minutes=40)),
        "location_id": "LOC-RIV-09",
        "observation_text": "Cold storage dock worker noted that the driver's electronic paperwork had an outdated corporate header but valid cryptographic carrier seal. Box truck had a faded blue refrigeration unit.",
        "observed_entities": ["driver presenting electronic tablet", "refrigerated box truck"],
        "vehicle_description": "white box truck with faded blue refrigeration unit on roof",
        "direction_of_travel": "Headed toward Rivergate industrial bypass",
        "confidence_level": "HIGH",
        "related_incident_ids": [inc_pharma1],
        "contradiction_flags": [],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-1420",
        "camera_id": "CAM-RIV-09-01",
        "location_id": "LOC-RIV-09",
        "recorded_from": to_iso_utc(dt_pharma1),
        "recorded_to": to_iso_utc(dt_pharma1 + timedelta(minutes=55)),
        "observed_entities": ["refrigerated box truck", "dock forklift loading pallets"],
        "vehicle_description": "white Freightliner refrigerated box truck with blue chiller housing",
        "vehicle_color": "white",
        "partial_plate": "4NV***",
        "movement_description": "Refrigerated truck backed into Bay 4; four pallets loaded; departed westbound",
        "image_quality": "CLEAR",
        "observation_confidence": 0.92,
        "related_incident_ids": [inc_pharma1],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-1580",
        "camera_id": "CAM-CEN-15-02",
        "location_id": "LOC-CEN-15",
        "recorded_from": to_iso_utc(dt_pharma2),
        "recorded_to": to_iso_utc(dt_pharma2 + timedelta(minutes=50)),
        "observed_entities": ["white refrigerated box truck", "pallet loading"],
        "vehicle_description": "white box truck with blue chiller housing",
        "vehicle_color": "white",
        "partial_plate": "4NV***",
        "movement_description": "Truck reversed into delivery ramp; pallets transferred; departed south toward Riverside",
        "image_quality": "MODERATE",
        "observation_confidence": 0.85,
        "related_incident_ids": [inc_pharma2],
        "data_quality": "HIGH",
    })

    evd_pharma1 = "EVD-2025-1150"
    evd_pharma2 = "EVD-2025-1280"
    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-1150",
        "incident_id": inc_pharma1,
        "evidence_item_id": evd_pharma1,
        "collected_at": to_iso_utc(dt_pharma1 + timedelta(hours=5)),
        "location_id": "LOC-RIV-09",
        "evidence_type": "DIGITAL_FOOTPRINT",
        "description": "Cryptographic dispatch manifest metadata and counterfeit digital dispatch stamp hash",
        "examination_method": "LOG_AND_SIGNAL_ANALYSIS",
        "result_summary": "Extracted SHA-256 digital dispatch signature matches compromised private key leaked from regional logistics wholesaler",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_pharma2],
        "limitations": null,
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-1280",
        "incident_id": inc_pharma2,
        "evidence_item_id": evd_pharma2,
        "collected_at": to_iso_utc(dt_pharma2 + timedelta(hours=4)),
        "location_id": "LOC-CEN-15",
        "evidence_type": "DIGITAL_FOOTPRINT",
        "description": "Electronic bill of lading verification log from Central distribution facility",
        "examination_method": "LOG_AND_SIGNAL_ANALYSIS",
        "result_summary": "Identical compromised carrier signature hash and authorization token reused, confirming same perpetrator group",
        "result_status": "MATCH_CONFIRMED",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_pharma1],
        "limitations": null,
        "data_quality": "HIGH",
    })

    planted_records["newspaper_reports"].append({
        "news_id": "NEWS-0620",
        "publication_name": "Riverside Wharf News",
        "published_at": to_iso_utc(dt_pharma2 + timedelta(days=2)),
        "headline": "High-Value Pharmaceutical Cargo Siphoned in Coordinated Freight Fraud",
        "article_text": "Detectives from Riverside and Central are tracking an organized cargo ring utilizing forged electronic bills of lading to divert sensitive cold-storage medications from authorized distribution hubs.",
        "mentioned_date_from": to_iso_utc(dt_pharma1),
        "mentioned_date_to": to_iso_utc(dt_pharma2),
        "mentioned_location_ids": ["LOC-RIV-09", "LOC-CEN-15"],
        "crime_labels": ["CARGO_THEFT", "FRAUD"],
        "mentioned_property": ["oncology pharmaceuticals", "biotherapeutics"],
        "related_incident_ids": [inc_pharma1, inc_pharma2],
        "source_reliability": "HIGH",
        "data_quality": "HIGH",
    })

    ground_truth.append({
        "relationship_id": "REL-SERIES-007",
        "title": "Cross-Station Pharmaceutical Cold-Storage Diversion Ring (Riverside & Central)",
        "scenario_type": "ORGANIZED_CARGO_FRAUD",
        "stations_involved": ["RIVERSIDE", "CENTRAL"],
        "incident_ids": [inc_pharma1, inc_pharma2],
        "source_record_ids": {
            "witness_reports": ["WIT-1340"],
            "cctv_reports": ["CCTV-1420", "CCTV-1580"],
            "forensic_reports": ["FOR-1150", "FOR-1280"],
            "newspaper_reports": ["NEWS-0620"],
        },
        "why_related": "Cargo theft ring utilizing compromised electronic shipping manifests and a white refrigerated Freightliner box truck (partial plate 4NV***) with blue chiller housing across Riverside and Central hubs.",
        "supporting_evidence": [
            "Forensic digital signature hash match confirms identical compromised cryptographic key used in FOR-1150 and FOR-1280",
            "CCTV-1420 and CCTV-1580 identify the same refrigerated truck with distinctive blue rooftop chiller and plate 4NV***",
            "Matching target cargo: multi-pallet refrigerated high-value pharmaceuticals",
        ],
        "contradictions_and_limitations": [
            "Outdated corporate header on manifest noted by dock worker was initially dismissed as standard clerical lag",
        ],
        "confidence_label": "HIGH",
    })

    # 8. SCENARIO 8: Distractor / False Lead - Amateur Opportunistic Smash-and-Grab (NORTH)
    # Similar location and target property type to Crowbar Syndicate (Scenario 1), but completely distinct MO and DNA.
    inc_copycat = "INC-NORTH-0520"
    dt_copycat = datetime(2025, 2, 28, 1, 40, 0, tzinfo=timezone.utc)

    planted_records["police_incidents"].append({
        "incident_id": inc_copycat,
        "station_id": "NORTH",
        "reported_at": to_iso_utc(dt_copycat + timedelta(minutes=15)),
        "occurred_from": to_iso_utc(dt_copycat),
        "occurred_to": to_iso_utc(dt_copycat + timedelta(minutes=5)),
        "crime_type": "BURGLARY",
        "location_id": "LOC-NORTH-04",
        "location_description": "North Ridge Shopping Plaza, Unit 12 electronics shop",
        "method_description": "Concrete cinder block thrown through front plate glass window; solitary individual grabbed display model phones and fled on foot; blood droplets left on broken glass",
        "property_involved": ["dummy display cell phones", "store tablet"],
        "estimated_loss": 1200.0,
        "status": "CLOSED",
        "source_reference_ids": ["WIT-0510", "CCTV-0540", "FOR-0460"],
        "data_quality": "HIGH",
    })

    planted_records["witness_reports"].append({
        "witness_report_id": "WIT-0510",
        "submitted_at": to_iso_utc(dt_copycat + timedelta(minutes=30)),
        "observed_from": to_iso_utc(dt_copycat),
        "observed_to": to_iso_utc(dt_copycat + timedelta(minutes=4)),
        "location_id": "LOC-NORTH-04",
        "observation_text": "Pedestrian heard glass crash. Saw a solitary teenager running on foot clutching dummy electronics. No getaway vehicle present.",
        "observed_entities": ["lone male teenager running on foot"],
        "vehicle_description": null,
        "direction_of_travel": "Fled on foot into adjoining residential neighborhood",
        "confidence_level": "HIGH",
        "related_incident_ids": [inc_copycat],
        "contradiction_flags": [],
        "data_quality": "HIGH",
    })

    planted_records["cctv_reports"].append({
        "cctv_report_id": "CCTV-0540",
        "camera_id": "CAM-NORTH-04-01",
        "location_id": "LOC-NORTH-04",
        "recorded_from": to_iso_utc(dt_copycat - timedelta(minutes=2)),
        "recorded_to": to_iso_utc(dt_copycat + timedelta(minutes=6)),
        "observed_entities": ["lone male subject in hoodie", "concrete block"],
        "vehicle_description": null,
        "vehicle_color": null,
        "partial_plate": null,
        "movement_description": "Individual hurled cinder block through front window; grabbed tethered display dummy phones; cut hand on glass; fled on foot",
        "image_quality": "CLEAR",
        "observation_confidence": 0.95,
        "related_incident_ids": [inc_copycat],
        "data_quality": "HIGH",
    })

    planted_records["forensic_reports"].append({
        "evidence_report_id": "FOR-0460",
        "incident_id": inc_copycat,
        "evidence_item_id": "EVD-2025-0460",
        "collected_at": to_iso_utc(dt_copycat + timedelta(hours=1)),
        "location_id": "LOC-NORTH-04",
        "evidence_type": "DNA",
        "description": "Blood swab collected from jagged shards of broken storefront glass",
        "examination_method": "STR_PROFILING",
        "result_summary": "Single male DNA profile matching local juvenile offender; completely non-matching against syndicate biological and toolmark profiles",
        "result_status": "EXCLUSION",
        "confidence_level": "HIGH",
        "compared_evidence_ids": [evd_1],
        "limitations": "Individual admitted solo opportunistic crime",
        "data_quality": "HIGH",
    })

    planted_records["newspaper_reports"].append({
        "news_id": "NEWS-0260",
        "publication_name": "Northern Courier",
        "published_at": to_iso_utc(dt_copycat + timedelta(days=1)),
        "headline": "North Plaza Electronics Store Vandalized in Midnight Smash-and-Grab",
        "article_text": "An opportunistic burglar smashed a display window at North Ridge Shopping Plaza, making off with dummy display units before fleeing on foot.",
        "mentioned_date_from": to_iso_utc(dt_copycat),
        "mentioned_date_to": to_iso_utc(dt_copycat + timedelta(minutes=10)),
        "mentioned_location_ids": ["LOC-NORTH-04"],
        "crime_labels": ["BURGLARY", "VANDALISM"],
        "mentioned_property": ["dummy display phones"],
        "related_incident_ids": [inc_copycat],
        "source_reliability": "HIGH",
        "data_quality": "HIGH",
    })

    ground_truth.append({
        "relationship_id": "REL-DISTRACTOR-008",
        "title": "Known False Lead: Opportunistic Juvenile Smash-and-Grab Excluded from Safe Burglary Syndicate",
        "scenario_type": "FALSE_LEAD_EXCLUSION",
        "stations_involved": ["NORTH"],
        "incident_ids": [inc_copycat],
        "source_record_ids": {
            "witness_reports": ["WIT-0510"],
            "cctv_reports": ["CCTV-0540"],
            "forensic_reports": ["FOR-0460"],
            "newspaper_reports": ["NEWS-0260"],
        },
        "why_related": "Occurred within the North precinct during the active period of REL-SERIES-001, but represents an unrelated, opportunistic solo juvenile smash-and-grab.",
        "supporting_evidence": [
            "Forensic DNA report FOR-0460 directly identifies local juvenile offender, excluding professional syndicate",
            "CCTV-0540 confirms thrown cinder block MO with no pry tools or getaway vehicle used",
            "Targeted items were dummy display phones rather than heavy safes",
        ],
        "contradictions_and_limitations": [
            "Superficial geographic proximity and business category initially triggered cross-indexing in police blotter",
        ],
        "confidence_label": "EXCLUSION",
    })

    return ground_truth, planted_records


def generate_background_records(
    planted_records: Dict[str, List[Dict[str, Any]]],
    target_counts: Dict[str, int],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates realistic, varied, non-trivial background records to achieve
    exact target counts across all 5 JSON files.
    """
    records = {k: list(v) for k, v in planted_records.items()}

    # 1. Background Police Incidents
    needed_incidents = target_counts["police_incidents"] - len(records["police_incidents"])
    inc_counter = 1

    existing_incident_ids = {r["incident_id"] for r in records["police_incidents"]}

    for _ in range(needed_incidents):
        while True:
            station = random.choice(STATIONS)
            inc_id = f"INC-{station}-{inc_counter:04d}"
            inc_counter += 1
            if inc_id not in existing_incident_ids:
                existing_incident_ids.add(inc_id)
                break

        crime_type = random.choice(CRIME_TYPES)
        station_locs = LOCATIONS[station]
        loc_id, loc_desc = random.choice(station_locs)

        occ_from = random_date_between(BASE_START_TIME, BASE_END_TIME)
        has_occ_to = random.random() < 0.75
        occ_to = (occ_from + timedelta(minutes=random.randint(15, 360))) if has_occ_to else None

        rep_at = (occ_to or occ_from) + timedelta(minutes=random.randint(10, 1440))

        methods_list = METHODS.get(crime_type, ["Unspecified criminal methodology"])
        method = random.choice(methods_list)

        props_list = PROPERTIES.get(crime_type, [["personal belongings"]])
        prop = list(random.choice(props_list))

        has_loss = crime_type not in ["VANDALISM", "PROPERTY_DAMAGE"] or random.random() < 0.6
        loss = round(random.uniform(150.0, 45000.0), 2) if has_loss else None

        status = random.choice(["OPEN", "UNDER_INVESTIGATION", "CLOSED", "UNRESOLVED"])
        quality = random.choices(["HIGH", "MEDIUM", "LOW"], weights=[0.5, 0.35, 0.15])[0]

        records["police_incidents"].append({
            "incident_id": inc_id,
            "station_id": station,
            "reported_at": to_iso_utc(rep_at),
            "occurred_from": to_iso_utc(occ_from),
            "occurred_to": to_iso_utc(occ_to),
            "crime_type": crime_type,
            "location_id": loc_id,
            "location_description": loc_desc,
            "method_description": method,
            "property_involved": prop,
            "estimated_loss": loss,
            "status": status,
            "source_reference_ids": [],
            "data_quality": quality,
        })

    # Sort police incidents deterministically by reported_at
    records["police_incidents"].sort(key=lambda x: x["reported_at"])

    # 2. Background Newspaper Reports
    needed_news = target_counts["newspaper_reports"] - len(records["newspaper_reports"])
    existing_news_ids = {r["news_id"] for r in records["newspaper_reports"]}
    all_police_incidents = records["police_incidents"]

    news_counter = 1
    for _ in range(needed_news):
        while True:
            news_id = f"NEWS-{news_counter:04d}"
            news_counter += 1
            if news_id not in existing_news_ids:
                existing_news_ids.add(news_id)
                break

        pub_name, default_rel = random.choice(NEWSPAPERS)
        # Select an incident to report on, or generic blotter
        reports_on_incident = random.random() < 0.65
        if reports_on_incident:
            inc = random.choice(all_police_incidents)
            inc_dt = datetime.fromisoformat(inc["occurred_from"].replace("Z", "+00:00"))
            pub_dt = inc_dt + timedelta(days=random.randint(1, 5), hours=random.randint(1, 12))
            loc_ids = [inc["location_id"]]
            labels = [inc["crime_type"]]
            prop = list(inc["property_involved"])
            related_ids = [inc["incident_id"]] if random.random() < 0.55 else []
            headline = f"{inc['crime_type'].replace('_', ' ').title()} Reported Near {LOCATION_MAP[inc['location_id']].split(',')[0]}"
            text = (
                f"Authorities are investigating a {inc['crime_type'].lower()} incident occurring near "
                f"{LOCATION_MAP[inc['location_id']]}. Initial reports indicate {inc['method_description'].lower()}. "
                f"Police have urged anyone with information to contact local precinct detectives."
            )
            date_from = inc["occurred_from"]
            date_to = inc["occurred_to"]
        else:
            pub_dt = random_date_between(BASE_START_TIME + timedelta(days=4), BASE_END_TIME)
            loc_id, loc_desc = random.choice(ALL_LOCATIONS)
            c_type = random.choice(CRIME_TYPES)
            loc_ids = [loc_id]
            labels = [c_type, "PUBLIC_SAFETY"]
            prop = []
            related_ids = []
            headline = f"Residents Voice Concern Over Neighborhood Safety Near {loc_desc.split(',')[0]}"
            text = (
                f"Community members gathered this week to discuss regional safety and property protection "
                f"in the vicinity of {loc_desc}. Local officials pledged increased patrol visibility and coordinated security reviews."
            )
            date_from = to_iso_utc(max(BASE_START_TIME, pub_dt - timedelta(days=3)))
            date_to = to_iso_utc(pub_dt)

        quality = random.choices(["HIGH", "MEDIUM", "LOW"], weights=[0.55, 0.35, 0.10])[0]

        records["newspaper_reports"].append({
            "news_id": news_id,
            "publication_name": pub_name,
            "published_at": to_iso_utc(pub_dt),
            "headline": headline,
            "article_text": text,
            "mentioned_date_from": date_from,
            "mentioned_date_to": date_to,
            "mentioned_location_ids": loc_ids,
            "crime_labels": labels,
            "mentioned_property": prop,
            "related_incident_ids": related_ids,
            "source_reliability": default_rel,
            "data_quality": quality,
        })

    records["newspaper_reports"].sort(key=lambda x: x["published_at"])

    # 3. Background Witness Reports
    needed_witness = target_counts["witness_reports"] - len(records["witness_reports"])
    existing_wit_ids = {r["witness_report_id"] for r in records["witness_reports"]}
    wit_counter = 1

    DIRECTIONS = [
        "Northbound on main arterial road",
        "Headed south toward expressway on-ramp",
        "Westbound into commercial alleyway",
        "East toward transit station plaza",
        "Fled on foot toward residential park",
        "Departed along waterfront access road",
        null,
    ]

    for _ in range(needed_witness):
        while True:
            wit_id = f"WIT-{wit_counter:04d}"
            wit_counter += 1
            if wit_id not in existing_wit_ids:
                existing_wit_ids.add(wit_id)
                break

        links_to_incident = random.random() < 0.60
        if links_to_incident:
            inc = random.choice(all_police_incidents)
            inc_dt = datetime.fromisoformat(inc["occurred_from"].replace("Z", "+00:00"))
            obs_from = inc_dt + timedelta(minutes=random.randint(-10, 15))
            obs_to = obs_from + timedelta(minutes=random.randint(5, 30)) if random.random() < 0.7 else None
            sub_at = (obs_to or obs_from) + timedelta(minutes=random.randint(30, 2880))
            loc_id = inc["location_id"]
            related_ids = [inc["incident_id"]] if random.random() < 0.65 else []
        else:
            obs_from = random_date_between(BASE_START_TIME, BASE_END_TIME)
            obs_to = obs_from + timedelta(minutes=random.randint(5, 45)) if random.random() < 0.7 else None
            sub_at = (obs_to or obs_from) + timedelta(minutes=random.randint(30, 2880))
            loc_id, _ = random.choice(ALL_LOCATIONS)
            related_ids = []

        has_vehicle = random.random() < 0.55
        if has_vehicle:
            veh_info = random.choice(VEHICLES)
            veh_desc = veh_info[0]
        else:
            veh_desc = null

        has_entities = random.random() < 0.85
        entities = random.sample([
            "individual in dark hooded sweatshirt",
            "tall male wearing high-visibility vest",
            "second person carrying large black duffle bag",
            "person wearing medical face mask and gloves",
            "two individuals conversing near vehicle trunk",
            "lone cyclist circling parking structure",
        ], k=random.randint(1, 3)) if has_entities else []

        conf = random.choices(["HIGH", "MEDIUM", "LOW", "UNCERTAIN"], weights=[0.4, 0.35, 0.15, 0.1])[0]
        contra = []
        if conf in ["LOW", "UNCERTAIN"] and random.random() < 0.4:
            contra.append(random.choice([
                "disputes_suspect_count",
                "inconsistent_observation_time",
                "divergent_vehicle_description",
                "poor_illumination_uncertainty",
            ]))

        text = (
            f"Witness observed activity near {LOCATION_MAP[loc_id]}. "
            f"{'Entities noted: ' + ', '.join(entities) + '. ' if entities else ''}"
            f"{'Vehicle noted: ' + veh_desc + '. ' if veh_desc else ''}"
            f"Witness felt circumstances were suspicious and notified law enforcement."
        )

        quality = random.choices(["HIGH", "MEDIUM", "LOW"], weights=[0.45, 0.4, 0.15])[0]

        records["witness_reports"].append({
            "witness_report_id": wit_id,
            "submitted_at": to_iso_utc(sub_at),
            "observed_from": to_iso_utc(obs_from),
            "observed_to": to_iso_utc(obs_to),
            "location_id": loc_id,
            "observation_text": text,
            "observed_entities": entities,
            "vehicle_description": veh_desc,
            "direction_of_travel": random.choice(DIRECTIONS),
            "confidence_level": conf,
            "related_incident_ids": related_ids,
            "contradiction_flags": contra,
            "data_quality": quality,
        })

    records["witness_reports"].sort(key=lambda x: x["submitted_at"])

    # 4. Background CCTV Reports
    needed_cctv = target_counts["cctv_reports"] - len(records["cctv_reports"])
    existing_cctv_ids = {r["cctv_report_id"] for r in records["cctv_reports"]}
    cctv_counter = 1

    IMAGE_QUALITIES = ["CLEAR", "MODERATE", "DEGRADED", "NIGHT_IR_LOW_RES", "PARTIAL_GLARE", "POOR"]

    for _ in range(needed_cctv):
        while True:
            cctv_id = f"CCTV-{cctv_counter:04d}"
            cctv_counter += 1
            if cctv_id not in existing_cctv_ids:
                existing_cctv_ids.add(cctv_id)
                break

        links_to_incident = random.random() < 0.55
        if links_to_incident:
            inc = random.choice(all_police_incidents)
            inc_dt = datetime.fromisoformat(inc["occurred_from"].replace("Z", "+00:00"))
            rec_from = inc_dt - timedelta(minutes=random.randint(5, 15))
            rec_to = rec_from + timedelta(minutes=random.randint(15, 60))
            loc_id = inc["location_id"]
            related_ids = [inc["incident_id"]] if random.random() < 0.60 else []
        else:
            rec_from = random_date_between(BASE_START_TIME, BASE_END_TIME)
            rec_to = rec_from + timedelta(minutes=random.randint(10, 90))
            loc_id, _ = random.choice(ALL_LOCATIONS)
            related_ids = []

        cams = CAMERAS_BY_LOCATION.get(loc_id, [f"CAM-{loc_id}-01"])
        cam_id = random.choice(cams)

        has_veh = random.random() < 0.6
        if has_veh:
            veh = random.choice(VEHICLES)
            v_desc = veh[0]
            v_color = veh[1]
            plate = veh[2] if random.random() < 0.7 else null
        else:
            v_desc = null
            v_color = null
            plate = null

        entities = random.sample([
            "motor vehicle entering monitored perimeter",
            "individual loitering near service entryway",
            "two subjects in hooded jackets",
            "pedestrian carrying package",
            "commercial delivery vehicle idling",
            "bicycle crossing frame",
        ], k=random.randint(1, 2))

        movement = random.choice([
            "Subject approached facility perimeter, inspected door latch, and departed frame",
            "Vehicle paused adjacent to loading dock, executed U-turn, and exited field of view",
            "Two individuals traversed camera zone carrying equipment; disappeared into service corridor",
            "Continuous movement observed along monitored walkway during late evening interval",
            "Rapid departure recorded following trigger event; accelerated toward boundary avenue",
        ])

        img_qual = random.choices(IMAGE_QUALITIES, weights=[0.35, 0.30, 0.15, 0.10, 0.05, 0.05])[0]
        # Algorithmic observation confidence based on image quality
        base_conf = {
            "CLEAR": (0.85, 0.99),
            "MODERATE": (0.70, 0.88),
            "DEGRADED": (0.45, 0.72),
            "NIGHT_IR_LOW_RES": (0.40, 0.68),
            "PARTIAL_GLARE": (0.35, 0.60),
            "POOR": (0.20, 0.45),
        }[img_qual]
        obs_conf = round(random.uniform(base_conf[0], base_conf[1]), 2)
        quality = random.choices(["HIGH", "MEDIUM", "LOW"], weights=[0.45, 0.40, 0.15])[0]

        records["cctv_reports"].append({
            "cctv_report_id": cctv_id,
            "camera_id": cam_id,
            "location_id": loc_id,
            "recorded_from": to_iso_utc(rec_from),
            "recorded_to": to_iso_utc(rec_to),
            "observed_entities": entities,
            "vehicle_description": v_desc,
            "vehicle_color": v_color,
            "partial_plate": plate,
            "movement_description": movement,
            "image_quality": img_qual,
            "observation_confidence": obs_conf,
            "related_incident_ids": related_ids,
            "data_quality": quality,
        })

    records["cctv_reports"].sort(key=lambda x: x["recorded_from"])

    # 5. Background Forensic Reports
    needed_forensic = target_counts["forensic_reports"] - len(records["forensic_reports"])
    existing_for_ids = {r["evidence_report_id"] for r in records["forensic_reports"]}
    for_counter = 1

    RESULT_STATUSES = ["MATCH_CONFIRMED", "INCONCLUSIVE", "EXCLUSION", "PENDING_REFERENCE", "PARTIAL_MATCH"]
    EVIDENCE_TYPES = list(FORENSIC_METHODS.keys())

    for _ in range(needed_forensic):
        while True:
            for_id = f"FOR-{for_counter:04d}"
            evd_id = f"EVD-{for_counter:04d}"
            for_counter += 1
            if for_id not in existing_for_ids:
                existing_for_ids.add(for_id)
                break

        links_to_incident = random.random() < 0.70
        if links_to_incident:
            inc = random.choice(all_police_incidents)
            inc_dt = datetime.fromisoformat(inc["occurred_from"].replace("Z", "+00:00"))
            coll_at = inc_dt + timedelta(hours=random.randint(2, 72))
            loc_id = inc["location_id"]
            inc_id = inc["incident_id"]
        else:
            coll_at = random_date_between(BASE_START_TIME, BASE_END_TIME)
            loc_id, _ = random.choice(ALL_LOCATIONS)
            inc_id = null

        ev_type = random.choice(EVIDENCE_TYPES)
        method_name, method_desc = FORENSIC_METHODS[ev_type]

        status = random.choices(RESULT_STATUSES, weights=[0.4, 0.25, 0.15, 0.15, 0.05])[0]
        conf = {
            "MATCH_CONFIRMED": "HIGH",
            "INCONCLUSIVE": "INCONCLUSIVE",
            "EXCLUSION": "HIGH",
            "PENDING_REFERENCE": "LOW",
            "PARTIAL_MATCH": "MEDIUM",
        }[status]

        has_limitations = status in ["INCONCLUSIVE", "PARTIAL_MATCH", "PENDING_REFERENCE"] or random.random() < 0.2
        limitations = (
            random.choice([
                "Degraded substrate compromised latent detail",
                "Partial sample insufficient for full allelic locus ladder",
                "Awaiting submission of suspect reference exemplar standard",
                "Atmospheric weathering reduced recoverable chemical peaks",
                "Superficial smudging obscured secondary minutiae ridge terminations",
            ])
            if has_limitations
            else null
        )

        desc = f"Physical evidence item ({ev_type.lower().replace('_', ' ')}) collected from scene at {LOCATION_MAP[loc_id]}."
        summary = (
            f"Laboratory examination conducted via {method_desc}. "
            f"Evaluation determined findings consistent with status {status.replace('_', ' ').lower()}."
        )

        quality = random.choices(["HIGH", "MEDIUM", "LOW"], weights=[0.55, 0.35, 0.10])[0]

        records["forensic_reports"].append({
            "evidence_report_id": for_id,
            "incident_id": inc_id,
            "evidence_item_id": evd_id,
            "collected_at": to_iso_utc(coll_at),
            "location_id": loc_id,
            "evidence_type": ev_type,
            "description": desc,
            "examination_method": method_name,
            "result_summary": summary,
            "result_status": status,
            "confidence_level": conf,
            "compared_evidence_ids": [],
            "limitations": limitations,
            "data_quality": quality,
        })

    records["forensic_reports"].sort(key=lambda x: x["collected_at"])

    return records


def write_json_file(file_path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_all(seed: int = RANDOM_SEED) -> Dict[str, Any]:
    print(f"[*] Initializing random generator with seed {seed}...")
    random.seed(seed)

    print("[*] Generating planted scenarios and offline ground truth...")
    ground_truth, planted_records = create_planted_scenarios()

    print("[*] Generating realistic background records to reach exact quotas...")
    all_records = generate_background_records(planted_records, TARGET_COUNTS)

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_gen_dir = os.path.join(base_dir, "data", "generated")
    data_eval_dir = os.path.join(base_dir, "data", "evaluation")

    files_to_write = {
        os.path.join(data_gen_dir, "police_incidents.json"): all_records["police_incidents"],
        os.path.join(data_gen_dir, "newspaper_reports.json"): all_records["newspaper_reports"],
        os.path.join(data_gen_dir, "witness_reports.json"): all_records["witness_reports"],
        os.path.join(data_gen_dir, "cctv_reports.json"): all_records["cctv_reports"],
        os.path.join(data_gen_dir, "forensic_reports.json"): all_records["forensic_reports"],
        os.path.join(data_eval_dir, "ground_truth.json"): ground_truth,
    }

    for path, data in files_to_write.items():
        print(f"[*] Writing {len(data) if isinstance(data, list) else 'N/A'} records to {os.path.relpath(path, base_dir)}...")
        write_json_file(path, data)

    total_records = sum(len(all_records[k]) for k in TARGET_COUNTS)
    print(f"\n[+] Successfully generated exactly {total_records} records across 5 primary datasets!")
    print(f"[+] Ground truth planted scenarios generated: {len(ground_truth)} scenarios.")

    return {
        "record_counts": {k: len(all_records[k]) for k in TARGET_COUNTS},
        "total_records": total_records,
        "ground_truth_scenarios": len(ground_truth),
    }


if __name__ == "__main__":
    generate_all()
