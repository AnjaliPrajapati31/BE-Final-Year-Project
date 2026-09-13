import json

import pytest

from app.core.exceptions import DomainError
from app.services.explanation import OpenAIExplanationProvider, build_redacted_context, context_sha256

pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.value).encode("utf-8")


def test_redacted_context_excludes_geometry_identity_and_time_series():
    row = {"status": "completed", "field_code": "SECRET", "geometry": {"type": "Polygon"}, "warnings": []}
    payloads = {
        "crop": {"class_label": "Paddy", "confidence": 0.9, "raw_pixels": [1, 2]},
        "water_balance": {"water_deficit_mm": 12},
        "charts": {"water_balance": [{"date": "2025-01-01"}]},
        "modules": {"crop": {"status": "completed"}},
    }
    context = build_redacted_context(row, payloads, {"water_balance": payloads["water_balance"], "irrigation_advisory": None})
    encoded = json.dumps(context)
    assert "SECRET" not in encoded
    assert "Polygon" not in encoded
    assert "raw_pixels" not in encoded
    assert "2025-01-01" not in encoded
    assert context["water_balance"]["water_deficit_mm"] == 12
    assert len(context_sha256(context)) == 64


def test_provider_is_optional_and_cannot_block_science():
    provider = OpenAIExplanationProvider(None, None, "https://example.invalid", 1)
    with pytest.raises(DomainError) as error:
        provider.explain({}, "en")
    assert error.value.code == "AI_EXPLANATION_UNAVAILABLE"


def test_provider_uses_structured_output_and_store_false():
    captured = {}
    explanation = {
        "summary": "Summary",
        "crop_and_stage": "Paddy, vegetative",
        "water_status": "12 mm deficit",
        "irrigation_guidance": "Irrigate soon",
        "cautions": ["Provisional"],
    }

    def transport(request, timeout):
        captured["body"] = json.loads(request.data)
        captured["authorization"] = request.headers["Authorization"]
        captured["timeout"] = timeout
        return FakeResponse({"output": [{"content": [{"type": "output_text", "text": json.dumps(explanation)}]}]})

    provider = OpenAIExplanationProvider("secret", "test-model", "https://api.example/responses", 7, transport)
    assert provider.explain({"water_balance": {"water_deficit_mm": 12}}, "en") == explanation
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["strict"] is True
    assert captured["authorization"] == "Bearer secret"
    assert captured["timeout"] == 7
