from __future__ import annotations

import hashlib
import csv
import io
import json
import os
from pathlib import Path
from uuid import UUID

import numpy as np
from PIL import Image, ImageDraw
from rasterio.io import MemoryFile
from rasterio.transform import Affine

from app.core.exceptions import DomainError


class ArtifactWriter:
    def __init__(self, root: Path, enabled: bool):
        self.root = root.resolve()
        self.enabled = enabled

    def _write(self, request_id: UUID, artifact_type: str, extension: str, mime_type: str, raw: bytes) -> dict:
        if not self.enabled:
            raise DomainError("ARTIFACT_WRITE_FAILED", "Artifact generation is disabled.")
        directory = (self.root / str(request_id)).resolve()
        if self.root not in directory.parents:
            raise DomainError("ARTIFACT_WRITE_FAILED", "Invalid artifact destination.")
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{artifact_type}.{extension}"
        destination = directory / filename
        temporary = destination.with_suffix(f".{os.getpid()}.tmp")
        try:
            temporary.write_bytes(raw)
            os.replace(temporary, destination)
        except OSError as exc:
            raise DomainError("ARTIFACT_WRITE_FAILED", "Could not write an analysis artifact.", 500) from exc
        return {"type": artifact_type, "relative_path": f"{request_id}/{filename}", "mime_type": mime_type, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    def write_json(self, request_id: UUID, artifact_type: str, payload: dict) -> dict:
        return self._write(request_id, artifact_type, "json", "application/json", json.dumps(payload, indent=2, sort_keys=True).encode())

    def write_csv(self, request_id: UUID, artifact_type: str, rows: list[dict]) -> dict:
        buffer = io.StringIO(newline="")
        fieldnames = list(rows[0]) if rows else []
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            for row in rows:
                writer.writerow({key: json.dumps(value) if isinstance(value, (dict, list)) else value for key, value in row.items()})
        return self._write(request_id, artifact_type, "csv", "text/csv", buffer.getvalue().encode())

    def write_crop_geotiff(self, request_id: UUID, probabilities: np.ndarray, field_mask: np.ndarray, grid) -> dict:
        nodata = -9999.0
        classes = probabilities.argmax(axis=0).astype(np.float32)
        stack = np.stack([probabilities[0], probabilities[1], classes]).astype(np.float32)
        stack[:, ~field_mask.astype(bool)] = nodata
        try:
            with MemoryFile() as memory:
                with memory.open(driver="GTiff", width=32, height=32, count=3, dtype="float32", crs=grid.crs, transform=Affine(*grid.transform), nodata=nodata, compress="deflate") as dataset:
                    dataset.write(stack)
                    dataset.set_band_description(1, "Paddy probability")
                    dataset.set_band_description(2, "Non-Paddy probability")
                    dataset.set_band_description(3, "Predicted class: 0 Paddy, 1 Non-Paddy")
                raw = memory.read()
        except Exception as exc:
            raise DomainError("ARTIFACT_WRITE_FAILED", "Could not create the crop GeoTIFF artifact.", 500) from exc
        return self._write(request_id, "crop_probability", "tif", "image/tiff", raw)

    def write_crop_png(self, request_id: UUID, paddy: np.ndarray, field_mask: np.ndarray) -> dict:
        try:
            clipped = np.clip(paddy, 0, 1)
            rgba = np.zeros((32, 32, 4), dtype=np.uint8)
            rgba[..., 0] = ((1 - clipped) * 220).astype(np.uint8)
            rgba[..., 1] = (clipped * 190).astype(np.uint8)
            rgba[..., 2] = 40
            rgba[..., 3] = field_mask.astype(np.uint8) * 255
            image = Image.fromarray(rgba, "RGBA").resize((320, 320), Image.Resampling.NEAREST)
            buffer = io.BytesIO(); image.save(buffer, format="PNG")
        except Exception as exc:
            raise DomainError("ARTIFACT_WRITE_FAILED", "Could not create the crop preview artifact.", 500) from exc
        return self._write(request_id, "crop_probability_preview", "png", "image/png", buffer.getvalue())

    def write_stage_png(self, request_id: UUID, timeline: list[dict]) -> dict | None:
        points = [(index, float(row["ndvi"])) for index, row in enumerate(timeline) if row.get("ndvi") is not None]
        if not points:
            return None
        try:
            image = Image.new("RGB", (900, 420), "white"); draw = ImageDraw.Draw(image)
            draw.rectangle((60, 30, 870, 360), outline="#9ca3af")
            count = max(1, len(points) - 1)
            coordinates = [(60 + index * 810 / count, 360 - (value + 1) * 165) for index, value in points]
            if len(coordinates) > 1:
                draw.line(coordinates, fill="#15803d", width=4)
            for x, y in coordinates:
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#15803d")
            draw.text((60, 380), "Provisional NDVI timeline (-1 to 1)", fill="black")
            buffer = io.BytesIO(); image.save(buffer, format="PNG")
        except Exception as exc:
            raise DomainError("ARTIFACT_WRITE_FAILED", "Could not create the stage timeline artifact.", 500) from exc
        return self._write(request_id, "stage_curve", "png", "image/png", buffer.getvalue())

    def write_analysis(self, request_id: UUID, crop: dict, stage: dict, probabilities: np.ndarray, inputs) -> tuple[list[dict], list[str]]:
        artifacts: list[dict] = []
        warnings: list[str] = []
        operations = [
            lambda: self.write_json(request_id, "crop_summary_json", crop),
            lambda: self.write_csv(request_id, "crop_summary_csv", [crop]),
            lambda: self.write_crop_geotiff(request_id, probabilities, inputs.field_mask, inputs.grid),
            lambda: self.write_crop_png(request_id, probabilities[0], inputs.field_mask),
            lambda: self.write_json(request_id, "stage_summary_json", {key: value for key, value in stage.items() if key != "timeline"}),
            lambda: self.write_csv(request_id, "stage_timeline_csv", stage.get("timeline", [])),
        ]
        for operation in operations:
            try:
                artifacts.append(operation())
            except DomainError as exc:
                warnings.append(exc.message)
        try:
            stage_png = self.write_stage_png(request_id, stage.get("timeline", []))
            if stage_png:
                artifacts.append(stage_png)
        except DomainError as exc:
            warnings.append(exc.message)
        if not artifacts and warnings:
            raise DomainError("ARTIFACT_WRITE_FAILED", warnings[0], 500)
        return artifacts, warnings
