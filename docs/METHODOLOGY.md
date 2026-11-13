# Methodology and boundaries

## Observation → screening → evidence review

Source records retain observed time, received time, provider reference, source type, declared mode and quality. Intake validates types, finite ranges, timestamps and coordinate ranges. This does not authenticate a device, independently verify a valid flag, or establish Amazon Basin membership. DEMO and FIELD remain separate in UI and exports; FIELD is a declaration, not a guarantee of real-world authenticity.

### Public alerts

The INPE connector discovers supported public DETER layers via WFS capabilities, obtains geometry/date properties via schema and requests one bounded feature page with explicit EPSG:4326 and WFS 1.0.0 lon/lat ordering. Source and retrieval metadata are retained. Spatial selection uses Shapely intersection with a rectangular AOI. Polygons touching its boundary count; original polygons are retained rather than clipped. No geometric area from the imported polygon is recomputed as an official rate.

Missing observations, cloud cover, sensor resolution and publication delay limit interpretation. DETER alerts and annual PRODES rates are distinct. The bundled eight-record sample is not an exhaustive 2026 dataset or a representative statistical sample.

### Image screening

RGB uses Green Leaf Index `(2G - R - B)/(2G + R + B)`, a visible-band heuristic. NDVI uses `(NIR - Red)/(NIR + Red)` on calibrated reflectance. Neither algorithm uniquely identifies deforestation.

Both require before<after times, co-registration confirmation and a supplied common clear/valid mask. NDVI additionally requires equal CRS, dimensions and transform; finite reflectance in [0,1]; no nodata; a nonzero denominator; and aligned masks. There is no automatic cloud classifier or resampling. The user must verify alignment and masking quality.

Candidate change means baseline index ≥ configured baseline and index decline ≥ configured threshold. The denominator is common-valid baseline-eligible pixels, not all pixels or all forest. Output includes total, valid, eligible and changed pixel counts. GeoTIFF projected metre grids may report cell-area hectares using the affine determinant; geographic grids omit hectare estimates. NDVI location comes from the raster centre transformed to WGS84. Spatial grid consistency does not establish positional ground accuracy.

### Rule priorities

- Invalid upstream quality: BLOCKED.
- Older than 48 hours: HISTORICAL, even if the original signal is strong.
- Fresh published alert flag=1: HIGH verification priority.
- Fresh image / supplied vegetation change ≥10%: HIGH.
- Fresh supplied acoustic activity index ≥0.8 or temperature ≥40°C: MEDIUM.
- Other fresh valid observations: LOW; no inference of safety.

These fixed thresholds are educational defaults, not calibrated probabilities. Multiple signals are not automatically fused. A shared site label alone is not corroboration.

### Sensors

Configured site cadence is scoped by site ID and mode. If no sensor record exists: NO_DATA. If latest observed age exceeds max(60 seconds, 3×expected interval): STALE. Otherwise latest quality invalid → INVALID, else ACTIVE. Last-valid time remains available. Freshness is re-evaluated on refresh, automatically every 30 seconds while the browser is visible. No external SMS/email/push alerts are sent. Duplicate event IDs are idempotent; changed content under an existing ID is rejected. Original observation times are not replaced by receipt times.

### AI

Local Isolation Forest uses a single metric, one site, one workspace, fixed random seed and at least 40 valid readings. Earlier observations train the model, latest 10 are held out chronologically. Historical baselines may contain anomalies. The final anomaly flag requires both the Isolation Forest flag and |modified z| > 3.5, with modified z = 0.67448975 × (value - training median) / training MAD. The band is fit on earlier observations only; held-out values cannot change it. Zero or numerically negligible MAD is rejected rather than replaced with an arbitrary scale. Partition times must be strictly separated. Raw Isolation Forest flags and scores remain in the output; decision_score is explicitly defined as 3.5 - |modified z|. The guard can suppress subtle anomalies and is not a calibrated probability or logging class. No accuracy estimate is fabricated without independent labels.

Cloud Gemini receives minimized numeric/context fields after explicit consent and returns unverified text. No cloud image upload, RAG corpus, autonomous decision, hardware command, model training or priority override is included. Credentials and availability are prerequisites.

### Human review and integrity

Decisions are appended with reviewer identity, rationale and time. The application retains earlier decisions. Uploaded originals are copied with SHA-256. Audit events are locally hash-chained; evidence inventory, payload hashes and stored file bytes are checked. The chain is not externally signed/anchored and can be rebuilt by an attacker with local access. A hash proves content identity, not ecological truth, source authenticity or legality.

## Evaluation required before field claims

Use independently labelled spatial/temporal holdouts, inspect false positives from flooding, seasonality and shadows, evaluate precision/recall and alert delay, verify sensor calibration and communication loss, compare georeferencing against independent references, and measure the human response process. Claiming avoided deforestation additionally needs an independently defensible counterfactual. No such outcome has been validated here.

Method references:
- Isolation Forest automatic offset: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- Modified z-score screening: https://itl.nist.gov/div898/handbook/eda/section3/eda35h.htm
