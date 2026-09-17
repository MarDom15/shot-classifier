"""Fonctions communes d'evaluation : metriques, matrice de confusion, sauvegarde."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def compute_metrics(y_true, y_pred, labels=None) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "n_test": len(y_true),
    }


def save_run(
    report_dir: Path,
    stage: str,
    model_name: str,
    y_true,
    y_pred,
    labels: list,
) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    metrics = compute_metrics(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    result = {
        "stage": stage,
        "model": model_name,
        **metrics,
        "labels": labels,
        "confusion_matrix": cm.tolist(),
    }
    out_path = report_dir / f"{stage}__{model_name}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    report_txt = classification_report(y_true, y_pred, labels=labels, zero_division=0)
    with open(report_dir / f"{stage}__{model_name}.txt", "w") as f:
        f.write(report_txt)

    return result


def collect_results(report_dir: Path, stage: str) -> pd.DataFrame:
    rows = []
    for p in sorted(report_dir.glob(f"{stage}__*.json")):
        with open(p) as f:
            r = json.load(f)
        rows.append({
            "stage": r["stage"],
            "model": r["model"],
            "accuracy": r["accuracy"],
            "balanced_accuracy": r["balanced_accuracy"],
            "f1_macro": r["f1_macro"],
            "precision_macro": r["precision_macro"],
            "recall_macro": r["recall_macro"],
            "n_test": r["n_test"],
        })
    return pd.DataFrame(rows).sort_values("f1_macro", ascending=False).reset_index(drop=True)
