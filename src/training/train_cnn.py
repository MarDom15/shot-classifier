"""Entraine le CNN 1D directement sur les 512 echantillons bruts.

Meme decoupage que les modeles classiques (par session, voir
src/utils/config.py) afin que les resultats des deux approches soient
comparables dans le tableau final (src/training/compare_models.py).

Usage:
    python -m src.training.train_cnn
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch import nn

from src.data.parse_raw import sample_columns
from src.models.cnn1d import Shot1DCNN
from src.training.evaluate import save_run
from src.utils.config import (
    DATA_WAVEFORMS,
    GROUP_COL,
    MODELS_DIR,
    RANDOM_SEED,
    REPORTS_DIR,
    TEST_SESSION,
)
from src.utils.labels import STAGE1_COL, STAGE2_COL, add_labels, shots_only

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def _split(df: pd.DataFrame):
    train = df[df[GROUP_COL].astype(str) != TEST_SESSION]
    test = df[df[GROUP_COL].astype(str) == TEST_SESSION]
    return train, test


def _to_tensor(x, dtype=torch.float32):
    return torch.tensor(x, dtype=dtype)


def train_one_stage(df: pd.DataFrame, stage: str, target_col: str, report_dir, models_dir,
                     epochs: int = 60, batch_size: int = 16, lr: float = 1e-3):
    # Reseede a chaque appel (pas seulement a l'import du module) : l'agent
    # autonome (src/agent/ml_agent.py) appelle main() plusieurs fois dans le
    # meme process au long de sa boucle "watch", et sans ce reset chaque
    # cycle repartirait d'un etat aleatoire different -> resultats non reproductibles.
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    scols = sample_columns(df)
    train_full, test = _split(df)
    print(f"\n=== {stage} (CNN) === train_full={len(train_full)} test={len(test)}")

    le = LabelEncoder()
    y_train_full = le.fit_transform(train_full[target_col])
    y_test = le.transform(test[target_col])
    n_classes = len(le.classes_)

    # sous-ensemble de validation interne (uniquement pour l'early stopping),
    # prelevee dans le train — le test (autre session) ne sert jamais a arreter l'entrainement.
    idx = np.arange(len(train_full))
    strat = y_train_full if min(np.bincount(y_train_full)) >= 2 else None
    train_idx, val_idx = train_test_split(idx, test_size=0.2, random_state=RANDOM_SEED, stratify=strat)

    X_all = train_full[scols].to_numpy(dtype=float)
    X_test = test[scols].to_numpy(dtype=float)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_all[train_idx])
    X_val = scaler.transform(X_all[val_idx])
    X_test_s = scaler.transform(X_test)

    y_train = y_train_full[train_idx]
    y_val = y_train_full[val_idx]

    model = Shot1DCNN(n_classes=n_classes).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    class_counts = np.bincount(y_train, minlength=n_classes)
    class_weights = torch.tensor(len(y_train) / (n_classes * np.maximum(class_counts, 1)), dtype=torch.float32)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(DEVICE))

    X_train_t = _to_tensor(X_train).to(DEVICE)
    y_train_t = _to_tensor(y_train, dtype=torch.long).to(DEVICE)
    X_val_t = _to_tensor(X_val).to(DEVICE)
    y_val_t = _to_tensor(y_val, dtype=torch.long).to(DEVICE)
    X_test_t = _to_tensor(X_test_s).to(DEVICE)

    best_val_loss = float("inf")
    best_state = None
    patience, bad_epochs = 12, 0

    n = len(X_train_t)
    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n)
        total_loss = 0.0
        for i in range(0, n, batch_size):
            batch_idx = perm[i:i + batch_size]
            xb, yb = X_train_t[batch_idx], y_train_t[batch_idx]
            opt.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            opt.step()
            total_loss += loss.item() * len(batch_idx)

        model.eval()
        with torch.no_grad():
            val_out = model(X_val_t)
            val_loss = criterion(val_out, y_val_t).item()

        if val_loss < best_val_loss - 1e-4:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                print(f"  early stopping a l'epoch {epoch} (val_loss={val_loss:.4f})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        y_pred = model(X_test_t).argmax(dim=1).cpu().numpy()

    labels = list(range(n_classes))
    result = save_run(report_dir, stage, "cnn1d", y_test, y_pred, labels)
    print(f"  cnn1d                acc={result['accuracy']:.3f}  f1_macro={result['f1_macro']:.3f}")

    stage_dir = models_dir / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": model.state_dict(),
        "n_classes": n_classes,
        "scaler_mean": scaler.mean_,
        "scaler_scale": scaler.scale_,
        "label_encoder_classes": le.classes_,
    }, stage_dir / "cnn1d.pt")

    return result


def main():
    df = pd.read_csv(DATA_WAVEFORMS)
    df = add_labels(df)

    report_dir = REPORTS_DIR / "cnn"
    models_dir = MODELS_DIR

    train_one_stage(df, "stage1_is_shot", STAGE1_COL, report_dir, models_dir)
    train_one_stage(shots_only(df), "stage2_weapon", STAGE2_COL, report_dir, models_dir)


if __name__ == "__main__":
    main()
