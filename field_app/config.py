"""Configuration de l'app terrain : cle API partagee avec le RPi, port d'ecoute.

Genere un fichier instance/config.json au premier lancement (a cote de l'exe,
pas dans les sources) avec une cle API aleatoire, affichee au demarrage pour
que l'operateur puisse configurer le script d'envoi du Raspberry Pi.
"""
from __future__ import annotations

import json
import secrets

# En mode fige (PyInstaller), le dossier instance/ vit a cote de l'executable,
# pas dans le bundle temporaire en lecture seule (sys._MEIPASS).
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

INSTANCE_DIR = APP_DIR / "instance"
CONFIG_PATH = INSTANCE_DIR / "config.json"

DEFAULTS = {
    "host": "0.0.0.0",
    "port": 8765,
    "api_key": None,
    "max_history": 50,
}


def load_config() -> dict:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        cfg = {**DEFAULTS, **json.loads(CONFIG_PATH.read_text(encoding="utf-8"))}
    else:
        cfg = dict(DEFAULTS)

    if not cfg.get("api_key"):
        cfg["api_key"] = secrets.token_urlsafe(24)

    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg
