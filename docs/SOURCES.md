# Primary references

Consulted November 12, 2026.

- INPE TerraBrasilis data access: https://terrabrasilis.dpi.inpe.br/acesso-aos-dados/
- INPE WFS discovery and queries: https://terrabrasilis.dpi.inpe.br/download-de-dados/
- INPE WFS pagination caveats: https://terrabrasilis.dpi.inpe.br/wfs-getfeature-usando-paginacao-para-baixar-dados/
- Live capabilities used: https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/wfs?service=WFS&version=2.0.0&request=GetCapabilities
- INPE monitoring roles: https://www.gov.br/inpe/pt-br/acesso-a-informacao/perguntas-frequentes/principais-produtos-e-servicos-do-inpe/monitoramento-do-territorio-florestas/como-se-monitora-o-desmatamento
- Rasterio valid/nodata mask semantics: https://rasterio.readthedocs.io/en/stable/topics/masks.html
- Rasterio reprojection/CRS concepts: https://rasterio.readthedocs.io/en/stable/topics/reproject.html
- Google Gemini REST request structure: https://ai.google.dev/gemini-api/docs/generate-content/get-started
- Leaflet: https://leafletjs.com/
- OpenStreetMap tile policy: https://operations.osmfoundation.org/policies/tiles/
- Motivation — UNESCO AI Climate Institute announcement: https://www.unesco.org/en/articles/unesco-brazilian-government-and-itu-partner-launch-green-ai-climate-institute

The old INPE documentation example names deter_public and date. The live service exposed deter-amz:deter_amz and view_date during verification; the adapter uses capabilities and schema discovery rather than assuming that old example remains current.

External sources support data access and method semantics. They do not validate this application's thresholds, algorithms, results, or affiliation.
