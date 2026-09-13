from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.water.validation import build_validation_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a non-claiming paddy water-balance validation report.")
    parser.add_argument("input", type=Path, help="JSON file containing a top-level fields array")
    parser.add_argument("--output", type=Path, help="Optional destination for the generated JSON report")
    arguments = parser.parse_args()

    try:
        payload = json.loads(arguments.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Validation input is unreadable: {exc}") from exc
    fields = payload.get("fields")
    if not isinstance(fields, list):
        raise SystemExit("Validation input must contain a top-level fields array")

    report = build_validation_report(fields)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if not report["water_deficit_accuracy_publishable"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
