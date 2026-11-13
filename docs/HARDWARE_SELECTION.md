# Reference hardware selection

Selected for integration planning, without considering cost. No acquisition, physical integration or field validation is implied.

| Role | Reference equipment | Rationale |
|---|---|---|
| Vegetation mapping | WingtraRAY + MicaSense RedEdge-P | Documented platform compatibility, multispectral imagery and reflectance-calibration workflow |
| Visual / thermal inspection | DJI Matrice 400 + Zenmuse H30T | Documented pairing and visual plus radiometric thermal records |
| Fixed observation | AXIS P1488-LE | Documented RTSP/RTSPS, ONVIF and VAPIX interfaces |
| Environmental context | Vaisala WXT536 | Weather measurements and digital sensor interfaces |
| Edge processing | NVIDIA Jetson Orin NX 16 GB | Candidate for local acquisition and media preparation; carrier board and supporting electronics required |
| Connectivity | Teltonika RUTX50 | Cellular backhaul where coverage exists, dual SIM and Ethernet |

See [the manufacturer study](Drone_Sensor_Study.pdf), [hardware interfaces](HARDWARE.md) and [validation boundaries](ACCEPTANCE.md).

## Integration status

The Python application does not yet implement manufacturer-specific DJI/AXIS connectors, live RTSP/RTMP ingestion, radiometric thermal decoding or an acoustic classifier. It accepts prepared image pairs, observation JSON and file attachments. No selected equipment was physically tested. Vendor SDK availability is not evidence of completed integration.

The fifth project post should report the available software / simulated-transport evidence separately from pending physical hardware tests.
