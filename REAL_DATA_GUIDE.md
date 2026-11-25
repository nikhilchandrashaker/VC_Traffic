# Swapping in real data
This environment could not reach these sources, so none were downloaded or tested here. The steps below are a plan, not a verified recipe.
1. **Speeds/volumes:** Caltrans PeMS (detector 5-minute or hourly data; free account) for Ventura County freeways, and/or the FHWA NPMRDS travel-time data (access via your agency or RITIS). Aggregate to 15 minutes per segment.
2. **Weather:** NOAA Climate Data Online station data (e.g., Oxnard/Camarillo airports); rename to `precip_mm_15min` (convert units), `temp_f`, `visibility_mi`, `wind_mph`.
3. **Incidents:** Caltrans/CHP incident logs (PeMS incident table) to `incidents.csv` fields.
4. **Segments:** fill `segments.csv` from your detector/segment list, including `downstream_ids`/`upstream_ids`.
5. Keep the field names in `docs/DATA_DICTIONARY.md`, drop fields you lack (the models need speed, volume, incident, rain, calendar, segment fields), update the holiday list in scripts 01/02, and run scripts 02-05.
6. Before trusting results: handle missing detector data, add spatial cross-validation, and compare against a deep spatial-temporal baseline.
