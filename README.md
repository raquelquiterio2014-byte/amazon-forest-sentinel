# Amazon Forest Sentinel
## Integrated educational release — Evidence & Early Warning

A single Python application for importing public forest-change alerts, comparing co-registered images, receiving sensor observations, identifying unusual readings and recording human verification. Runs locally in a browser, with SQLite persistence. No GPU required; use bounded areas and image pairs on an 8 GB laptop.

This independent project is inspired by AI-for-climate work. It is not the AI Climate Institute platform, an INPE product, or a UNESCO / ITU / COP31 endorsed system. It supports possible prevention workflows but does not prove prevented deforestation, illegal activity or operational readiness.

## Start on Windows

Recommended: Python 3.11 or 3.12 **64-bit**, with the Python launcher enabled.

1. Extract the whole ZIP to a writable folder, e.g. `Documents\Amazon_Forest_Sentinel`.
2. Double-click **start_windows.bat**. The first run creates a virtual environment and installs the requirements; internet is needed for installation.
3. A local browser page opens at **http://127.0.0.1:8765**. Keep the terminal window open.
4. Click **Load demonstration**. Read the DEMO notice and explore the modules.
5. Stop the application with Ctrl+C in its terminal.

For PyCharm, open the extracted project, select a Python 3.11/3.12 interpreter, then run:

```shell
python -m pip install -r requirements.txt
python server.py
```

On Linux/macOS use `sh start.sh`. If port 8765 is occupied: `python server.py --port 8766`.

## Hardware study and reference selection

- [Drone and sensor study with manufacturer documentation](docs/Drone_Sensor_Study.pdf)
- [Selected reference hardware and integration status](docs/HARDWARE_SELECTION.md)
- [Software verification and remaining validation boundaries](docs/TEST_REPORT.md)

## What's included

| Module | Function |
|---|---|
| Forest overview | Counts, source coverage, verification priorities and recent evidence |
| Map & study area | Offline Leaflet code; point/polygon inspection, exact AOI intersection; optional online OpenStreetMap basemap |
| Evidence explorer | Search, source/quality inspection, individual rule reasons and hashes |
| Data & drone imports | Live public INPE WFS query, a bundled real sample, WGS84 GeoJSON, observation JSON and flight manifests |
| Image comparison | RGB Green Leaf Index or red/NIR NDVI screening; required common valid masks, dated inputs and saved overlays |
| Sensors & receiver | Bearer-authenticated HTTP ingestion, site cadence, ACTIVE / STALE / INVALID / NO_DATA states |
| AI assistance | Offline Isolation Forest with a train-only median/MAD guard; optional minimized-data Gemini advisory |
| Human review | Append-only-in-app decisions with rationale and preserved original evidence files |
| Reports & audit | Separate DEMO/FIELD JSON and CSV exports, print-ready HTML, local hash-chain checks |
| Methodology | Thresholds, source distinctions and validation boundaries |

## First guided session

1. **Overview → Load demonstration** creates 63 synthetic observations and two configured sensor sites. Repeated clicks do not refresh or overwrite existing timestamps.
2. **Sensors** shows one recent or stale site depending on when you loaded the data, and an intentionally historical site. Time passing can make the demonstration stale: this is expected.
3. **AI assistance → Run local anomaly model** uses `DEMO-RIVER / temperature_c`. Earlier 50 values train the model and robust median/MAD band; latest 10 are held out. The final flag requires both an Isolation Forest flag and an absolute modified z-score above 3.5. On the synthetic fixture, seven ordinary readings remain unflagged and the three introduced temperature increases are flagged. This result is not field accuracy.
4. **Data & drone imports → Import bundled real INPE sample** loads 8 real public alerts observed in 2026 into FIELD. They are historical records, not current emergency detections. The example is deliberately incomplete.
5. **Map → Fit evidence** inspects their original polygons. Basemap tiles load only if you enable the online checkbox.
6. **Image comparison → Use synthetic example pair → Analyze** runs a reproducible RGB experiment. Change the method to NDVI, reload its synthetic pair, and run again.
7. Select any record in **Evidence explorer**, then add a decision in **Human review**. Attach an original file if appropriate.
8. Export JSON, CSV or an HTML report in **Reports & audit**. Open the HTML report in your browser and print to PDF if desired.

