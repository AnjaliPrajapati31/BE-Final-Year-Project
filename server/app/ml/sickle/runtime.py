from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import numpy as np
import torch

from app.core.exceptions import DomainError

from .fusion import FusionModel

EXPECTED_PARAMETER_COUNT = 1_597_010


class SickleRuntime:
    model_name = "sickle_utae_s1_s2_fusion"

    def __init__(self, model, device: torch.device, checkpoint_sha256: str, concurrency: int):
        self.model = model
        self.device = device
        self.checkpoint_sha256 = checkpoint_sha256
        self._semaphore = threading.BoundedSemaphore(max(1, concurrency))

    @classmethod
    def load(cls, checkpoint_path: Path, device_name: str = "auto", concurrency: int = 1):
        if not checkpoint_path.is_file():
            raise DomainError("MODEL_NOT_READY", "SICKLE checkpoint is missing.", 503)
        digest = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
        if device_name == "auto":
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            device = torch.device(device_name)
            if device.type == "cuda" and not torch.cuda.is_available():
                raise DomainError("MODEL_NOT_READY", "Configured CUDA device is unavailable.", 503)
        model = FusionModel()
        count = sum(parameter.numel() for parameter in model.parameters())
        if count != EXPECTED_PARAMETER_COUNT:
            raise DomainError("MODEL_NOT_READY", f"Unexpected model parameter count: {count}.", 503)
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("model"), dict):
            raise DomainError("MODEL_NOT_READY", "Checkpoint does not contain model state.", 503)
        state = {}
        for key, value in checkpoint["model"].items():
            if key.startswith("module."):
                key = key[len("module."):]
            if key.startswith("_orig_mod."):
                key = key[len("_orig_mod."):]
            state[key] = value
        model.load_state_dict(state, strict=True)
        model.to(device).eval()
        return cls(model, device, digest, concurrency)

    def infer(self, s1: np.ndarray, s1_dates: np.ndarray, s2: np.ndarray, s2_dates: np.ndarray) -> np.ndarray:
        data = {
            "S1": (torch.from_numpy(s1).unsqueeze(0).to(self.device, torch.float32), torch.from_numpy(s1_dates).unsqueeze(0).to(self.device, torch.long)),
            "S2": (torch.from_numpy(s2).unsqueeze(0).to(self.device, torch.float32), torch.from_numpy(s2_dates).unsqueeze(0).to(self.device, torch.long)),
        }
        with self._semaphore, torch.inference_mode():
            probabilities = torch.softmax(self.model(data), dim=1)
        if tuple(probabilities.shape) != (1, 2, 32, 32):
            raise DomainError("CROP_INFERENCE_FAILED", "Unexpected SICKLE output shape.", 500)
        return probabilities[0].detach().cpu().numpy()
