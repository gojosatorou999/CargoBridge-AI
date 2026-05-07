"""
CargoBridge AI — CrewAI Multi-Agent Pipeline
=============================================
Three specialised agents work sequentially to analyse, validate, and score
every disruption report before it hits the verification queue.

Pipeline:
  1. DisruptionAnalystAgent   → Extracts structured facts from free-text
  2. WeatherAISValidatorAgent → Cross-checks facts against live sensor data
  3. ConfidenceScorerAgent    → Merges both analyses into a 0-100 score + reason

Usage:
    from cargo_crew import score_disruption_with_crew
    result = score_disruption_with_crew(report_text, context_dict)
    # result == {"score": int, "reason": str, "validation": str, "facts": dict}

The module degrades gracefully: if OPENAI_API_KEY is missing or CrewAI
raises an error, it returns None so the caller can fall back to the
deterministic expert_system.py scorer.
"""

import os
import json
import logging
import re

logger = logging.getLogger(__name__)

# ── CrewAI is optional — graceful import ──────────────────────────────────────

try:
    from crewai import Agent, Task, Crew, Process
    from crewai_tools import SerperDevTool
    _CREWAI_AVAILABLE = True
except Exception as _crew_import_error:
    _CREWAI_AVAILABLE = False
    logger.warning(
        "CrewAI could not be loaded (%s: %s). "
        "This is usually a Python version / pydantic compatibility issue. "
        "CrewAI requires Python <=3.12 and langchain 0.1.x. "
        "To enable the AI Crew pipeline: use Python 3.11-3.12, then run: "
        "pip install crewai crewai-tools langchain-openai  "
        "Falling back to the built-in expert_system scorer.",
        type(_crew_import_error).__name__, _crew_import_error,
    )


def _crewai_ready() -> bool:
    """Returns True only when both the library and an API key are present."""
    return _CREWAI_AVAILABLE and bool(os.environ.get("OPENAI_API_KEY"))


# ── Agent definitions (created lazily so imports never block startup) ─────────

def _build_agents():
    """Instantiate and return (reader, validator, scorer) agents."""

    reader = Agent(
        role="Disruption Analyst",
        goal=(
            "Extract key structured facts from a raw disruption report. "
            "Identify: disruption type, exact location, estimated severity (low/medium/high), "
            "and any timing details. Return strict JSON."
        ),
        backstory=(
            "You are a senior logistics incident analyst with 15 years parsing port "
            "disruption reports for DP World and JNPT. You never embellish — only extract "
            "what is explicitly stated or strongly implied in the report text."
        ),
        verbose=True,
        allow_delegation=False,
    )

    # Serper web search lets the validator look up live weather headlines and
    # port notices — purely supplementary, not a hard dependency.
    tools = []
    if os.environ.get("SERPER_API_KEY"):
        try:
            tools = [SerperDevTool()]
        except Exception:
            pass  # continue without web search

    validator = Agent(
        role="Weather & AIS Validator",
        goal=(
            "Cross-check the extracted disruption facts against the live weather "
            "snapshot, AIS vessel data, and historical patterns. "
            "Return: 'confirmed', 'partial', or 'unconfirmed' with a one-sentence rationale."
        ),
        backstory=(
            "You are a maritime intelligence officer who fuses real-time weather feeds "
            "and AIS vessel tracking data to verify whether reported port disruptions "
            "are supported by objective sensor readings."
        ),
        tools=tools,
        verbose=True,
        allow_delegation=False,
    )

    scorer = Agent(
        role="Confidence Scorer",
        goal=(
            "Combine the disruption facts and validation verdict into a final "
            "confidence score (0–100) and a concise reason string. "
            "Output strict JSON: {\"score\": <int>, \"reason\": <str>}."
        ),
        backstory=(
            "You are a quantitative risk analyst who has calibrated confidence models "
            "on thousands of historical port disruption outcomes. "
            "Score 85-100 = Highly Reliable, 60-84 = Good, 40-59 = Questionable, "
            "0-39 = Low Confidence. Always justify with specific evidence."
        ),
        verbose=True,
        allow_delegation=False,
    )

    return reader, validator, scorer


# ── Context serialiser ────────────────────────────────────────────────────────

def _build_context_summary(context: dict) -> str:
    """Convert the sensor-data context dict into a readable string for agents."""
    lines = []

    weather = context.get("weather")
    if weather:
        lines.append(
            f"Weather snapshot: temp={weather.get('temp_c', 'N/A')}°C, "
            f"wind={weather.get('wind_speed_kmh', 'N/A')} km/h, "
            f"wave_height={weather.get('wave_height_m', 'N/A')} m, "
            f"code={weather.get('weather_code', 'N/A')}"
        )
    else:
        lines.append("Weather snapshot: not available")

    ais_vessels = context.get("ais_vessels", [])
    if ais_vessels:
        lines.append(f"AIS data: {len(ais_vessels)} vessels currently tracked in the area.")
        for v in ais_vessels[:3]:  # show first 3 to keep prompt short
            lines.append(
                f"  • {v.get('vessel_name', 'Unknown')} — dest: {v.get('destination_port', '?')}, "
                f"speed: {v.get('speed_knots', '?')} knots"
            )
    else:
        lines.append("AIS data: no vessels currently tracked.")

    nearby_count = context.get("nearby_similar_reports", 0)
    lines.append(f"Spatial corroboration: {nearby_count} similar report(s) within 5 km in the last 24 h.")

    reporter_role = context.get("reporter_role", "unknown")
    approval_rate = context.get("reporter_approval_rate", None)
    lines.append(
        f"Reporter: role={reporter_role}, "
        f"historical approval rate={approval_rate if approval_rate is not None else 'N/A (new user)'}"
    )

    return "\n".join(lines)


