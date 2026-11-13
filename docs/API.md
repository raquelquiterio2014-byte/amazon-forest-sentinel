# Local API reference

Base: `http://127.0.0.1:8765`. This is a loopback-only single-user development application, not an internet service. Host validation restricts requests to localhost with the configured port. POST requests reject cross-origin browser origins. No CORS permission is granted.

Browser endpoints require `X-Session-Token` obtained by the local UI at startup. Do not reuse this ephemeral token for hardware. Device ingestion uses the private persistent `Authorization: Bearer ...` token from `data/sensor_token.txt`.

| Endpoint | Method | Payload / result |
|---|---|---|
| `/api/state?mode=DEMO` | GET | Current selected workspace, recent events, site health, integrity check |
| `/api/demo` | POST | `{}` creates stable synthetic fixtures once |
| `/api/import` | POST | Observation or JSON array; per-row errors and duplicate counts |
| `/api/ingest` | POST | Same observation contract with hardware bearer token; explicit ACK |
| `/api/site` | POST | id, mode, latitude, longitude, expected_interval_s |
| `/api/geojson` | POST | collection plus options: mode, source_ref, aoi, date_field, id_field, class_field |
| `/api/inpe` | POST | start, end, aoi, count, optional options; downloads one public WFS page into FIELD |
| `/api/drone` | POST | manifest with flight_id, mode and drone observations |
| `/api/analyze` | POST | method rgb/ndvi, before/after/mask file objects and acquisition metadata |
| `/api/attach` | POST | observation id and file object; copies original and stores hash |
| `/api/review` | POST | id, reviewer, decision, note; appends history |
| `/api/local-ai` | POST | mode, site_id and metric; trains local anomaly model |
| `/api/cloud-ai` | POST | id and consent:true; minimized-data Gemini request |
| `/api/export?mode=FIELD&format=json` | GET | JSON evidence bundle; csv and html formats also available |
| `/files/<sha256>` | GET | Authenticated original/overlay download |

File objects use `{"name":"filename.ext","data":"BASE64_BYTES"}`. Maximum original file size is 32 MiB; request size limit is 100 MiB. Images additionally have a 4-million-pixel limit. Imports are limited to 10,000 records and commit valid records individually. The UI shows rejected rows rather than implying all-or-nothing success. HTTP ingestion returns 200 with `ack:false` for per-row rejections, so clients must inspect ACK, not just HTTP status.

Supported observations and flight metadata are documented in HARDWARE.md and examples/. Image metadata is illustrated by examples/image_metadata.json. Imported public INPE IDs use a stable provider namespace across overlapping queries; source retrieval metadata remain in import/query audit events. A changed payload under the same stable ID is a conflict, never a silent overwrite.
