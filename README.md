# Traffic Intelligence Project: Ventura County Corridor Congestion

A reproducible data science project on why traffic congestion forms, whether it can be forecast 15/30/60 minutes ahead, and whether adaptive signals help.

> **READ THIS FIRST: the data are simulated.** No real traffic, weather, or incident records were downloaded (the build environment could not reach NPMRDS, PeMS, Data.gov, or NOAA). `observations.csv` and the other tables come from a mechanistic simulator over 12 *stylised* segments loosely patterned on US-101, SR-126, SR-118, SR-33 and arterials in Ventura/Oxnard. Results describe the simulator, not real Ventura traffic. The pipeline is built so real data can replace it (see `docs/REAL_DATA_GUIDE.md`).

## Contents
| Path | What |
|---|---|
| `data/observations.csv` | 208,512 rows: 12 segments x 17,376 fifteen-minute intervals (2025-01-01 to 06-30), 18 fields |
| `data/segments.csv` `weather.csv` `incidents.csv` `signals.csv` | Road metadata and network links, weather, 309 incidents, 27 pretimed signals |
| `data/simulation_results.csv` | Signal-control simulation summary |
| `outputs/Traffic_Congestion_Research_Paper.pdf` | 7-page paper with models, diagrams, results, limitations |
| `outputs/Traffic_Dashboard.html` | Offline interactive dashboard (open in a browser) |
| `src/01..05_*.py` | Dataset generator, models and figures, signal simulation, paper builder, dashboard builder |
| `notebooks/exploration.ipynb` | Starter notebook |
| `docs/DATA_DICTIONARY.md`, `docs/REAL_DATA_GUIDE.md` | Field definitions; how to swap in real data |

## Run
```bash
pip install -r requirements.txt
bash run_all.sh        # about 5-10 min; writes data/, figures/, results.json, outputs/
```
Seeds are fixed, so results reproduce.

## Headline results (simulated data, May-Jun hold-out)
- 60-min speed forecast MAE: gradient boosting + graph features 1.33 mph vs persistence 3.85 mph.
- 60-min congestion-level macro-F1 0.80 vs 0.49 for persistence.
- Max-pressure signal control cuts delay under tidal demand (304 s to 26 s per vehicle) but barely helps in a capacity-cut incident.
- Rain and incident effects recovered by the estimator match the simulator's built-in mechanisms (a code check, not a real-world finding).

## Known limitations
Simulated data; breakdown speeds can fall to a few mph, inflating delay totals; no LSTM/GNN (a graph-feature gradient-boosting model stands in); signal model is one isolated two-phase intersection not calibrated to the dataset; Webster-style plan equals fixed plan in the symmetric scenarios.
