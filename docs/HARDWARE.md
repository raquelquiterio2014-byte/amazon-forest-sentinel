# Drone and sensor integration

## Observation contract

HTTP `POST /api/ingest` accepts one observation object or an array. Content type is JSON; `Authorization: Bearer <private token>` is required. The token is generated at first launch in `data/sensor_token.txt`; never put it in a public repository. Requests are local-only. The response has `ack`, `inserted`, `duplicates` and per-row `errors`. Identical IDs/content are acknowledged as duplicates. Conflicting reuse of an ID is rejected. ACK means durably committed to local SQLite, not validated physical accuracy.

```json
{
  "id": "device-boot-id-sequence",
  "site_id": "FIELD-SITE-001",
  "source_type": "sensor",
  "source_ref": "Device ID, sensor model, source and calibration reference",
  "mode": "FIELD",
  "timestamp": "2026-11-12T18:00:00Z",
  "latitude": -3.1,
  "longitude": -60.0,
  "metric": "temperature_c",
  "value": 27.1,
  "quality": "valid",
  "metadata": {
    "device_id": "field-device-001",
    "calibration_id": "replace-with-actual-record",
    "firmware": "actual-build-identifier",
    "battery_v": 3.8
  }
}
```

Dates must be real observation times with a timezone. Current supported metrics: `temperature_c`, `humidity_pct`, `acoustic_activity_index`, `vegetation_change_pct`, `satellite_alert`. Acoustic indexes and vegetation-change estimates must come from an explicitly documented upstream process. No microphone classifier is included. Do not set invalid data to zero; send `quality: invalid` with a finite in-range raw value only when available, or withhold the observation and let the configured freshness check expose missing data. Do not invent a measurement to satisfy the schema.

### Software replay

Start the application first. In another terminal, from the project folder:

```shell
python device_client.py --replay examples/sensor_observations.json --refresh-demo-time
```

The optional time-refresh switch is restricted to DEMO records. It must never rewrite the acquisition time of field observations.

Use `--retry` to retry pending events every five seconds. Queue state persists in `data/device_outbox.sqlite3`; errors remain visible in that SQLite table. A rejected record is retained for diagnosis. This is a bounded single-laptop prototype, not a fleet-scale broker.

### USB serial / ESP32

Install the optional serial dependency:

```shell
python -m pip install -r requirements-serial.txt
python device_client.py --serial COM5 --baud 115200
```

On Linux use an actual device such as `/dev/ttyUSB0`. The device must emit one full observation JSON per newline. The bridge validates each record, enqueues it on the laptop and waits for receiver ACK before removing it. If the laptop never receives a record, its queue cannot recover it; deploy MCU-side persistence separately if required.

The supplied `firmware/esp32_serial_sensor.ino` is an uncompiled example for ESP32 + DHT22. It uses NTP over Wi-Fi for timestamps and USB serial for observations. Configure actual Wi-Fi, site coordinates and calibration metadata. DHT22 readings being syntactically valid does not mean the device is calibrated. Failed reads are withheld; no-data detection occurs at the site cadence level.

### Remote deployment

Do not expose this development HTTP server directly to the internet. A device-side bridge can forward through an existing authenticated SSH tunnel to the laptop loopback endpoint; production requires separately managed TLS, per-device credentials, access controls, broker/queue policies, monitoring and deployment hardening. This package does not configure a remote host or create credentials for external services.

### Drone workflows

1. Import a flight manifest following `examples/drone_manifest.json`: `flight_id`, `mode` and `observations` are required; every observation must have `source_type: drone` and the same mode.
2. Attach originals (images, logs, calibration / flight records) against an observation in Human Review. The application copies originals and stores hashes.
3. For image screening, use orthorectified and co-registered inputs, correct band calibration and a common valid mask. RGB location is provided metadata; NDVI location is derived from the GeoTIFF centre.
4. Record ground verification, alternate explanations and reviewer conclusions.

This is data integration, not a flight controller. No autonomous route generation, aircraft control, person identification or enforcement action is implemented. No drone or sensor hardware has been tested as part of this release.
