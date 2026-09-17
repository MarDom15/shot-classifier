"""Agent ML/DL autonome — orchestre le cycle de vie complet du pipeline sans
intervention manuelle : ingestion des nouvelles données, reconstruction du
jeu de features, entraînement des 9 modèles sur les 2 étages, sélection du
meilleur modèle par étage, sauvegarde avec rollback, détection de dérive,
et journalisation d'un rapport de run.

Deux modes :
    run    : exécute un cycle complet une seule fois, puis s'arrête.
    watch  : boucle indéfiniment, en ré-exécutant un cycle complet à
             intervalle régulier (et en reprenant immédiatement si de
             nouvelles données apparaissent dans data/raw/incoming/).

Usage :
    python -m src.agent.ml_agent run
    python -m src.agent.ml_agent watch --interval 21600   # toutes les 6h

Pour déposer de nouvelles données : placer une nouvelle archive .zip (même
structure que l'archive d'origine) dans data/raw/incoming/. Elle sera prise
en compte automatiquement au prochain cycle, fusionnée avec les données
existantes (déduplication automatique), et déclenchera un ré-entraînement.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from src.data import features as features_mod
from src.data.import_field_captures import build_field_archive
from src.data.parse_raw import parse_zips
from src.monitoring.metrics import (
    AGENT_CYCLE_DURATION,
    AGENT_CYCLES_TOTAL,
    AGENT_DATASET_EVENTS,
    AGENT_F1_MACRO,
    AGENT_LAST_CYCLE_TIMESTAMP,
    AGENT_ROLLBACKS_TOTAL,
    start_metrics_server,
)
from src.training import compare_models, train_classical, train_cnn
from src.utils.config import (
    DATA_FEATURES,
    DATA_RAW,
    DATA_WAVEFORMS,
    MODELS_DIR,
    REPORTS_DIR,
    ROOT,
)

METRICS_PORT = 8001

INCOMING_DIR = DATA_RAW.parent / "incoming"
HISTORY_DIR = MODELS_DIR.parent / "models_store_history"
AGENT_LOG_DIR = REPORTS_DIR / "agent"
AGENT_LOG_PATH = AGENT_LOG_DIR / "run_log.jsonl"

# Captures de l'app terrain (field_app/) confirmees par un operateur :
# reconverties en archive .zip a chaque cycle et deposees dans
# data/raw/incoming/, pour etre reprises comme n'importe quelle autre
# archive sans traitement particulier (voir src/data/import_field_captures.py).
FIELD_DATA_DIR = ROOT / "field_app" / "data"
FIELD_EXPORT_ZIP = INCOMING_DIR / "field_export.zip"

STAGES = ["stage1_is_shot", "stage2_weapon"]


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _log(message: str) -> None:
    print(f"[agent] {message}", flush=True)


def discover_source_zips() -> list[Path]:
    """Archive d'origine + toute nouvelle archive deposee dans incoming/."""
    zips = [DATA_RAW]
    if INCOMING_DIR.exists():
        zips += sorted(INCOMING_DIR.glob("*.zip"))
    return [z for z in zips if z.exists()]


def import_field_data() -> dict:
    """Reconvertit les captures terrain confirmees (field_app/) en archive
    .zip dans incoming/, si le dossier existe (l'app terrain n'a peut-etre
    jamais tourne sur cette machine)."""
    if not FIELD_DATA_DIR.exists():
        return {"available": False}
    stats = build_field_archive(FIELD_DATA_DIR, FIELD_EXPORT_ZIP)
    if stats["included"]:
        _log(f"donnees terrain importees: {stats['included']} capture(s) confirmee(s) {stats['weapons']}")
    return {"available": True, **stats}


def build_dataset() -> dict:
    """Etape 1 : (re)construit les CSV a partir de toutes les archives sources."""
    field_import = import_field_data()
    zips = discover_source_zips()
    result = parse_zips(zips)
    DATA_WAVEFORMS.parent.mkdir(parents=True, exist_ok=True)
    result.df.to_csv(DATA_WAVEFORMS, index=False)

    feat_df = features_mod.compute_features(result.df)
    feat_df.to_csv(DATA_FEATURES, index=False)

    info = {
        "n_source_archives": len(zips),
        "source_archives": [str(z) for z in zips],
        "n_events": len(result.df),
        "n_anomalies": len(result.anomalies),
        "anomalies": result.anomalies,
        "field_import": field_import,
    }
    _log(f"dataset reconstruit: {info['n_events']} evenements depuis {info['n_source_archives']} archive(s) "
         f"({info['n_anomalies']} anomalie(s))")
    return info


def snapshot_models(tag: str) -> Path | None:
    """Sauvegarde une copie horodatee des modeles courants avant ecrasement,
    pour permettre un rollback si le nouvel entrainement regresse."""
    if not MODELS_DIR.exists() or not any(MODELS_DIR.iterdir()):
        return None
    dest = HISTORY_DIR / tag
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(MODELS_DIR, dest, dirs_exist_ok=True)
    _log(f"snapshot des modeles actuels sauvegarde: {dest}")
    return dest


def rollback_models(snapshot_dir: Path) -> None:
    if MODELS_DIR.exists():
        shutil.rmtree(MODELS_DIR)
    shutil.copytree(snapshot_dir, MODELS_DIR)
    _log(f"rollback effectue depuis {snapshot_dir}")


