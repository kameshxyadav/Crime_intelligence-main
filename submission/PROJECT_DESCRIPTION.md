# Project Name, One-liner, Descriptions

## Project name
Cross-Station Crime Intelligence

## One-liner
A multi-agent system that links crimes across police stations, and lets a Skeptic agent and deterministic code try to break every link before an officer sees it.

## Short description
Crime data is split across stations and across five record types: incident reports, forensics, CCTV, witness statements and press. Cross-Station Crime Intelligence queries all five through Zetaris, has Nemotron agents propose links between incidents in different stations, then attacks each link with a Skeptic agent and a Python verifier. Officers get cited, auditable leads. Decoys and contradictions are shown, not hidden.

## Long description
A burglar who hits a warehouse in one precinct and a jeweller in another leaves clues scattered across systems that do not talk to each other: a toolmark in a lab report, a partial plate on a CCTV clip, a witness who saw a van. Most of those records carry no explicit link.

Cross-Station Crime Intelligence federates five sources (police incidents, forensic reports, CCTV reports, witness reports, newspaper reports) through Zetaris NDP, with no ETL copy. Over three fictional precincts we load 10,000 synthetic records with planted crime series, contradictory witnesses and decoys.

An investigation runs as a bounded loop:
1. A **Planner** (Nemotron 3.5 Lightning 30B) decides what to retrieve.
2. Code (not a model) runs read-only SQL against Zetaris.
3. A **Finder** proposes candidate links with shared attributes, differences and missing evidence.
4. A **deterministic verifier** checks that every cited ID exists, quotes are verbatim, claimed attributes appear in records tied to both incidents, and that duplicate reports (same camera window, news about a police-recorded incident) are not counted as independent corroboration.
5. A **Skeptic** (Nemotron 3 Ultra 550B) attacks the links without seeing the Finder's score, and can ask for more retrieval.
6. A **Reporter** writes only from validated state, and its citations are re-checked.

Four Meterless engines support this: World Model holds shared state, H-MEM keeps vetted summaries as context only, Scout Intent screens each request, and Markovian bounds and resumes the run. Every model call goes through Nightshift, and each is recorded with the model that actually answered.

The result is a dossier an officer can audit: each link is labelled SUPPORTED, WEAK or UNSUPPORTED, forensic exclusions and witness conflicts stay visible, and scores are labelled as uncalibrated heuristics. The system links incidents; it never scores people and never decides guilt. The UI adds a role-based "One OS" (citizen, officer, analyst, chief), a station-correlation map, and an anonymous citizen tip portal with client-side EXIF/GPS stripping and prompt-injection screening.
