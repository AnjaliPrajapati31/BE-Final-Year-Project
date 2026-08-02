from __future__ import annotations

import argparse
import re
import urllib.parse
import urllib.request

import rasterio


def confirmed_url(file_id: str) -> str:
    initial = "https://drive.usercontent.google.com/download?" + urllib.parse.urlencode(
        {"id": file_id, "export": "download"}
    )
    with urllib.request.urlopen(initial, timeout=30) as response:
        html = response.read().decode("utf-8")
    uuid_match = re.search(r'name="uuid" value="([^"]+)"', html)
    if not uuid_match:
        raise RuntimeError("Google Drive did not return a public large-file confirmation page")
    return "https://drive.usercontent.google.com/download?" + urllib.parse.urlencode(
        {"id": file_id, "export": "download", "confirm": "t", "uuid": uuid_match.group(1)}
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Read a public Google Drive GeoTIFF header using HTTP ranges.")
    parser.add_argument("file_id")
    args = parser.parse_args()
    url = confirmed_url(args.file_id)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(f"/vsicurl/{url}") as source:
        print(
            {
                "width": source.width,
                "height": source.height,
                "count": source.count,
                "crs": str(source.crs),
                "bounds": tuple(source.bounds),
                "transform": tuple(source.transform),
                "block_shapes": source.block_shapes[:2],
                "bands": source.descriptions,
            }
        )


if __name__ == "__main__":
    main()
