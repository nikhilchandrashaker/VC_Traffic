#!/usr/bin/env bash
set -e
python src/01_generate_dataset.py
python src/02_analysis_models.py
python src/03_signal_simulation.py
python src/04_build_paper.py
python src/05_build_dashboard.py
