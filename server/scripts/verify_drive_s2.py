from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.warp import Resampling, reproject

from probe_drive_geotiff import confirmed_url


FILES = {
    "June": "1-W_I8ckxOsFL9qX6m1Q7f_BL7Gy4-6Lu",
    "July": "1GnL_Z0Sr59hI-Ue6xA9fY9FfNlFH6VxF",
    "August": "1Y_0iJzGte0wfjR1hmyzmHMPWet1frcus",
    "September": "19TDYO7iwDYq1ggXooMN7_nRpzN38J4Bg",
    "October": "1QSPlpIq7U1jXVtS4Sp8mmzjRmCFtaqro",
}
S2_BANDS = ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B9", "B11", "B12")


def main() -> None:
    fixture_path = Path("tests/fixtures/sickle/pilot_001/pilot_001_sickle_input.npz")
    with np.load(fixture_path) as fixture:
        target_transform = Affine(*fixture["target_transform"].astype(float))
        target_crs = str(fixture["target_crs"].item()) if "target_crs" in fixture.files else "EPSG:4326"
        golden_months = fixture["S2_months"].tolist()
        golden = fixture["S2"].astype(np.float32)
    report = {}
    for month, file_id in FILES.items():
        output = np.full((12, 32, 32), np.nan, dtype=np.float32)
        url = confirmed_url(file_id)
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(f"/vsicurl/{url}") as source:
            band_map = {name: index for index, name in enumerate(source.descriptions, start=1)}
            for output_index, band_name in enumerate(S2_BANDS):
                reproject(
                    source=rasterio.band(source, band_map[band_name]),
                    destination=output[output_index],
                    src_transform=source.transform,
                    src_crs=source.crs,
                    src_nodata=source.nodata,
                    dst_transform=target_transform,
                    dst_crs=target_crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                )
            source_grid = tuple(source.transform)
        output = np.nan_to_num(output, nan=0.0, posinf=0.0, neginf=0.0)
        values = {
            "zero_fraction": float(np.mean(output[0] == 0)),
            "kept": bool(np.mean(output[0] == 0) < 0.25),
            "source_transform": source_grid,
        }
        if month in golden_months:
            expected = golden[golden_months.index(month)]
            values.update(
                exact=bool(np.array_equal(output, expected)),
                max_abs_difference=float(np.max(np.abs(output - expected))),
                mean_abs_difference=float(np.mean(np.abs(output - expected))),
            )
        report[month] = values
    print(json.dumps(report, indent=2))
    used = [month for month, values in report.items() if values["kept"]]
    if used != golden_months or not all(report[month].get("exact", False) for month in golden_months):
        raise SystemExit("Drive TIFF extraction does not match the golden S2 input.")
    print("Drive TIFF to golden S2 parity PASSED")


if __name__ == "__main__":
    main()
