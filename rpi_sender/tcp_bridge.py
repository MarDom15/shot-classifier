"""Pont TCP -> app terrain : tourne sur le Raspberry Pi, ecoute les connexions
TCP entrantes de PLUSIEURS boitiers de controle (un par capteur/cible, ex.
Siemens LOGO! 8 — chacun avec sa propre IP fixe), et relaie chaque forme
d'onde recue vers la tablette (field_app) avec le bon `target_id`, via HTTP.

*** HYPOTHESES PAR DEFAUT — A CONFIRMER/AJUSTER AVEC LE TECHNICIEN ***

1. Chaque capteur se connecte depuis sa propre adresse IP fixe (boitier de
   controle dedie) : c'est cette IP qui identifie la cible, via la table
   `ip_to_target` du fichier de configuration. Si les capteurs sont plutot
   distingues autrement (numero de port, identifiant dans le message...),
   adapter `identify_sensor()`.

2. Un message = le contenu complet d'une connexion TCP (le boitier se
   connecte, envoie une forme d'onde, puis ferme la connexion). C'est le
   cas le plus simple et le plus courant pour ce genre d'automate. Si le
   systeme reel garde une connexion ouverte pour envoyer plusieurs messages
   a la suite, il faudra ajouter un decoupage explicite (longueur prefixee
   ou delimiteur) — voir le commentaire dans `handle_connection()`.

3. Le contenu recu peut etre soit 512 octets bruts (echantillons ADC
   0-255), soit une IMAGE (PNG/JPEG/BMP/GIF) representant la forme d'onde
   — les deux cas sont detectes automatiquement (voir image_digitize.py) et
   convertis vers le meme format final (512 valeurs 0-255) avant l'envoi a
   la tablette.

Configuration (rpi_sender/instance/tcp_bridge_config.json, cree au premier
lancement) :
    tablet_host   : IP de la tablette (field_app)
    tablet_port   : port de l'app terrain (8765 par defaut)
    api_key       : cle affichee au demarrage de field_app/server.py
    listen_host   : interface d'ecoute du pont (0.0.0.0 = toutes)
    listen_port   : port TCP sur lequel les boitiers se connectent
    ip_to_target  : { "192.168.1.101": 1, "192.168.1.102": 2, ... }

Usage :
    python tcp_bridge.py                                  # ecoute et relaie en continu
    python tcp_bridge.py --simulate-sensor 127.0.0.1 --target-id 3
                                                           # simule un capteur, sans materiel
"""
from __future__ import annotations

import argparse
import json
import random
import socket
import sys
import threading
import time
from pathlib import Path

from image_digitize import digitize_image, looks_like_image
from tablet_client import send_waveform

APP_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = APP_DIR / "instance"
CONFIG_PATH = INSTANCE_DIR / "tcp_bridge_config.json"

RAW_FRAME_SIZE = 512

DEFAULTS = {
    "tablet_host": "192.168.1.42",
    "tablet_port": 8765,
    "api_key": "",
    "listen_host": "0.0.0.0",
    "listen_port": 9000,
    "ip_to_target": {
        "127.0.0.1": 1,
    },
}


def load_config() -> dict:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    else:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print(f"Fichier de configuration cree : {CONFIG_PATH}")
        print("Renseignez-y tablet_host, api_key et ip_to_target avant un usage reel.")
    return cfg


def identify_sensor(cfg: dict, client_ip: str) -> tuple[int | None, str]:
    """*** POINT D'INTEGRATION *** : quelle cible correspond a une connexion
    entrante. Par defaut : table IP -> target_id de la configuration."""
    target_id = cfg["ip_to_target"].get(client_ip)
    label = f"cible {target_id}" if target_id is not None else f"IP inconnue {client_ip}"
    return target_id, label


def _read_all(conn: socket.socket, max_bytes: int = 5_000_000) -> bytes:
    """Lit tout le contenu de la connexion jusqu'a sa fermeture par l'autre
    bout. Hypothese : un message = une connexion (voir note en tete de
    fichier). Si le systeme reel garde la connexion ouverte pour plusieurs
    messages, remplacer cette fonction par une lecture avec longueur
    prefixee ou delimiteur explicite."""
    buf = bytearray()
    while len(buf) < max_bytes:
        chunk = conn.recv(65536)
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def decode_payload(raw: bytes) -> list[int] | None:
    """Convertit le contenu recu (octets bruts ou image) en 512 valeurs
    0-255, ou None si le format n'est pas reconnu."""
    if looks_like_image(raw):
        return digitize_image(raw)
    if len(raw) == RAW_FRAME_SIZE:
        return list(raw)
    return None


