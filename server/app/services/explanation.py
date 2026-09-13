from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.exceptions import DomainError
from app.schemas.explanation import AnalysisExplanation
from pydantic import ValidationError

PROMPT_VERSION = "analysis-explanation-v1"
PROVIDER = "openai-responses"

OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "crop_and_stage": {"type": "string"},
        "water_status": {"type": "string"},
        "irrigation_guidance": {"type": "string"},
        "cautions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "crop_and_stage", "water_status", "irrigation_guidance", "cautions"],
}


def build_redacted_context(row: dict, payloads: dict, water: dict) -> dict:
    """Return only bounded scientific outputs; never identifiers, geometry, imagery, or raw time series."""
    crop = payloads.get("crop") or {}
    stage = payloads.get("growth_stage") or {}
    stress = payloads.get("moisture_stress") or {}
    balance = water.get("water_balance") or {}
    advisory = water.get("irrigation_advisory") or {}
    modules = payloads.get("modules") or {}
    bounded_warnings = lambda values: [str(value)[:300] for value in (values or [])[:12]]
    return {
        "overall_status": row.get("status"),
        "crop": {key: crop.get(key) for key in ("class_label", "confidence", "paddy_probability", "experimental")},
        "growth_stage": {key: stage.get(key) for key in ("status", "stage", "evidence", "provisional", "latest_observation")},
        "moisture_stress": {key: stress.get(key) for key in ("status", "stress_risk", "stress_score", "provisional", "warning")},
        "water_balance": {key: balance.get(key) for key in (
            "status", "as_of_date", "water_deficit_mm", "water_deficit_low_mm", "water_deficit_high_mm",
            "root_depletion_mm", "ponded_water_mm", "evidence_level", "provisional",
        )},
        "irrigation_advisory": {key: advisory.get(key) for key in (
            "status", "action", "urgency", "net_depth_mm", "gross_depth_mm", "volume_m3",
            "recommended_timing", "reason", "evidence_level", "provisional",
        )},
        "module_statuses": {name: value.get("status") for name, value in modules.items() if isinstance(value, dict)},
        "water_warnings": bounded_warnings(balance.get("warnings")),
        "advisory_warnings": bounded_warnings(advisory.get("warnings")),
        "system_warnings": bounded_warnings(row.get("warnings")),
    }


def context_sha256(context: dict) -> str:
    encoded = json.dumps(context, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class OpenAIExplanationProvider:
    api_key: str | None
    model: str | None
    endpoint: str
    timeout_seconds: int
    transport: Callable = urlopen

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    def explain(self, context: dict, language: str) -> dict:
        if not self.enabled:
            raise DomainError("AI_EXPLANATION_UNAVAILABLE", "AI explanation is not configured.", 503)
        language_name = "Tamil" if language == "ta" else "English"
        instructions = (
            "Explain deterministic agricultural analysis outputs to a farmer. Never recalculate, alter, or invent "
            "crop classes, millimetres, volumes, urgency, dates, or irrigation actions. Treat null as unavailable. "
            "State clearly when science is provisional or evidence is low. Do not diagnose disease. "
            f"Write concise {language_name}. The supplied JSON contains no field identity or geometry."
        )
        body = {
            "model": self.model,
            "store": False,
            "instructions": instructions,
            "input": json.dumps(context, sort_keys=True, default=str),
            "text": {"format": {"type": "json_schema", "name": "analysis_explanation", "strict": True, "schema": OUTPUT_SCHEMA}},
        }
        request = Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.transport(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise DomainError("AI_EXPLANATION_FAILED", "AI explanation could not be generated.", 502) from exc
        text = next((
            content.get("text")
            for item in result.get("output", [])
            for content in item.get("content", [])
            if content.get("type") == "output_text" and content.get("text")
        ), None)
        try:
            explanation = json.loads(text) if text else None
        except json.JSONDecodeError as exc:
            raise DomainError("AI_EXPLANATION_FAILED", "AI explanation returned invalid structured output.", 502) from exc
        try:
            explanation = AnalysisExplanation.model_validate(explanation).model_dump()
        except ValidationError as exc:
            raise DomainError("AI_EXPLANATION_FAILED", "AI explanation returned an invalid contract.", 502)
        return explanation
