"""Entraine et compare plusieurs modeles classiques (features enrichies).

Deux etages :
    stage1 : is_shot (Steine=0 vs arme=1)         -> toutes les lignes
    stage2 : weapon  (G36/MP7/P8)                  -> lignes "tir" uniquement

Split train/test PAR SESSION (jamais aleatoire) : voir src/utils/config.py.

Usage:
    python -m src.training.train_classical
"""
from __future__ import annotations

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from src.models.classical import build_registry
from src.training.evaluate import collect_results, save_run
from src.utils.config import (
    DATA_FEATURES,
    GROUP_COL,
    MODELS_DIR,
    REPORTS_DIR,
    TEST_SESSION,
)
from src.utils.labels import STAGE1_COL, STAGE2_COL, add_labels, shots_only

FEATURE_COLS = [
    "mean", "std", "min", "max", "peak_to_peak", "peak_idx", "peak_amplitude",
    "energy", "abs_mean_dev", "clip_frac", "zero_crossing_rate", "rise_time_idx",
    "skewness", "kurtosis", "dominant_freq_bin", "spectral_centroid",
    "spectral_energy_low", "spectral_energy_mid", "spectral_energy_high",
    "spectral_flatness", "spectral_energy_total",
]


def _split(df: pd.DataFrame):
    train = df[df[GROUP_COL].astype(str) != TEST_SESSION]
    test = df[df[GROUP_COL].astype(str) == TEST_SESSION]
    return train, test


def run_stage(df: pd.DataFrame, stage: str, target_col: str, report_dir, models_dir):
    train, test = _split(df)
    print(f"\n=== {stage} === train={len(train)} test={len(test)}")

    X_train = train[FEATURE_COLS].to_numpy(dtype=float)
    X_test = test[FEATURE_COLS].to_numpy(dtype=float)

    le = LabelEncoder()
    y_train = le.fit_transform(train[target_col])
    y_test = le.transform(test[target_col])
    labels = list(range(len(le.classes_)))

    registry = build_registry(n_classes=len(le.classes_))
    best_name, best_f1 = None, -1.0
    stage_dir = models_dir / stage
    stage_dir.mkdir(parents=True, exist_ok=True)

    for name, pipe in registry.items():
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        result = save_run(report_dir, stage, name, y_test, y_pred, labels)
        print(f"  {name:20s} acc={result['accuracy']:.3f}  f1_macro={result['f1_macro']:.3f}")
        # chaque modele est sauvegarde (pas seulement le meilleur) pour permettre
        # a l'app Streamlit de comparer leurs predictions sur un nouvel exemple.
        joblib.dump({"model": pipe, "label_encoder": le, "features": FEATURE_COLS},
                    stage_dir / f"{name}.joblib")
        if result["f1_macro"] > best_f1:
            best_f1, best_name = result["f1_macro"], name

    with open(stage_dir / "best_model.txt", "w") as f:
        f.write(best_name)
    print(f"  -> meilleur modele: {best_name} (f1_macro={best_f1:.3f}), tous les modeles sauvegardes dans {stage_dir}")

    return collect_results(report_dir, stage)


def main():
    df = pd.read_csv(DATA_FEATURES)
    df = add_labels(df)

    report_dir = REPORTS_DIR / "classical"
    models_dir = MODELS_DIR

    res1 = run_stage(df, "stage1_is_shot", STAGE1_COL, report_dir, models_dir)
    res2 = run_stage(shots_only(df), "stage2_weapon", STAGE2_COL, report_dir, models_dir)

    print("\n=== Tableau comparatif — Etage 1 (tir vs non-tir) ===")
    print(res1.to_string(index=False))
    print("\n=== Tableau comparatif — Etage 2 (identification de l'arme) ===")
    print(res2.to_string(index=False))

    combined = pd.concat([res1, res2], ignore_index=True)
    out_csv = report_dir / "comparison_classical.csv"
    combined.to_csv(out_csv, index=False)
    print(f"\nTableau combine ecrit dans {out_csv}")


if __name__ == "__main__":
    main()
