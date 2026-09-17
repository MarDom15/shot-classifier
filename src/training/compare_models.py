"""Agrege les resultats des modeles classiques et du CNN 1D en un tableau
comparatif final, et produit un graphique de synthese.

A executer apres train_classical.py et train_cnn.py :
    python -m src.training.compare_models
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.training.evaluate import collect_results
from src.utils.config import REPORTS_DIR

STAGE_LABELS = {
    "stage1_is_shot": "Étage 1 — tir vs non-tir",
    "stage2_weapon": "Étage 2 — identification de l'arme",
}

# Palette categorique fixe (Okabe-Ito, accessible daltonisme)
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#999999", "#F0E442"]


def main():
    frames = []
    for stage, label in STAGE_LABELS.items():
        classical = collect_results(REPORTS_DIR / "classical", stage)
        cnn = collect_results(REPORTS_DIR / "cnn", stage)
        combined = pd.concat([classical, cnn], ignore_index=True).sort_values("f1_macro", ascending=False)
        frames.append(combined)
        print(f"\n=== {label} ===")
        print(combined.to_string(index=False))

    full = pd.concat(frames, ignore_index=True)
    out_csv = REPORTS_DIR / "model_comparison_final.csv"
    full.to_csv(out_csv, index=False)
    print(f"\nTableau final: {out_csv}")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), dpi=150)
    BASE_COLOR = "#8C9BAB"      # gris-bleu neutre pour les modeles courants
    BEST_COLOR = "#0072B2"      # accent unique reserve au meilleur modele
    for ax, stage in zip(axes, STAGE_LABELS):
        sub = full[full.stage == stage].sort_values("f1_macro", ascending=True)
        colors = [BEST_COLOR if i == len(sub) - 1 else BASE_COLOR for i in range(len(sub))]
        bars = ax.barh(sub["model"], sub["f1_macro"], color=colors)
        for b, v in zip(bars, sub["f1_macro"]):
            ax.text(v + 0.01, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=9)
        ax.set_xlim(0, 1.0)
        ax.set_xlabel("F1 macro (jeu de test = session 19090822)")
        ax.set_title(STAGE_LABELS[stage], fontsize=11, loc="left")
        ax.grid(axis="x", color="#e5e5e5", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    fig.suptitle("Comparaison des modèles par étage de classification", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig_path = REPORTS_DIR / "model_comparison_final.png"
    fig.savefig(fig_path, bbox_inches="tight")
    print(f"Graphique: {fig_path}")


if __name__ == "__main__":
    main()