def _best_f1_per_stage(comparison_csv: Path) -> dict[str, float]:
    import pandas as pd
    if not comparison_csv.exists():
        return {}
    df = pd.read_csv(comparison_csv)
    return df.groupby("stage")["f1_macro"].max().to_dict()


def train_and_select() -> dict:
    """Etape 2 : entraine tous les modeles (classiques + CNN) et regenere la
    comparaison. Un snapshot est pris avant d'ecraser les modeles courants ;
    si la performance regresse significativement, un rollback automatique
    est declenche."""
    comparison_csv = REPORTS_DIR / "model_comparison_final.csv"
    previous_best = _best_f1_per_stage(comparison_csv)

    tag = _now_tag()
    snapshot_dir = snapshot_models(tag)

    train_classical.main()
    train_cnn.main()
    compare_models.main()

    new_best = _best_f1_per_stage(comparison_csv)

    regressions = {}
    REGRESSION_TOLERANCE = 0.02  # tolere une petite fluctuation (re-entrainement non deterministe)
    for stage in STAGES:
        prev = previous_best.get(stage)
        new = new_best.get(stage)
        if prev is not None and new is not None and new < prev - REGRESSION_TOLERANCE:
            regressions[stage] = {"previous_f1_macro": prev, "new_f1_macro": new}

    rolled_back = False
    if regressions and snapshot_dir is not None:
        _log(f"regression detectee sur {list(regressions)} -> rollback automatique")
        rollback_models(snapshot_dir)
        rolled_back = True
    elif regressions:
        _log(f"regression detectee sur {list(regressions)} mais aucun snapshot disponible pour rollback")

    return {
        "snapshot": str(snapshot_dir) if snapshot_dir else None,
        "previous_best_f1": previous_best,
        "new_best_f1": new_best,
        "regressions": regressions,
        "rolled_back": rolled_back,
    }


def check_drift() -> dict:
    """Etape 3 : regenere le rapport de derive des donnees."""
    try:
        from src.monitoring.drift import generate_drift_report
        tag = _now_tag()
        out_path = AGENT_LOG_DIR / f"drift_{tag}.html"
        path = generate_drift_report(out_path)
        _log(f"rapport de derive genere: {path}")
        return {"status": "ok", "report": path}
    except Exception as e:  # pragma: no cover - defensif
        _log(f"echec de la generation du rapport de derive: {e}")
        return {"status": "error", "error": str(e)}


def run_once() -> dict:
    """Execute un cycle complet : donnees -> entrainement -> comparaison ->
    derive -> journal. Ne leve pas d'exception : toute erreur est capturee
    et journalisee pour que le mode `watch` puisse continuer a fonctionner."""
    tag = _now_tag()
    _log(f"=== debut du cycle {tag} ===")
    started = time.perf_counter()
    entry = {"tag": tag, "started_at": tag}
    try:
        entry["dataset"] = build_dataset()
        entry["training"] = train_and_select()
        entry["drift"] = check_drift()
        entry["status"] = "success"
    except Exception as e:
        entry["status"] = "error"
        entry["error"] = str(e)
        entry["traceback"] = traceback.format_exc()
        _log(f"ECHEC du cycle: {e}")

    AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(AGENT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    AGENT_CYCLES_TOTAL.labels(status=entry["status"]).inc()
    AGENT_CYCLE_DURATION.observe(time.perf_counter() - started)
    if entry["status"] == "success":
        AGENT_LAST_CYCLE_TIMESTAMP.set(time.time())
        AGENT_DATASET_EVENTS.set(entry["dataset"]["n_events"])
        for stage, f1 in entry["training"]["new_best_f1"].items():
            AGENT_F1_MACRO.labels(stage=stage).set(f1)
        if entry["training"]["rolled_back"]:
            AGENT_ROLLBACKS_TOTAL.inc()

    _log(f"=== fin du cycle {tag} (statut: {entry['status']}) ===")
    return entry


def watch(interval: int = 21600, max_cycles: int | None = None) -> None:
    """Boucle autonome : un cycle complet toutes les `interval` secondes.
    S'arrete apres `max_cycles` cycles si precise (utile pour les tests),
    sinon tourne indefiniment jusqu'a interruption (Ctrl+C / arret du conteneur)."""
    start_metrics_server(METRICS_PORT)
    _log(f"agent demarre en mode watch (intervalle={interval}s, metriques sur :{METRICS_PORT}/metrics). "
         "Ctrl+C pour arreter.")
    cycles = 0
    while True:
        run_once()
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            _log(f"nombre maximal de cycles atteint ({max_cycles}), arret.")
            break
        _log(f"prochain cycle dans {interval}s...")
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="Execute un cycle complet une seule fois.")

    watch_p = sub.add_parser("watch", help="Boucle autonome (retraining periodique).")
    watch_p.add_argument("--interval", type=int, default=21600, help="Secondes entre deux cycles (defaut 6h).")
    watch_p.add_argument("--max-cycles", type=int, default=None, help="Limite de cycles (debug/tests).")

    args = ap.parse_args()
    if args.command == "run":
        entry = run_once()
        raise SystemExit(0 if entry["status"] == "success" else 1)
    elif args.command == "watch":
        watch(interval=args.interval, max_cycles=args.max_cycles)


if __name__ == "__main__":
    main()
