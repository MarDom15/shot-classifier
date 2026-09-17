"""Script a executer sur le Raspberry Pi : capture une forme d'onde du
capteur d'impact et l'envoie a l'app terrain (tablette Windows) sur le wifi
commun, pour classification en direct.

Point important : ce depot ne contient pas le code d'acquisition materielle
du capteur (ADC, GPIO, etc.) — seulement le pipeline de classification a
partir de formes d'onde deja capturees. La fonction `capture_waveform()`
ci-dessous est donc un point d'integration a completer avec votre propre
lecture materielle (spidev, RPi.GPIO, port serie d'un microcontroleur qui
fait l'acquisition, etc.). En attendant, `--simulate` genere des formes
d'onde plausibles pour tester toute la chaine reseau sans capteur reel.

Configuration (rpi_sender/instance/config.json, cree au premier lancement) :
    host       : IP de la tablette sur le wifi commun (ex. "192.168.1.42")
    port       : port de l'app terrain (8765 par defaut)
    api_key    : cle affichee au demarrage de field_app/server.py — a copier ici
    sensor_id  : identifiant libre de ce capteur (ex. "rpi-nord")
    interval_s : delai entre deux verifications du capteur (mode simulate)

Usage :
    python send_waveform.py --simulate                # test sans materiel
    python send_waveform.py --host 192.168.1.42        # usage reel
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from urllib import error, request

APP_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = APP_DIR / "instance"
CONFIG_PATH = INSTANCE_DIR / "config.json"

DEFAULTS = {
    "host": "192.168.1.42",
    "port": 8765,
    "api_key": "",
    "sensor_id": "rpi-01",
    "interval_s": 2.0,
    "simulate": False,
}


def load_config() -> dict:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    else:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print(f"Fichier de configuration cree : {CONFIG_PATH}")
        print("Renseignez-y au moins 'host' et 'api_key' avant un usage reel.")
    return cfg


def capture_waveform() -> list[int]:
    """Point d'integration materiel : doit renvoyer 512 entiers 0-255.

    A completer avec la lecture reelle du capteur (ex. via spidev pour un
    ADC SPI, ou lecture d'un port serie si l'acquisition est faite par un
    microcontroleur externe). Voir CAHIER_DES_CHARGES.md section 4 pour le
    format attendu (echantillonnage 512 pts, ADC 8 bits, ligne de base ~128).
    """
    raise NotImplementedError(
        "Acquisition materielle non implementee. Completez capture_waveform() "
        "avec la lecture reelle de votre capteur, ou lancez ce script avec "
        "--simulate pour tester la chaine reseau sans materiel."
    )


def simulate_waveform() -> list[int]:
    """Genere une forme d'onde plausible pour tester la chaine bout en bout
    sans materiel : ligne de base ~128 avec un bruit leger, et de temps en
    temps un pic marque (simule un impact)."""
    baseline = 128
    values = [baseline + random.randint(-4, 4) for _ in range(512)]
    if random.random() < 0.3:  # simule un impact de temps en temps
        peak_idx = random.randint(20, 120)
        amplitude = random.randint(60, 120)
        for offset in range(-5, 30):
            i = peak_idx + offset
            if 0 <= i < 512:
                decay = max(0.0, 1 - abs(offset) / 25)
                values[i] = max(0, min(255, int(baseline + amplitude * decay * random.choice([1, -1]))))
    return [max(0, min(255, v)) for v in values]


def send(cfg: dict, values: list[int]) -> None:
    url = f"http://{cfg['host']}:{cfg['port']}/ingest"
    body = json.dumps({
        "values": values,
        "sensor_id": cfg["sensor_id"],
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": cfg["api_key"]},
    )
    try:
        with request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            summary = result.get("result", {})
            if summary.get("is_shot"):
                print(f"[{cfg['sensor_id']}] TIR détecté — arme : {summary.get('weapon')}")
            else:
                print(f"[{cfg['sensor_id']}] non-tir")
    except error.HTTPError as e:
        print(f"Erreur HTTP {e.code} en envoyant vers {url} : {e.read().decode(errors='replace')}", file=sys.stderr)
    except error.URLError as e:
        print(f"Impossible de joindre {url} ({e.reason}) — la tablette est-elle sur le meme wifi ?", file=sys.stderr)


def main():
    cfg = load_config()

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=cfg["host"], help="IP de la tablette sur le wifi commun")
    ap.add_argument("--port", type=int, default=cfg["port"])
    ap.add_argument("--api-key", default=cfg["api_key"])
    ap.add_argument("--sensor-id", default=cfg["sensor_id"])
    ap.add_argument("--interval", type=float, default=cfg["interval_s"], help="secondes entre deux captures (mode simulate)")
    ap.add_argument("--simulate", action="store_true", default=cfg["simulate"], help="genere des formes d'onde de test, sans materiel")
    ap.add_argument("--once", action="store_true", help="envoie une seule forme d'onde puis quitte")
    args = ap.parse_args()

    cfg.update(host=args.host, port=args.port, api_key=args.api_key, sensor_id=args.sensor_id)

    if not cfg["api_key"]:
        print("Aucune cle API configuree — copiez celle affichee au demarrage de field_app/server.py "
              f"dans {CONFIG_PATH} ou passez --api-key.", file=sys.stderr)
        sys.exit(1)

    capture = simulate_waveform if args.simulate else capture_waveform
    print(f"Envoi vers http://{cfg['host']}:{cfg['port']}/ingest "
          f"({'simulation' if args.simulate else 'capteur reel'}, capteur={cfg['sensor_id']})")

    while True:
        try:
            values = capture()
            send(cfg, values)
        except NotImplementedError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
