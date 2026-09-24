# GB street tiles (`/t/`)

Pre-built binary street-geometry tiles for the whole of Great Britain, used
by the PassTrack Android Auto car map (`TileStreetCache.kt` /
`SiteTileFetcher.kt` in the app repo) so the car screen never depends on a
live query to the public Overpass API.

## Format

- One file per grid tile: `t/<latIdx>/<latIdx>_<lngIdx>.bin` (sharded one
  level by `latIdx` — GB is ~46k tiles total, past the ~20k-files-per-dir
  guidance for a flat layout), where `latIdx = floor(lat / 0.02)`,
  `lngIdx = floor(lng / 0.03)` (same grid `TileStreetCache.kt` uses —
  0.02° lat x 0.03° lng, ~2km cells).
- File body is the CST1 binary format (`CarStreetsCodec.kt` in the app
  repo): magic `"CST1"`, uint32 LE way count, then per way: 1 byte class
  (0 major / 1 secondary / 2 minor), uint32 LE point count, then that many
  (int32 LE lat*1e6, int32 LE lng*1e6) pairs.
- May be gzip-compressed at the same `.bin` path (detected by magic bytes
  `1f 8b`, not by filename) — the app's `SiteTileFetcher` handles either.
- A tile with no drivable roads simply has no file (the app treats a 404 as
  "confirmed empty", not an error).

Built by `tool/build_gb_street_tiles.py` in the app repo from a full Great
Britain `.osm.pbf` extract (Geofabrik). Ways are Douglas-Peucker simplified
(~3m tolerance) and clipped to each tile they cross.

## Attribution

Contains data from **OpenStreetMap**, © OpenStreetMap contributors,
available under the **Open Database License (ODbL)**.
https://www.openstreetmap.org/copyright — https://opendatacommons.org/licenses/odbl/

## Regenerating

See `tool/build_gb_street_tiles.py` in `Safee1/driving-test-simulator`.
