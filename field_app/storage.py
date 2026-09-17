"""Stockage durable des captures et de leurs confirmations, pour permettre
une future amelioration des modeles a partir des donnees de terrain.

Deux fichiers JSON Lines, uniquement en ajout (append-only) : simple et
robuste (pas de reecriture sur place, donc pas de risque de corruption en
cas de coupure sur le terrain) :

- captures.jsonl     : chaque forme d'onde recue + la prediction du modele
                       au moment de la capture (jamais modifie ensuite).
- confirmations.jsonl : correction/validation d'un operateur pour une
                        capture donnee (identifiee par son id), ajoutee
                        separement. La derniere confirmation pour un id
                        fait foi.

Important : la prediction seule n'est PAS une verite terrain. Sans
confirmation d'un operateur (l'arme reellement tiree), ces donnees ne
doivent pas servir a re-entrainer les modeles — cela reviendrait a leur
faire apprendre leurs propres erreurs. Seules les captures confirmees
constituent des donnees labellisees exploitables. Voir field_app/README.md.
"""
from __future__ import annotations

import json
from pathlib import Path

from config import APP_DIR

DATA_DIR = APP_DIR / "data"
CAPTURES_PATH = DATA_DIR / "captures.jsonl"
CONFIRMATIONS_PATH = DATA_DIR / "confirmations.jsonl"


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_capture(entry: dict) -> None:
    _append_jsonl(CAPTURES_PATH, entry)


def log_confirmation(entry_id: str, confirmed: dict, confirmed_at: str) -> None:
    _append_jsonl(CONFIRMATIONS_PATH, {
        "id": entry_id,
        "confirmed": confirmed,
        "confirmed_at": confirmed_at,
    })
