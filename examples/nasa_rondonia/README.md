# NASA Rondonia — real historical RGB image experiment

This is a separate experiment using the existing Amazon Forest Sentinel application. It does not change Python source or implement a NASA/drone integration. NASA does not endorse this independent educational project.

## Source and dates

NASA Earth Observatory, **World of Change: Amazon Deforestation**:
https://science.nasa.gov/earth/earth-observatory/world-of-change/amazon-deforestation/

- Before: `amazon_deforestation_20000730.jpg`, July 30, 2000.
- After: `amazon_deforestation_20120718.jpg`, July 18, 2012.
- Both are published RGB display JPGs, 720 × 480; originals are unchanged.

## Run in the existing app

1. Start `start_windows.bat` in the application root. Keep the terminal open.
2. Open http://127.0.0.1:8765 and select FIELD.
3. Open Image comparison and select RGB green-index screening.
4. Select the two JPGs as Before and After respectively.
5. Select `common_mask_nasa.png` as Common valid / clear mask.
6. Replace the entire acquisition metadata JSON with `metadata_nasa.json`.
7. Run the comparison. Review the overlay and exported evidence.

Use RGB, not NDVI. No API key is required. Optional Gemini interprets selected numeric fields only, not imagery.

## Interpretation and limits

FIELD denotes publicly sourced real imagery here, not a field visit or a drone capture. The mask is a manually selected partial region for an exploratory software test, not a validated cloud classification. White pixels are retained and black pixels excluded. Labels, scale and obvious edge smoke/clouds are avoided, but residual artifacts may remain.

The published viewports are visually consistent. Four 50 × 50 high-pass patch searches over ±6 pixels peaked at zero integer displacement, with correlations 0.575, 0.300, 0.360 and 0.095. Some correlations are weak. This does not establish geographic or subpixel registration accuracy. `aligned: true` records exploratory acceptance only; see the accompanying metadata note.

The app requires numeric coordinates: the supplied -10.2, -63.8 are an approximate regional reference near Buritis, NOT the image center or a footprint. Do not interpret the map marker as georeferencing. Only acquisition calendar dates are known; midnight UTC is a serialization placeholder.

The default RGB thresholds are unchanged. Rendered JPG color differences are not calibrated surface reflectance. Results are candidate pixel changes, not a verified deforestation area, rate, illegal activity finding or detection accuracy. No hectares are calculated. Physical hardware was unavailable for testing.

`software_check.json` records an independent local processing check with these exact inputs. It is not evidence of completion on the user's Windows machine. The NASA experiment belongs in its own post, separate from Post 5/5.
