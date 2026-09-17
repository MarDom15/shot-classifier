"""Service d'inference unifie : a partir d'une forme d'onde brute (512
valeurs 0-255), calcule les caracteristiques et interroge tous les modeles
sauvegardes (classiques + CNN) pour les deux etages de classification.

Utilise par l'app Streamlit (app/streamlit_app.py) et par les tests.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import torch

from src.data.features import compute_features
from src.models.cnn1d import Shot1DCNN
from src.utils.config import MODELS_DIR

STAGE1 = "stage1_is_shot"
STAGE2 = "stage2_weapon"


def _raw_to_df(values: list[int]) -> pd.DataFrame:
    if len(values) != 512:
        raise ValueError(f"512 echantillons attendus, {len(values)} recus.")
    row = {f"s{i:03d}": v for i, v in enumerate(values)}
    row.update({"session": "input", "folder": "input", "weapon": "?", "mode": "",
                "distance_m": None, "variant_D": False, "file": "input.txt",
                "label_prefix": "?", "event_index_in_file": 0, "n_events_in_file": 1,
                "n_samples_raw": 512, "extra_sample_flag": False, "filepath": "input"})
    return pd.DataFrame([row])


def list_available_models(stage: str) -> list[str]:
    stage_dir = MODELS_DIR / stage
    if not stage_dir.exists():
        return []
    names = [p.stem for p in stage_dir.glob("*.joblib")]
    if (stage_dir / "cnn1d.pt").exists():
        names.append("cnn1d")
    return sorted(names)


def best_model_name(stage: str) -> str | None:
    p = MODELS_DIR / stage / "best_model.txt"
    return p.read_text().strip() if p.exists() else None


def _predict_classical(stage: str, model_name: str, feat_row: pd.DataFrame):
    bundle = joblib.load(MODELS_DIR / stage / f"{model_name}.joblib")
    model, le, cols = bundle["model"], bundle["label_encoder"], bundle["features"]
    X = feat_row[cols].to_numpy(dtype=float)
    pred = model.predict(X)[0]
    label = le.inverse_transform([pred])[0]
    proba = None
    if hasattr(model, "predict_proba"):
        p = model.predict_proba(X)[0]
        proba = {cls: float(p[i]) for i, cls in enumerate(le.classes_)}
    return label, proba


def _predict_cnn(stage: str, values: list[int]):
    ckpt = torch.load(MODELS_DIR / stage / "cnn1d.pt", map_location="cpu", weights_only=False)
    model = Shot1DCNN(n_classes=ckpt["n_classes"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    x = (np.array(values, dtype=float) - ckpt["scaler_mean"]) / ckpt["scaler_scale"]
    xt = torch.tensor(x, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        logits = model(xt)
        proba_arr = torch.softmax(logits, dim=1).numpy()[0]
    classes = ckpt["label_encoder_classes"]
    pred_idx = int(np.argmax(proba_arr))
    label = classes[pred_idx]
    proba = {cls: float(proba_arr[i]) for i, cls in enumerate(classes)}
    return label, proba


def predict_all(values: list[int], stage: str) -> dict:
    """Retourne les predictions de tous les modeles disponibles pour un etage."""
    df = _raw_to_df(values)
    feat_row = compute_features(df)

    results = {}
    for name in list_available_models(stage):
        try:
            if name == "cnn1d":
                label, proba = _predict_cnn(stage, values)
            else:
                label, proba = _predict_classical(stage, name, feat_row)
            results[name] = {"label": str(label), "proba": proba}
        except Exception as e:  # pragma: no cover - defensif pour l'UI
            results[name] = {"label": None, "error": str(e)}
    return results


def predict_pipeline(values: list[int]) -> dict:
    """Predit d'abord tir/non-tir, puis (si tir) l'arme, avec tous les modeles."""
    stage1 = predict_all(values, STAGE1)
    out = {"stage1": stage1, "stage1_best": best_model_name(STAGE1)}

    best1 = stage1.get(best_model_name(STAGE1), {})
    # is_shot encode via LabelEncoder -> les classes sont [0,1] ; on considere
    # "tir" si le meilleur modele de l'etage 1 predit la classe 1.
    if str(best1.get("label")) == "1":
        stage2 = predict_all(values, STAGE2)
        out["stage2"] = stage2
        out["stage2_best"] = best_model_name(STAGE2)
    else:
        out["stage2"] = None
    return out
