"""Client HTTP partage : envoie une forme d'onde a l'app terrain (tablette,
field_app/server.py) via /ingest. Utilise par send_waveform.py et
tcp_bridge.py pour eviter de dupliquer cette logique.
"""
from __future__ import annotations

import json
import sys
import time
from urllib import error, request


def send_waveform(host: str, port: int, api_key: str, values: list[int],
                   sensor_id: str | None = None, target_id: int | None = None,
                   label: str | None = None) -> dict | None:
    """POST une forme d'onde vers /ingest. Renvoie la reponse JSON (dict) si
    l'envoi a reussi, None sinon (erreur deja affichee sur stderr)."""
    url = f"http://{host}:{port}/ingest"
    body: dict = {
        "values": values,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if sensor_id is not None:
        body["sensor_id"] = sensor_id
    if target_id is not None:
        body["target_id"] = target_id

    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
    )
    tag = label or sensor_id or (f"cible {target_id}" if target_id is not None else "?")
    try:
        with request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            summary = result.get("result", {})
            if summary.get("is_shot"):
                print(f"[{tag}] TIR détecté — arme : {summary.get('weapon')}")
            else:
                print(f"[{tag}] non-tir")
            return result
    except error.HTTPError as e:
        print(f"[{tag}] Erreur HTTP {e.code} en envoyant vers {url} : {e.read().decode(errors='replace')}",
              file=sys.stderr)
    except error.URLError as e:
        print(f"[{tag}] Impossible de joindre {url} ({e.reason}) — la tablette est-elle sur le meme wifi ?",
              file=sys.stderr)
    return None
