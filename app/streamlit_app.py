"""App Streamlit : demo de classification + monitoring.

Lancement local :
    streamlit run app/streamlit_app.py

Lancement via Docker :
    docker compose up
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models.inference import predict_pipeline
from src.monitoring.metrics import (
    PREDICTION_LATENCY,
    PREDICTIONS_TOTAL,
    start_metrics_server,
)
from src.utils.config import DATA_FEATURES, DATA_WAVEFORMS, REPORTS_DIR

LOG_PATH = ROOT / "monitoring" / "prediction_log.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Streamlit ré-exécute tout ce script à chaque interaction : start_metrics_server
# ignore silencieusement le cas où le port est déjà pris par un rerun précédent.
start_metrics_server(8000)

st.set_page_config(page_title="Classification des tirs", page_icon="🎯", layout="wide")

# ----------------------------------------------------------------------
# i18n : dictionnaire de chaines FR/EN. Le pipeline et les donnees restent
# identiques quelle que soit la langue choisie ; seul l'affichage change.
STRINGS = {
    "fr": {
        "title": "🎯 Classification des tirs — démonstrateur",
        "caption": "Prototype de recherche : détecte un impact (tir vs pierre) puis identifie l'arme, "
                   "à partir d'une forme d'onde brute de 512 échantillons ADC 8 bits.",
        "tab_predict": "🔮 Prédiction",
        "tab_compare": "📊 Comparaison des modèles",
        "tab_monitor": "🩺 Monitoring",
        "tab_about": "ℹ️ À propos",
        "predict_subheader": "Tester une forme d'onde",
        "source_radio": "Source de la forme d'onde",
        "source_dataset": "Exemple du jeu de données",
        "source_paste": "Coller 512 valeurs hexadécimales",
        "choose_event": "Choisir un événement",
        "paste_label": "512 octets hexadécimaux séparés par des espaces",
        "paste_placeholder": "B0 B9 B5 A0 90 81 69 64 ...",
        "invalid_format": "Format invalide : attendu des octets hexadécimaux séparés par des espaces.",
        "sample_count_warning": "{n} échantillons fournis (512 attendus) — la prédiction peut être imprécise.",
        "predict_button": "Lancer la prédiction",
        "predict_spinner": "Inférence en cours...",
        "stage1_header": "**Étage 1 — Tir vs non-tir**",
        "shot_detected": "🔫 Tir détecté",
        "non_shot_detected": "🪨 Impact non balistique (pierre)",
        "model_used": "{label}  \n_Modèle utilisé : {model}_",
        "non_shot_bar": "Non-tir",
        "shot_bar": "Tir",
        "expander_stage1": "Voir tous les modèles (étage 1)",
        "stage2_header": "**Étage 2 — Identification de l'arme**",
        "stage2_not_triggered": "Non déclenché : l'étage 1 n'a pas détecté de tir.",
        "weapon_predicted": "Arme prédite : **{label}**  \n_Modèle utilisé : {model}_",
        "expander_stage2": "Voir tous les modèles (étage 2)",
        "true_label": "Étiquette réelle (jeu de données) : **{label}**",
        "compare_subheader": "Comparaison des modèles entraînés",
        "stage_selectbox": "Étage",
        "compare_caption": "F1 macro calculé sur la session tenue à l'écart de l'entraînement (validation par session, "
                            "pas de tirage aléatoire) — voir CAHIER_DES_CHARGES.md, section méthodologie.",
        "compare_missing": "Aucun résultat trouvé. Lancez d'abord : "
                            "`python -m src.training.train_classical && python -m src.training.train_cnn "
                            "&& python -m src.training.compare_models`",
        "monitor_subheader": "Monitoring du modèle en production",
        "predictions_logged": "Prédictions enregistrées (cette instance)",
        "stage1_distribution": "**Répartition des prédictions étage 1 (tir / non-tir)**",
        "no_predictions": "Aucune prédiction enregistrée pour l'instant — utilisez l'onglet Prédiction.",
        "drift_header": "**Dérive des données (data drift)**",
        "drift_caption": "Compare la distribution des caractéristiques du trafic reçu à celle du jeu d'entraînement. "
                          "Nécessite un historique de prédictions suffisant ; voir `src/monitoring/drift.py`.",
        "drift_button": "Générer un rapport de dérive (Evidently)",
        "drift_success": "Rapport généré : {path}",
        "drift_error": "Impossible de générer le rapport : {error}",
        "about_text": """
        Ce démonstrateur fait partie d'un projet de recherche appliquée sur la classification
        de tirs à partir de signaux d'impact capteur (voir `CAHIER_DES_CHARGES.md` et
        `README.fr.md` à la racine du dépôt pour le contexte complet, les limites connues et
        la méthodologie).

        **Architecture du modèle** : classification en deux étages — détection tir/non-tir,
        puis identification de l'arme (G36 / MP7 / P8) — pour ne pas noyer la classe témoin
        (peu représentée) dans un problème multiclasse déséquilibré.

        **Avertissement** : jeu de données de recherche de taille modeste (397 événements).
        Les performances de l'étage 2 (identification de l'arme) sont fragiles hors des
        conditions d'enregistrement d'origine — voir la section "Limites" du cahier des charges.
        """,
    },
    "en": {
        "title": "🎯 Shot Classification — demo",
        "caption": "Research prototype: detects an impact (shot vs rock) then identifies the weapon, "
                   "from a raw waveform of 512 8-bit ADC samples.",
        "tab_predict": "🔮 Prediction",
        "tab_compare": "📊 Model comparison",
        "tab_monitor": "🩺 Monitoring",
        "tab_about": "ℹ️ About",
        "predict_subheader": "Test a waveform",
        "source_radio": "Waveform source",
        "source_dataset": "Example from the dataset",
        "source_paste": "Paste 512 hexadecimal values",
        "choose_event": "Choose an event",
        "paste_label": "512 hexadecimal bytes separated by spaces",
        "paste_placeholder": "B0 B9 B5 A0 90 81 69 64 ...",
        "invalid_format": "Invalid format: expected hexadecimal bytes separated by spaces.",
        "sample_count_warning": "{n} samples provided (512 expected) — the prediction may be inaccurate.",
        "predict_button": "Run prediction",
        "predict_spinner": "Running inference...",
        "stage1_header": "**Stage 1 — Shot vs non-shot**",
        "shot_detected": "🔫 Shot detected",
        "non_shot_detected": "🪨 Non-ballistic impact (rock)",
        "model_used": "{label}  \n_Model used: {model}_",
        "non_shot_bar": "Non-shot",
        "shot_bar": "Shot",
        "expander_stage1": "See all models (stage 1)",
        "stage2_header": "**Stage 2 — Weapon identification**",
        "stage2_not_triggered": "Not triggered: stage 1 did not detect a shot.",
        "weapon_predicted": "Predicted weapon: **{label}**  \n_Model used: {model}_",
        "expander_stage2": "See all models (stage 2)",
        "true_label": "True label (dataset): **{label}**",
        "compare_subheader": "Comparison of trained models",
        "stage_selectbox": "Stage",
        "compare_caption": "F1 macro computed on the session held out from training (per-session validation, "
                            "no random split) — see CAHIER_DES_CHARGES.md, methodology section.",
        "compare_missing": "No results found. Run this first: "
                            "`python -m src.training.train_classical && python -m src.training.train_cnn "
                            "&& python -m src.training.compare_models`",
        "monitor_subheader": "Production model monitoring",
        "predictions_logged": "Predictions logged (this instance)",
        "stage1_distribution": "**Stage 1 prediction breakdown (shot / non-shot)**",
        "no_predictions": "No predictions logged yet — use the Prediction tab.",
        "drift_header": "**Data drift**",
        "drift_caption": "Compares the feature distribution of incoming traffic to the training set. "
                          "Requires a sufficient prediction history; see `src/monitoring/drift.py`.",
        "drift_button": "Generate a drift report (Evidently)",
        "drift_success": "Report generated: {path}",
        "drift_error": "Could not generate the report: {error}",
        "about_text": """
        This demo is part of an applied research project on classifying shots from
        sensor impact signals (see `CAHIER_DES_CHARGES.md` and `README.md` at the
        root of the repository for the full context, known limitations and methodology).

        **Model architecture**: two-stage classification — shot/non-shot detection,
        then weapon identification (G36 / MP7 / P8) — to avoid drowning the (scarce)
        control class in an imbalanced multiclass problem.

        **Disclaimer**: modest research dataset (397 events). Stage 2 (weapon
        identification) performance is fragile outside the original recording
        conditions — see the "Limitations" section of the specification document.
        """,
    },
}

LANGS = {"Français": "fr", "English": "en"}
lang_choice = st.sidebar.radio("🌐 Langue / Language", list(LANGS.keys()))
LANG = LANGS[lang_choice]


def t(key: str, **kwargs) -> str:
    text = STRINGS[LANG][key]
    return text.format(**kwargs) if kwargs else text


def log_prediction(entry: dict):
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_log() -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame(columns=["timestamp", "stage1_label", "stage2_label", "source"])
    rows = [json.loads(line) for line in LOG_PATH.read_text().splitlines() if line.strip()]
    return pd.DataFrame(rows)


@st.cache_data
def load_reference_data():
    df = pd.read_csv(DATA_WAVEFORMS)
    feat = pd.read_csv(DATA_FEATURES)
    return df, feat


st.title(t("title"))
st.caption(t("caption"))

tab_predict, tab_compare, tab_monitor, tab_about = st.tabs(
    [t("tab_predict"), t("tab_compare"), t("tab_monitor"), t("tab_about")]
)

# ----------------------------------------------------------------------
with tab_predict:
    st.subheader(t("predict_subheader"))
    df_wave, _ = load_reference_data()
    scols = [c for c in df_wave.columns if c.startswith("s") and c[1:].isdigit()]

    mode = st.radio(
        t("source_radio"),
        [t("source_dataset"), t("source_paste")],
        horizontal=True,
    )

    values = None
    true_label = None

    if mode == t("source_dataset"):
        idx = st.selectbox(
            t("choose_event"),
            df_wave.index,
            format_func=lambda i: f"{df_wave.loc[i, 'weapon']} / {df_wave.loc[i, 'mode']} / "
                                   f"{df_wave.loc[i, 'distance_m']}m — {df_wave.loc[i, 'session']}/{df_wave.loc[i, 'file']}",
        )
        row = df_wave.loc[idx]
        values = row[scols].astype(int).tolist()
        true_label = row["weapon"]
    else:
        raw_text = st.text_area(t("paste_label"), height=120, placeholder=t("paste_placeholder"))
        if raw_text.strip():
            try:
                values = [int(v, 16) for v in raw_text.split()]
            except ValueError:
                st.error(t("invalid_format"))

    if values is not None:
        st.line_chart(pd.DataFrame({"amplitude": values}))
        if len(values) != 512:
            st.warning(t("sample_count_warning", n=len(values)))

        if st.button(t("predict_button"), type="primary"):
            with st.spinner(t("predict_spinner")):
                _predict_start = time.perf_counter()
                out = predict_pipeline(values)
                PREDICTION_LATENCY.observe(time.perf_counter() - _predict_start)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(t("stage1_header"))
                best1 = out["stage1_best"]
                r1 = out["stage1"][best1]
                label_txt = t("shot_detected") if str(r1["label"]) == "1" else t("non_shot_detected")
                st.success(t("model_used", label=label_txt, model=best1))
                if r1.get("proba"):
                    st.bar_chart(pd.Series({t("non_shot_bar"): r1["proba"].get(0, r1["proba"].get("0", 0)),
                                             t("shot_bar"): r1["proba"].get(1, r1["proba"].get("1", 0))}))
                with st.expander(t("expander_stage1")):
                    st.json(out["stage1"])

            with col2:
                st.markdown(t("stage2_header"))
                if out["stage2"] is None:
                    st.info(t("stage2_not_triggered"))
                else:
                    best2 = out["stage2_best"]
                    r2 = out["stage2"][best2]
                    st.success(t("weapon_predicted", label=r2["label"], model=best2))
                    if r2.get("proba"):
                        st.bar_chart(pd.Series(r2["proba"]))
                    with st.expander(t("expander_stage2")):
                        st.json(out["stage2"])

            if true_label is not None:
                st.caption(t("true_label", label=true_label))

            stage1_label = out["stage1"][out["stage1_best"]]["label"]
            stage2_label = out["stage2"][out["stage2_best"]]["label"] if out["stage2"] else "none"
            PREDICTIONS_TOTAL.labels(stage1_label=str(stage1_label), weapon=str(stage2_label)).inc()

            log_prediction({
                "source": mode,
                "true_label": str(true_label) if true_label is not None else None,
                "stage1_label": stage1_label,
                "stage1_model": out["stage1_best"],
                "stage2_label": out["stage2"][out["stage2_best"]]["label"] if out["stage2"] else None,
                "stage2_model": out.get("stage2_best"),
            })

# ----------------------------------------------------------------------
with tab_compare:
    st.subheader(t("compare_subheader"))
    cmp_path = REPORTS_DIR / "model_comparison_final.csv"
    if cmp_path.exists():
        cmp_df = pd.read_csv(cmp_path)
        stage_choice = st.selectbox(t("stage_selectbox"), cmp_df["stage"].unique())
        sub = cmp_df[cmp_df.stage == stage_choice].sort_values("f1_macro", ascending=False)
        st.dataframe(sub.set_index("model")[["accuracy", "f1_macro", "balanced_accuracy", "precision_macro", "recall_macro"]],
                     use_container_width=True)
        st.bar_chart(sub.set_index("model")["f1_macro"])
        st.caption(t("compare_caption"))
    else:
        st.warning(t("compare_missing"))

# ----------------------------------------------------------------------
with tab_monitor:
    st.subheader(t("monitor_subheader"))
    log_df = load_log()
    st.metric(t("predictions_logged"), len(log_df))

    if len(log_df):
        st.dataframe(log_df.sort_values("timestamp", ascending=False), use_container_width=True)
        st.markdown(t("stage1_distribution"))
        st.bar_chart(log_df["stage1_label"].value_counts())
    else:
        st.info(t("no_predictions"))

    st.divider()
    st.markdown(t("drift_header"))
    st.caption(t("drift_caption"))
    if st.button(t("drift_button")):
        try:
            from src.monitoring.drift import generate_drift_report
            report_path = generate_drift_report()
            st.success(t("drift_success", path=report_path))
            st.components.v1.html(Path(report_path).read_text(), height=600, scrolling=True)
        except Exception as e:
            st.error(t("drift_error", error=e))

# ----------------------------------------------------------------------
with tab_about:
    st.markdown(t("about_text"))
