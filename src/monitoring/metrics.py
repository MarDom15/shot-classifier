"""Definitions Prometheus partagees pour le monitoring du pipeline.

Chaque service (app Streamlit, agent) expose ses metriques sur son propre
port HTTP dedie (voir docker-compose.yml) via prometheus_client.start_http_server ;
Prometheus les scrape independamment (monitoring/prometheus.yml). Les noms
et libelles sont centralises ici pour eviter toute divergence entre services.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# --- App Streamlit (predictions interactives, port 8000) ---
PREDICTIONS_TOTAL = Counter(
    "shot_classifier_predictions_total",
    "Nombre de predictions effectuees par l'app de demonstration",
    ["stage1_label", "weapon"],
)
PREDICTION_LATENCY = Histogram(
    "shot_classifier_prediction_latency_seconds",
    "Temps d'inference du pipeline complet (etage 1, + etage 2 si tir detecte)",
)

# --- Agent autonome (cycles d'entrainement, port 8001) ---
AGENT_CYCLES_TOTAL = Counter(
    "shot_classifier_agent_cycles_total",
    "Nombre de cycles executes par l'agent, par statut final",
    ["status"],
)
AGENT_ROLLBACKS_TOTAL = Counter(
    "shot_classifier_agent_rollbacks_total",
    "Nombre de rollbacks automatiques declenches suite a une regression",
)
AGENT_F1_MACRO = Gauge(
    "shot_classifier_agent_f1_macro",
    "F1 macro du meilleur modele au dernier cycle reussi, par etage",
    ["stage"],
)
AGENT_DATASET_EVENTS = Gauge(
    "shot_classifier_agent_dataset_events",
    "Nombre d'evenements dans le jeu de donnees au dernier cycle",
)
AGENT_CYCLE_DURATION = Histogram(
    "shot_classifier_agent_cycle_duration_seconds",
    "Duree totale d'un cycle de l'agent (donnees + entrainement + derive)",
)
AGENT_LAST_CYCLE_TIMESTAMP = Gauge(
    "shot_classifier_agent_last_cycle_timestamp",
    "Horodatage Unix (secondes) de la fin du dernier cycle",
)


def start_metrics_server(port: int) -> None:
    """Demarre le serveur HTTP /metrics, en ignorant silencieusement le cas
    ou il tourne deja sur ce port (ex. re-execution du script Streamlit)."""
    from prometheus_client import start_http_server
    try:
        start_http_server(port)
    except OSError:
        pass