# ── Main public function ──────────────────────────────────────────────────────

def score_disruption_with_crew(report_text: str, context: dict) -> dict | None:
    """
    Run the 3-agent CrewAI pipeline and return a scoring dict, or None on failure.

    Parameters
    ----------
    report_text : str
        The raw disruption report description.
    context : dict
        Sensor and reporter metadata with keys:
            weather            : dict | None   — latest WeatherSnapshot fields
            ais_vessels        : list[dict]    — recent AISSnapshot dicts
            nearby_similar_reports : int       — count from spatial query
            reporter_role      : str
            reporter_approval_rate : float | None
            disruption_type    : str
            location_name      : str | None

    Returns
    -------
    dict with keys: score (int), reason (str), validation (str), facts (dict)
    None if CrewAI is unavailable or any error occurs.
    """
    if not _crewai_ready():
        logger.info("CrewAI not ready — skipping crew pipeline.")
        return None

    try:
        reader, validator, scorer = _build_agents()
        context_summary = _build_context_summary(context)

        disrupt_type = context.get("disruption_type", "unknown")
        location = context.get("location_name") or "unspecified location"

        # ── Task 1: Fact extraction ───────────────────────────────────────────
        t1 = Task(
            description=(
                f"A disruption report has been submitted for a {disrupt_type} "
                f"event at {location}.\n\n"
                f"Report text:\n\"\"\"\n{report_text}\n\"\"\"\n\n"
                "Extract and return a JSON object with these fields:\n"
                "  type       : disruption type (one word)\n"
                "  location   : place name or coordinates\n"
                "  severity   : low | medium | high\n"
                "  timing     : when the disruption started (if mentioned)\n"
                "  key_claims : list of 2–4 factual claims in the report\n"
                "Return ONLY the JSON object, no markdown."
            ),
            expected_output=(
                "JSON object: {type, location, severity, timing, key_claims}"
            ),
            agent=reader,
        )

        # ── Task 2: Validation ────────────────────────────────────────────────
        t2 = Task(
            description=(
                "Using the facts extracted in Task 1 and the live sensor context below, "
                "determine whether the disruption report is supported by objective data.\n\n"
                f"Live sensor context:\n{context_summary}\n\n"
                "Rules:\n"
                "  - 'confirmed'   : weather/AIS data clearly supports the report\n"
                "  - 'partial'     : some data aligns, some does not\n"
                "  - 'unconfirmed' : data contradicts or is absent\n\n"
                "Return a JSON object:\n"
                "  {\"verdict\": \"confirmed|partial|unconfirmed\", \"rationale\": \"one sentence\"}"
            ),
            expected_output=(
                "JSON: {verdict: confirmed|partial|unconfirmed, rationale: str}"
            ),
            agent=validator,
        )

        # ── Task 3: Score synthesis ───────────────────────────────────────────
        t3 = Task(
            description=(
                "Using the fact extraction (Task 1) and the validation verdict (Task 2), "
                "assign a final confidence score 0–100.\n\n"
                "Scoring guide:\n"
                "  85–100 : Highly Reliable — confirmed + strong corroboration\n"
                "  60–84  : Good Confidence — mostly confirmed\n"
                "  40–59  : Questionable    — partial or weak evidence\n"
                "  0–39   : Low Confidence  — unconfirmed or contradicted\n\n"
                "Also factor in reporter credibility and spatial corroboration from context.\n\n"
                "Return ONLY this JSON: {\"score\": <integer 0-100>, \"reason\": \"<1-2 sentence explanation>\"}"
            ),
            expected_output=(
                "JSON: {score: int, reason: str}"
            ),
            agent=scorer,
        )

        crew = Crew(
            agents=[reader, validator, scorer],
            tasks=[t1, t2, t3],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()

        # ── Parse outputs ─────────────────────────────────────────────────────
        # CrewAI returns the final task output as a string; earlier tasks are
        # accessible via task.output.raw
        facts_raw = t1.output.raw if t1.output else "{}"
        validation_raw = t2.output.raw if t2.output else "{}"
        score_raw = str(result)

        facts = _safe_json(facts_raw) or {}
        validation_obj = _safe_json(validation_raw) or {}
        score_obj = _safe_json(score_raw) or {}

        score = int(score_obj.get("score", 50))
        score = max(0, min(100, score))  # clamp
        reason = score_obj.get("reason", "Score assigned by AI pipeline.")
        verdict = validation_obj.get("verdict", "unconfirmed")

        return {
            "score": score,
            "reason": reason,
            "validation": verdict,
            "facts": facts,
        }

    except Exception as exc:
        logger.error("CrewAI pipeline failed: %s", exc, exc_info=True)
        return None


# ── JSON helper ───────────────────────────────────────────────────────────────

def _safe_json(text: str) -> dict | None:
    """Extract and parse the first JSON object found in text."""
    if not text:
        return None
    text = text.strip()
    # Try to extract a JSON block if the model wraps it in markdown
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


# ── Availability check for external callers ───────────────────────────────────

def crew_is_available() -> bool:
    """Returns True when CrewAI + OpenAI key are both configured."""
    return _crewai_ready()