def handle_connection(conn: socket.socket, addr: tuple[str, int], cfg: dict) -> None:
    client_ip = addr[0]
    target_id, label = identify_sensor(cfg, client_ip)
    if target_id is None:
        print(f"[{label}] connexion recue mais IP absente de ip_to_target "
              f"({CONFIG_PATH}) — a corriger pour que la cible soit identifiee cote tablette.")

    with conn:
        raw = _read_all(conn)
        if not raw:
            print(f"[{label}] connexion vide/fermee immediatement, rien a traiter.")
            return

        kind = "image" if looks_like_image(raw) else f"{len(raw)} octets bruts"
        print(f"[{label}] recu {kind}")

        try:
            values = decode_payload(raw)
        except Exception as e:  # pragma: no cover - defensif, ex. image corrompue
            print(f"[{label}] echec du decodage : {e}", file=sys.stderr)
            return

        if values is None:
            print(f"[{label}] format non reconnu (ni image, ni {RAW_FRAME_SIZE} octets bruts — "
                  f"recu {len(raw)} octets). A ajuster dans decode_payload() une fois le format confirme.",
                  file=sys.stderr)
            return

        send_waveform(
            cfg["tablet_host"], cfg["tablet_port"], cfg["api_key"], values,
            sensor_id=f"tcp-bridge:{client_ip}", target_id=target_id, label=label,
        )


def serve(cfg: dict) -> None:
    if not cfg["api_key"]:
        print(f"Aucune cle API configuree dans {CONFIG_PATH} — copiez celle affichee "
              "au demarrage de field_app/server.py.", file=sys.stderr)
        sys.exit(1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((cfg["listen_host"], cfg["listen_port"]))
    sock.listen()
    print(f"Pont TCP en ecoute sur {cfg['listen_host']}:{cfg['listen_port']} "
          f"-> relais vers http://{cfg['tablet_host']}:{cfg['tablet_port']}/ingest")
    print(f"Cibles connues : {cfg['ip_to_target']}")
    try:
        while True:
            conn, addr = sock.accept()
            threading.Thread(target=handle_connection, args=(conn, addr, cfg), daemon=True).start()
    except KeyboardInterrupt:
        print("Arret du pont TCP.")
    finally:
        sock.close()


def _simulated_waveform() -> list[int]:
    baseline = 128
    values = [baseline + random.randint(-4, 4) for _ in range(512)]
    if random.random() < 0.3:
        peak_idx = random.randint(20, 120)
        amplitude = random.randint(60, 120)
        for offset in range(-5, 30):
            i = peak_idx + offset
            if 0 <= i < 512:
                decay = max(0.0, 1 - abs(offset) / 25)
                values[i] = max(0, min(255, int(baseline + amplitude * decay * random.choice([1, -1]))))
    return [max(0, min(255, v)) for v in values]


def simulate_sensor(host: str, port: int, interval: float) -> None:
    """Simule un boitier de controle qui se connecte au pont TCP et envoie
    une forme d'onde brute par connexion — pour tester tout le pont, sans
    materiel ni technicien. Utiliser --simulate-sensor avec la meme IP que
    celle configuree dans ip_to_target pour voir la bonne cible s'allumer."""
    print(f"Simulation d'un capteur connecte a {host}:{port} (une connexion par envoi)...")
    while True:
        try:
            with socket.create_connection((host, port), timeout=5) as conn:
                conn.sendall(bytes(_simulated_waveform()))
        except OSError as e:
            print(f"Echec de connexion a {host}:{port} : {e}", file=sys.stderr)
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simulate-sensor", metavar="TABLET_OR_BRIDGE_HOST",
                     help="simule un capteur qui se connecte a ce pont (127.0.0.1 pour un test local)")
    ap.add_argument("--interval", type=float, default=2.0, help="secondes entre deux envois simules")
    args = ap.parse_args()

    cfg = load_config()

    if args.simulate_sensor:
        simulate_sensor(args.simulate_sensor, cfg["listen_port"], args.interval)
    else:
        serve(cfg)


if __name__ == "__main__":
    main()
