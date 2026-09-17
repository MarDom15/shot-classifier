"""Rapport de derive des donnees (data drift) avec Evidently.

Compare la distribution des caracteristiques d'une session de reference
(donnees d'entrainement) a celle d'une session "courante" (par defaut, la
session tenue a l'ecart pour le test, en simulation d'un flux de production).

Dans un vrai deploiement, la population "courante" serait remplacee par les
caracteristiques calculees sur les prédictions recentes (voir
monitoring/prediction_log.jsonl), rejouees a travers src/data/features.py.

Usage:
    python -m src.monitoring.drift --out docs/reports/drift_report.html
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.utils.config import DATA_FEATURES, GROUP_COL, TEST_SESSION

DRIFT_COLUMNS = [
    "mean", "std", "energy", "peak_to_peak", "peak_idx", "peak_amplitude",
    "clip_frac", "zero_crossing_rate", "rise_time_idx", "skewness", "kurtosis",
    "dominant_freq_bin", "spectral_centroid", "spectral_flatness",
]


def generate_drift_report(out_path: str | Path = "docs/reports/drift_report.html",
                           current_df: pd.DataFrame | None = None) -> str:
    from evidently import DataDefinition, Dataset, Report
    from evidently.presets import DataDriftPreset

    feat = pd.read_csv(DATA_FEATURES)
    cols = [c for c in DRIFT_COLUMNS if c in feat.columns]

    reference = feat[feat[GROUP_COL].astype(str) != TEST_SESSION][cols]
    current = current_df[cols] if current_df is not None else feat[feat[GROUP_COL].astype(str) == TEST_SESSION][cols]

    ref_ds = Dataset.from_pandas(reference, data_definition=DataDefinition())
    cur_ds = Dataset.from_pandas(current, data_definition=DataDefinition())

    report = Report([DataDriftPreset()])
    result = report.run(cur_ds, ref_ds)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.save_html(str(out_path))
    return str(out_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="docs/reports/drift_report.html")
    args = ap.parse_args()
    path = generate_drift_report(args.out)
    print(f"Rapport de derive ecrit: {path}")


if __name__ == "__main__":
    main()
