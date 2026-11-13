# Acceptance checklist — integrated educational delivery

| Capability | Implemented | Verified in this environment | Boundary |
|---|---|---|---|
| Python local web app, persistent SQLite | Yes | Automated HTTP and storage tests | Windows installer and visual rendering not run on Windows |
| Interactive Leaflet map / AOI | Yes | DOM map creation and geometry intersection tests | Basemap tile rendering not visually inspected; no basin boundary bundled |
| Public INPE connector | Yes | Real capabilities/schema discovery and a live eight-record 2026 query | Single bounded sample; service may change or be unavailable |
| Bundled real public data | Yes | Eight features imported without per-feature errors | Historical, incomplete sample; not current emergency evidence |
| RGB and NDVI change screening | Yes | Deterministic synthetic change and mask/grid tests, plus integrated UI flows | No field imagery accuracy study or automatic cloud classifier |
| Drone input | Yes | Manifest validation path and shared observation pipeline implemented | No physical flight, aircraft control or imagery acquisition |
| Sensor receiver and retry queue | Yes | Auth, ACK, duplicate/rejection and retry tests | Physical devices untested; receiver is loopback only |
| Cadence and no-data status | Yes | ACTIVE / INVALID / STALE / NO_DATA tests and DOM display | No external SMS/email/push notification |
| Local Isolation Forest | Yes | Chronological holdout and integrated UI run | Synthetic demonstration; no labelled forest-threat accuracy |
| Gemini advisory | Yes | Mocked transport and input-minimization tests | Requires user key/model; no successful live-key test claimed |
| Human review, preserved attachments | Yes | Append history, content copies and hashes tested | Human source interpretation is still required |
| Reports and integrity | Yes | JSON/CSV/HTML exports, escaping and tamper/deletion tests | Local hash chain is not externally anchored |

This is one integrated educational release. “Final” describes the consolidated delivery, not scientific certification, regulatory approval, field readiness or proof of environmental impact. Hardware, cloud credentials and externally prepared imagery are documented prerequisites, not simulated as successful integrations.
