"""Build the self-hosted basemap for the "Where is it?" map.

Copies the Newcastle area (zooms 0-15) out of the latest Protomaps daily build
of OpenStreetMap, by HTTP range requests, into one small PMTiles archive, and
fetches the fonts and sprites its style needs. Everything lands in
portal/web/public/basemap/ (gitignored), so applicants' browsers ask only our
own server for map data.

    api/.venv/bin/python basemap/extract.py          # run from portal/
"""

import datetime as dt
import functools
import math
import sys
from pathlib import Path

import httpx
from pmtiles.reader import Reader
from pmtiles.tile import tileid_to_zxy, zxy_to_tileid
from pmtiles.writer import Writer

# Newcastle's town boundary spans -69.6378, 43.9798 .. -69.5140, 44.1156
# (data/street-types/raw/town_boundary.geojson); this adds a margin.
BBOX = (-69.66, 43.96, -69.49, 44.13)
MAX_ZOOM = 15
OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "basemap"
ASSETS = "https://raw.githubusercontent.com/protomaps/basemaps-assets/main"
FONTS = ["Noto Sans Regular", "Noto Sans Medium", "Noto Sans Italic"]
RANGES = ["0-255", "256-511", "8192-8447"]
SPRITES = ["light.json", "light.png", "light@2x.json", "light@2x.png"]


def latest_build(client: httpx.Client) -> str:
    today = dt.date.today()
    for back in range(8):
        url = f"https://build.protomaps.com/{(today - dt.timedelta(days=back)):%Y%m%d}.pmtiles"
        if client.head(url).status_code == 200:
            return url
    sys.exit("no Protomaps build found in the last 8 days")


def tile_range(z: int) -> tuple[range, range]:
    n = 2 ** z

    def x(lon):
        return int((lon + 180) / 360 * n)

    def y(lat):
        return int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)

    west, south, east, north = BBOX
    return range(x(west), x(east) + 1), range(y(north), y(south) + 1)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        url = latest_build(client)
        print("source:", url)

        @functools.lru_cache(maxsize=4096)
        def get_bytes(offset: int, length: int) -> bytes:
            r = client.get(url, headers={"Range": f"bytes={offset}-{offset + length - 1}"})
            r.raise_for_status()
            return r.content

        reader = Reader(get_bytes)
        src = reader.header()
        meta = reader.metadata()
        ids = sorted(zxy_to_tileid(z, x, y)
                     for z in range(MAX_ZOOM + 1)
                     for xs, ys in [tile_range(z)] for x in xs for y in ys)
        written = 0
        archive = OUT / "newcastle.pmtiles"
        with open(archive, "wb") as f:
            writer = Writer(f)
            for tid in ids:
                data = reader.get(*tileid_to_zxy(tid))
                if data:
                    writer.write_tile(tid, data)
                    written += 1
            west, south, east, north = BBOX
            writer.finalize({
                "tile_type": src["tile_type"], "tile_compression": src["tile_compression"],
                "min_zoom": 0, "max_zoom": MAX_ZOOM,
                "min_lon_e7": int(west * 1e7), "min_lat_e7": int(south * 1e7),
                "max_lon_e7": int(east * 1e7), "max_lat_e7": int(north * 1e7),
                "center_zoom": 12, "center_lon_e7": int(-69.576 * 1e7), "center_lat_e7": int(44.048 * 1e7),
            }, {**meta, "attribution": "© OpenStreetMap contributors", "source": url})
        print(f"tiles: {written} of {len(ids)} in the box; archive {archive.stat().st_size / 1e6:.1f} MB")

        for font in FONTS:
            for rng in RANGES:
                dest = OUT / "fonts" / font / f"{rng}.pbf"
                dest.parent.mkdir(parents=True, exist_ok=True)
                r = client.get(f"{ASSETS}/fonts/{font.replace(' ', '%20')}/{rng}.pbf")
                r.raise_for_status()
                dest.write_bytes(r.content)
        for name in SPRITES:
            dest = OUT / "sprites" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            r = client.get(f"{ASSETS}/sprites/v4/{name}")
            r.raise_for_status()
            dest.write_bytes(r.content)
        print(f"fonts: {len(FONTS) * len(RANGES)} files; sprites: {len(SPRITES)} files")


if __name__ == "__main__":
    main()