## Real public data

The INPE connector discovers the current public DETER layer and its geometry/date fields via WFS capabilities and schema. It then queries a date interval and rectangular AOI. Current schema was verified on November 12, 2026: `deter-amz:deter_amz`, `geom`, `view_date`.

Only a bounded single page is requested (maximum 1,000 features). If the limit is reached, narrow the query; do not interpret the sample as a complete regional total. Results include download URL, retrieval time, response hash and completeness warning. Geometry is selected using exact intersection with the AOI; retained polygons are not clipped. No authoritative Amazon Basin boundary is bundled.

The bundled sample and exact provenance are in `examples/inpe_public_sample.geojson` and `examples/INPE_PROVENANCE.json`. DETER is an alert product; it is not the official annual PRODES deforestation rate. The user must check provider availability and source interpretation.

## Image inputs

- **RGB:** aligned PNG/JPEG before/after images and a PNG common clear mask (white usable, black excluded). The visible-band Green Leaf Index is **not NDVI**. Metadata supplies an approximate observation location; ordinary RGB images are not automatically orthorectified.
- **NDVI:** two GeoTIFFs with selectable red and NIR bands, identical CRS/grid/transform, plus an aligned common clear-mask GeoTIFF (>0 usable). Supply reflectance scale/offset appropriate to the source. Both dates must yield valid reflectance in [0,1]. Use small cropped areas, up to 4 million pixels and 32 MiB per file.
- **Both:** inputs must be co-registered and cloud-masked before import. An explicit checkbox confirms this prerequisite. The application rejects mismatched grids but cannot verify physical alignment or the accuracy of your masks.
- The change fraction denominator is common-valid pixels whose baseline index exceeds the baseline threshold. It is **not a percentage of the entire forest**. Grey overlay pixels are excluded; red pixels are screening candidates.
- Hectares are calculated only for projected metre-unit NDVI grids. This is grid-cell screening area, not validated deforestation area. NDVI locations are derived from the raster centre; RGB locations are supplied metadata.

## Sensors, drones and hardware

`docs/HARDWARE.md` specifies JSON contracts, USB serial bridging, durable laptop-side retries, a private receiver token and a sample ESP32/DHT22 sketch. `device_client.py` replays DEMO records or forwards a serial JSON stream. Optional serial dependencies: `python -m pip install -r requirements-serial.txt`.

The receiver binds only to 127.0.0.1. It is not a public deployment service. Use a local serial bridge or an authenticated SSH tunnel for remote hardware. Physical ESP32, microphones, drone flight/image acquisition and the example firmware are **not hardware-validated**. No flight controller is included.

## Cloud AI (optional)

Copy `.env.example` to `.env`, set `GEMINI_API_KEY` and `GEMINI_MODEL` to your own credentials and an available generateContent model ID, and restart. Never share `.env`.

Before each request, the UI asks to send only mode, source type, timestamp, metric, value and quality. Locations, IDs, source references, notes and files stay local. Gemini output is stored as unverified and never changes rules or controls hardware. Live Gemini access was **not tested with a real key**; request/response and minimized-data behaviour were tested with mocks. Core functionality and local AI operate without a key.

## Quality and testing

```shell
python -m unittest discover -s tests -v
```

See `docs/TEST_REPORT.md` and `docs/ACCEPTANCE.md` for evidence and remaining validation boundaries. This is a complete educational release with documented prerequisites, not a scientifically calibrated or operational prevention service.

## Local files and privacy

The first run creates `data/forest.sqlite3`, `data/files/` and a private receiver token. Originals uploaded to the app are copied under content hashes. Back up the entire data directory with the application stopped. Never include this directory, `.env`, precise field coordinates or working exports in a public repository.

Local hash chaining detects accidental modifications and inventory changes; an attacker with local access could rebuild the chain. It is not an externally anchored authenticity service. Keep independent copies of original sources.

## Rights and source attribution

No open-source license is granted for original project code. Third-party dependencies retain their own licenses. Bundled Leaflet is covered by `web/vendor/LEAFLET_LICENSE.txt`. INPE data retain their source attribution and applicable provider terms.

Primary references: see `docs/SOURCES.md`.
