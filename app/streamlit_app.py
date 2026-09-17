"""App Streamlit : demo de classification + monitoring.

Lancement local :
    streamlit run app/streamlit_app.py

Lancement via Docker :
    docker compose up
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models.inference import predict_pipeline
from src.utils.config import DATA_FEATURES, DATA_WAVEFORMS, REPORTS_DIR

LOG_PATH = ROOT / "monitoring" / "prediction_log.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Classification des tirs", page_icon="🎯", layout="wide")


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


st.title("🎯 Classification des tirs — démonstrateur")
st.caption(
    "Prototype de recherche : détecte un impact (tir vs pierre) puis identifie l'arme, "
    "à partir d'une forme d'onde brute de 512 échantillons ADC 8 bits."
)

tab_predict, tab_compare, tab_monitor, tab_about = st.tabs(
    ["🔮 Prédiction", "📊 Comparaison des modèles", "🩺 Monitoring", "ℹ️ À propos"]
)

# ----------------------------------------------------------------------
with tab_predict:
    st.subheader("Tester une forme d'onde")
    df_wave, _ = load_reference_data()
    scols = [c for c in df_wave.columns if c.startswith("s") and c[1:].isdigit()]

    mode = st.radio(
        "Source de la forme d'onde",
        ["Exemple du jeu de données", "Coller 512 valeurs hexadécimales"],
        horizontal=True,
    )

    values = None
    true_label = None

    if mode == "Exemple du jeu de données":
        idx = st.selectbox(
            "Choisir un événement",
            df_wave.index,
            format_func=lambda i: f"{df_wave.loc[i, 'weapon']} / {df_wave.loc[i, 'mode']} / "
                                   f"{df_wave.loc[i, 'distance_m']}m — {df_wave.loc[i, 'session']}/{df_wave.loc[i, 'file']}",
        )
        row = df_wave.loc[idx]
        values = row[scols].astype(int).tolist()
        true_label = row["weapon"]
    else:
        raw_text = st.text_area("512 octets hexadécimaux séparés par des espaces", height=120,
                                 placeholder="B0 B9 B5 A0 90 81 69 64 ...")
        if raw_text.strip():
            try:
                values = [int(t, 16) for t in raw_text.split()]
            except ValueError:
                st.error("Format invalide : attendu des octets hexadécimaux séparés par des espaces.")

    if values is not None:
        st.line_chart(pd.DataFrame({"amplitude": values}))
        if len(values) != 512:
            st.warning(f"{len(values)} échantillons fournis (512 attendus) — la prédiction peut être imprécise.")

        if st.button("Lancer la prédiction", type="primary"):
            with st.spinner("Inférence en cours..."):
                out = predict_pipeline(values)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Étage 1 — Tir vs non-tir**")
                best1 = out["stage1_best"]
                r1 = out["stage1"][best1]
                label_txt = "🔫 Tir détecté" if str(r1["label"]) == "1" else "🪨 Impact non balistique (pierre)"
                st.success(f"{label_txt}  \n_Modèle utilisé : {best1}_")
                if r1.get("proba"):
                    st.bar_chart(pd.Series({"Non-tir": r1["proba"].get(0, r1["proba"].get("0", 0)),
                                             "Tir": r1["proba"].get(1, r1["proba"].get("1", 0))}))
                with st.expander("Voir tous les modèles (étage 1)"):
                    st.json(out["stage1"])

            with col2:
                st.markdown("**Étage 2 — Identification de l'arme**")
                if out["stage2"] is None:
                    st.info("Non déclenché : l'étage 1 n'a pas détecté de tir.")
                else:
                    best2 = out["stage2_best"]
                    r2 = out["stage2"][best2]
                    st.success(f"Arme prédite : **{r2['label']}**  \n_Modèle utilisé : {best2}_")
                    if r2.get("proba"):
                        st.bar_chart(pd.Series(r2["proba"]))
                    with st.expander("Voir tous les modèles (étage 2)"):
                        st.json(out["stage2"])

            if true_label is not None:
                st.caption(f"Étiquette réelle (jeu de données) : **{true_label}**")

            log_prediction({
                "source": mode,
                "true_label": str(true_label) if true_label is not None else None,
                "stage1_label": out["stage1"][out["stage1_best"]]["label"],
                "stage1_model": out["stage1_best"],
                "stage2_label": out["stage2"][out["stage2_best"]]["label"] if out["stage2"] else None,
                "stage2_model": out.get("stage2_best"),
            })

# ----------------------------------------------------------------------
with tab_compare:
    st.subheader("Comparaison des modèles entraînés")
    cmp_path = REPORTS_DIR / "model_comparison_final.csv"
    if cmp_path.exists():
        cmp_df = pd.read_csv(cmp_path)
        stage_choice = st.selectbox("Étage", cmp_df["stage"].unique())
        sub = cmp_df[cmp_df.stage == stage_choice].sort_values("f1_macro", ascending=False)
        st.dataframe(sub.set_index("model")[["accuracy", "f1_macro", "balanced_accuracy", "precision_macro", "recall_macro"]],
                     use_container_width=True)
        st.bar_chart(sub.set_index("model")["f1_macro"])
        st.caption(
            "F1 macro calculé sur la session tenue à l'écart de l'entraînement (validation par session, "
            "pas de tirage aléatoire) — voir CAHIER_DES_CHARGES.md, section méthodologie."
        )
    else:
        st.warning(
            "Aucun résultat trouvé. Lancez d'abord : "
            "`python -m src.training.train_classical && python -m src.training.train_cnn && python -m src.training.compare_models`"
        )

# ----------------------------------------------------------------------
with tab_monitor:
    st.subheader("Monitoring du modèle en production")
    log_df = load_log()
    st.metric("Prédictions enregistrées (cette instance)", len(log_df))

    if len(log_df):
        st.dataframe(log_df.sort_values("timestamp", ascending=False), use_container_width=True)
        st.markdown("**Répartition des prédictions étage 1 (tir / non-tir)**")
        st.bar_chart(log_df["stage1_label"].value_counts())
    else:
        st.info("Aucune prédiction enregistrée pour l'instant — utilisez l'onglet Prédiction.")

    st.divider()
    st.markdown("**Dérive des données (data drift)**")
    st.caption(
        "Compare la distribution des caractéristiques du trafic reçu à celle du jeu d'entraînement. "
        "Nécessite un historique de prédictions suffisant ; voir `src/monitoring/drift.py`."
    )
    if st.button("Générer un rapport de dérive (Evidently)"):
        try:
            from src.monitoring.drift import generate_drift_report
            report_path = generate_drift_report()
            st.success(f"Rapport généré : {report_path}")
            st.components.v1.html(Path(report_path).read_text(), height=600, scrolling=True)
        except Exception as e:
            st.error(f"Impossible de générer le rapport : {e}")

# ----------------------------------------------------------------------
with tab_about:
    st.markdown(
        """
        Ce démonstrateur fait partie d'un projet de recherche appliquée sur la classification
        de tirs à partir de signaux d'impact capteur (voir `CAHIER_DES_CHARGES.md` et
        `README.md` à la racine du dépôt pour le contexte complet, les limites connues et
        la méthodologie).

        **Architecture du modèle** : classification en deux étages — détection tir/non-tir,
        puis identification de l'arme (G36 / MP7 / P8) — pour ne pas noyer la classe témoin
        (peu représentée) dans un problème multiclasse déséquilibré.

        **Avertissement** : jeu de données de recherche de taille modeste (397 événements).
        Les performances de l'étage 2 (identification de l'arme) sont fragiles hors des
        conditions d'enregistrement d'origine — voir la section "Limites" du cahier des charges.
        """
    )
