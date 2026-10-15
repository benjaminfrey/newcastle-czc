# Self-hosted basemap

The "Where is it?" map draws a street map of Newcastle from files on our own server, so an
applicant's browser never asks a map provider for the area they are looking at.

`extract.py` builds those files into `portal/web/public/basemap/` (gitignored):

- `newcastle.pmtiles`: OpenStreetMap vector tiles for the Newcastle area, zooms 0–15 (about 550
  tiles, about 2 MB), copied by HTTP range requests out of the latest Protomaps daily planet build
  (`https://build.protomaps.com/YYYYMMDD.pmtiles`).
- `fonts/`: Noto Sans Regular, Medium and Italic glyphs for the Latin ranges.
- `sprites/`: the Protomaps `light` icon sprites at 1x and 2x.

Run it on the VM, from `portal/`; it takes about three minutes:

    api/.venv/bin/pip install -r basemap/requirements.txt
    api/.venv/bin/python basemap/extract.py

Re-run it to refresh the map (OpenStreetMap changes daily; once a year is plenty here). The web
image copies whatever is in `public/basemap/` when it is built, so run this before `vm.sh lan`.

## Licences

- Map data: © OpenStreetMap contributors, under the Open Database License (ODbL). The map shows
  this attribution, which the licence requires.
- Fonts: SIL Open Font License (`fonts/OFL.txt` in protomaps/basemaps-assets).
- Sprites: derived from the MIT-licensed tangrams/icons (protomaps/basemaps-assets).
- Map style: the `@protomaps/basemaps` npm package (BSD-3-Clause).
