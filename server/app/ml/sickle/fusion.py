from __future__ import annotations

from types import SimpleNamespace

import torch
from torch import nn

from .utae import UTAE


SATELLITES = {
    "S1": {"bands": ["VV", "VH"]},
    "S2": {
        "bands": [
            "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8",
            "B8A", "B9", "B11", "B12",
        ]
    },
}


def model_config() -> SimpleNamespace:
    return SimpleNamespace(
        model="utae",
        satellites=SATELLITES,
        primary_sat="S1",
        img_size=(32, 32),
        encoder_widths=[64, 128],
        decoder_widths=[32, 128],
        out_conv=[32, 16],
        str_conv_k=4,
        str_conv_s=2,
        str_conv_p=1,
        agg_mode="att_group",
        encoder_norm="group",
        n_head=16,
        d_model=256,
        d_k=4,
        pad_value=0.0,
        padding_mode="reflect",
        num_classes=2,
    )


class BuildModel(nn.Module):
    """Preserves the checkpoint's otherwise-unused primary `model` branch."""

    def __init__(self, config: SimpleNamespace):
        super().__init__()
        self.CFG = config
        self.sat = list(config.satellites)[0]
        self.model = self.get_model(self.sat)

    def get_model(self, satellite: str) -> UTAE:
        config = self.CFG
        return UTAE(
            input_dim=len(config.satellites[satellite]["bands"]),
            encoder_widths=config.encoder_widths,
            decoder_widths=config.decoder_widths,
            out_conv=config.out_conv,
            str_conv_k=config.str_conv_k,
            str_conv_s=config.str_conv_s,
            str_conv_p=config.str_conv_p,
            agg_mode=config.agg_mode,
            encoder_norm=config.encoder_norm,
            n_head=config.n_head,
            d_model=config.d_model,
            d_k=config.d_k,
            encoder=False,
            return_maps=False,
            pad_value=config.pad_value,
            padding_mode=config.padding_mode,
        )

    def forward(self, data):
        images, dates = data[self.sat]
        return self.model(images, batch_positions=dates)


class FusionModel(BuildModel):
    def __init__(self, config: SimpleNamespace | None = None):
        config = config or model_config()
        super().__init__(config)
        self.models = nn.ModuleDict(
            {satellite: self.get_model(satellite) for satellite in config.satellites}
        )
        self.conv_final = nn.Conv2d(
            len(config.satellites) * config.out_conv[-1],
            config.num_classes,
            kernel_size=3,
            stride=1,
            padding=1,
        )

    def forward(self, data):
        outputs = []
        for satellite in self.CFG.satellites:
            images, dates = data[satellite]
            outputs.append(self.models[satellite](images, batch_positions=dates))
        return self.conv_final(torch.cat(outputs, dim=1))
