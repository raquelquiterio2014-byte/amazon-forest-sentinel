# Verification report — November 13, 2026

## Automated Python suite

**51 tests passed** on Python 3.12 / Linux, using:

```shell
python -m unittest discover -s tests -v
```

The suite covers finite-value/type/coordinate/time gates, duplicate IDs and conflicts, DEMO/FIELD separation, site cadence separation, valid zero versus missing data, quality/freshness gates, appended reviews, attachment preservation, content edits/deletion/hash-chain checks, spreadsheet formula protection, HTML escaping, exact AOI intersection and CRS validation, public sample import, overlapping public query deduplication, RGB/NDVI known synthetic change, common-mask exclusion, image date/grid/alignment gates, local AI holdout, minimized cloud payload, missing cloud credentials, HTTP token/origin checks, receiver ACKs/rejections, durable outbox retries, exports and integrated image processing.

Exact direct package versions used are recorded in requirements-tested.txt. Python compilation and `node --check web/app.js` passed. An upstream affine-library pending-deprecation warning appears for its existing multiplication operator; tests pass and the resulting raster centre is transformed by Rasterio.

## Integrated interface logic

JSDOM ran the shipped HTML/JavaScript against a real local Python HTTP server. Passed flows: demonstration loading; real public INPE sample import; Leaflet map creation; RGB and NDVI example processing; local Isolation Forest; record selection; human review; device status; JSON/CSV/HTML exports; methodology navigation. No application JavaScript errors remained. See DOM_ACCEPTANCE.json.

JSDOM is **not a visual browser**. Its blob image loading was mocked; independent Python tests validate generated image bytes and algorithm results. Chromium could not launch because this execution environment blocked a required process socket. No screenshot, mobile visual layout approval or Windows GUI validation is claimed.

## Real external data check

The official TerraBrasilis WFS capabilities exposed `deter-amz:deter_amz`. Schema discovery identified `geom` and `view_date`. A real query for 2026-01-01 through 2026-10-31 returned eight bounded sample records, imported successfully. The response reached its requested eight-record limit and is explicitly marked incomplete. Exact query, retrieval timestamp and response/bundled-file hashes are in examples/INPE_PROVENANCE.json.

## Not validated

- Physical ESP32, DHT22, acoustic sensor, drone or satellite image acquisition.
- Compilation of the illustrative Arduino firmware.
- Live Gemini credentials/model availability or response quality.
- Scientific detection accuracy, false-positive rates, geographic transferability, legal conclusions, prevented deforestation or environmental outcomes.
- Windows startup installer execution, full visual browser layout or production security deployment.

## Reproduce locally

Run the Python suite after installing requirements. For optional DOM testing, install Node.js 22+ and `npm install --no-save jsdom`, start `python server.py` in another terminal, then run `node tests/dom_acceptance.cjs`. The DOM report is written to data/dom_acceptance.json. DOM tests are development-only and are not needed to use the application.

## Local anomaly-screening verification

The revised algorithm retains Isolation Forest diagnostics and requires a train-only median/MAD guard for the final flag. It does not fit the guard to the ten held-out observations.

- DEMO fixture: 50 training observations and 10 evaluated observations.
- Seven ordinary holdout readings remain unflagged; three introduced temperature increases are flagged.
- Additional tests cover an independent ordinary holdout, independent high/low excursions, a shifted/scaled baseline, independence from evaluation values, zero-MAD rejection and tied-time partition rejection.
- The real local HTTP endpoint returns the same 7/3 summary.
- These are controlled synthetic checks, not estimates of field precision or recall.

Reproducible output is stored in LOCAL_AI_VALIDATION.json.
