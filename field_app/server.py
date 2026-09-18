"""App terrain : recoit les formes d'onde de 18 postes de tir (Raspberry Pi,
IP fixes 192.168.0.41-58) via le wifi commun, classe chaque tir en direct
avec le pipeline entraine, et pousse le resultat en temps reel a l'interface
web (tablette Windows) — une boite de controle par cible.

Lancement (dev, depuis les sources) :
    python field_app/server.py

Lancement (exe empaquete) :
    double-clic sur field_app.exe (voir field_app/build/)

Au premier lancement, un fichier instance/config.json est cree a cote de
l'executable avec une cle API aleatoire : c'est cette cle qu'il faut copier
dans la configuration du script d'envoi du Raspberry Pi (rpi_sender/).
"""
from __future__ import annotations

import sys
import uuid
import webbrowser
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Timer

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Repo root : field_app/ est au meme niveau que src/, app/, models_store/.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import CONFIG_PATH, load_config
from storage import log_capture, log_confirmation
from targets import TARGETS, TARGETS_BY_ID, identify_target

from src.models.inference import predict_pipeline

CONFIG = load_config()
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Shot Classifier — Terrain")

history: deque[dict] = deque(maxlen=CONFIG["max_history"])
connections: set[WebSocket] = set()
last_seen: str | None = None
# Dernier resultat connu par cible (id -> entry), independant de l'historique
# global (capacite limitee) : une cible silencieuse depuis longtemps garde
# son dernier statut affiche tant qu'un evenement plus recent d'une autre
# cible ne l'a pas fait sortir de `history`.
target_last_result: dict[int, dict] = {}


class IngestPayload(BaseModel):
    values: list[int] = Field(..., description="512 echantillons ADC 8 bits (0-255)")
    sensor_id: str | None = None
    captured_at: str | None = None
    target_id: int | None = Field(
        default=None,
        description="Cible explicite (1-18) — necessaire quand un seul RPi relaie "
                    "plusieurs cibles (l'IP source ne suffit alors plus a les distinguer). "
                    "Si absent, la cible est deduite de l'IP source (cas 1 RPi = 1 cible).",
    )


class ManualPredictPayload(IngestPayload):
    pass


class ConfirmPayload(BaseModel):
    id: str
    is_shot: bool
    weapon: str | None = None
    note: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summarize(out: dict) -> dict:
    """Reduit la sortie complete de predict_pipeline a ce qu'affiche l'UI."""
    best1 = out["stage1_best"]
    r1 = out["stage1"][best1]
    is_shot = str(r1["label"]) == "1"
    summary = {
        "is_shot": is_shot,
        "stage1_model": best1,
        "stage1_confidence": (r1.get("proba") or {}).get("1", r1.get("proba", {}).get(1)),
        "weapon": None,
        "stage2_model": None,
        "weapon_confidence": None,
    }
    if is_shot and out.get("stage2"):
        best2 = out["stage2_best"]
        r2 = out["stage2"][best2]
        summary["weapon"] = r2["label"]
        summary["stage2_model"] = best2
        if r2.get("proba"):
            summary["weapon_confidence"] = r2["proba"].get(r2["label"])
    return summary


def _make_entry(values: list[int], sensor_id: str | None, captured_at: str | None,
                 target: dict | None, source_ip: str | None) -> dict:
    out = predict_pipeline(values)
    return {
        "id": uuid.uuid4().hex,
        "received_at": _now(),
        "sensor_id": sensor_id,
        "captured_at": captured_at,
        "values": values,
        "summary": _summarize(out),
        "confirmed": None,
        "target_id": target["id"] if target else None,
        "target_label": target["label"] if target else (f"IP inconnue ({source_ip})" if source_ip else "Test manuel"),
        "ip": source_ip,
    }


async def _publish(entry: dict) -> None:
    log_capture(entry)
    history.appendleft(entry)
    if entry["target_id"] is not None:
        target_last_result[entry["target_id"]] = entry
    await _broadcast({"type": "result", "payload": entry})


async def _broadcast(message: dict) -> None:
    dead = []
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:  # pragma: no cover - connexion fermee entre temps
            dead.append(ws)
    for ws in dead:
        connections.discard(ws)


def _check_key(x_api_key: str | None) -> None:
    if x_api_key != CONFIG["api_key"]:
        raise HTTPException(status_code=401, detail="Cle API invalide (voir instance/config.json).")


@app.post("/ingest")
async def ingest(payload: IngestPayload, request: Request, x_api_key: str | None = Header(default=None)):
    """Point d'entree pour un Raspberry Pi : une forme d'onde -> une classification.

    Deux facons d'identifier la cible, selon le deploiement :
    - un RPi par cible (IP fixe) : la cible est deduite de l'IP source de la
      requete (192.168.0.41-58) — c'est le cas historique, voir targets.py ;
    - un RPi relayant plusieurs cibles : l'IP source ne suffit plus a les
      distinguer, le RPi doit alors preciser `target_id` (1-18) dans le
      corps de la requete — utilise en priorite si present."""
    _check_key(x_api_key)
    if len(payload.values) != 512:
        raise HTTPException(status_code=422, detail=f"512 valeurs attendues, {len(payload.values)} recues.")
    if any(v < 0 or v > 255 for v in payload.values):
        raise HTTPException(status_code=422, detail="Valeurs hors plage ADC 8 bits (0-255).")

    global last_seen
    last_seen = _now()

    source_ip = request.client.host if request.client else None
    if payload.target_id is not None:
        target = TARGETS_BY_ID.get(payload.target_id)
        if target is None:
            raise HTTPException(status_code=422, detail=f"target_id inconnu : {payload.target_id} (attendu 1-18).")
    else:
        target = identify_target(source_ip)
    entry = _make_entry(payload.values, payload.sensor_id, payload.captured_at, target, source_ip)
    await _publish(entry)
    return {"ok": True, "result": entry["summary"], "target": target}


@app.post("/api/manual-predict")
async def manual_predict(payload: ManualPredictPayload):
    """Utilise par le panneau 'Test manuel' de l'UI (meme origine, pas de cle
    requise) — la cible a simuler est choisie explicitement dans l'UI plutot
    que deduite de l'IP (une requete du navigateur vient de la tablette
    elle-meme, jamais d'une des 18 IP de cible)."""
    if len(payload.values) != 512:
        raise HTTPException(status_code=422, detail=f"512 valeurs attendues, {len(payload.values)} recues.")

    target = TARGETS_BY_ID.get(payload.target_id) if payload.target_id else None
    entry = _make_entry(payload.values, payload.sensor_id or "manuel (UI)", None, target, None)
    await _publish(entry)
    return {"ok": True, "result": entry["summary"]}


@app.post("/api/confirm")
async def confirm(payload: ConfirmPayload):
    """Enregistre la correction/validation d'un operateur pour une capture :
    seule cette information (pas la prediction seule) constitue une donnee
    labellisee exploitable pour un futur re-entrainement (voir storage.py)."""
    confirmed_at = _now()
    confirmed = {"is_shot": payload.is_shot, "weapon": payload.weapon, "note": payload.note}
    log_confirmation(payload.id, confirmed, confirmed_at)

    for entry in history:
        if entry.get("id") == payload.id:
            entry["confirmed"] = confirmed
            break

    await _broadcast({"type": "confirmation", "payload": {"id": payload.id, "confirmed": confirmed}})
    return {"ok": True}


@app.get("/api/targets")
async def targets():
    return {"targets": TARGETS, "last_results": target_last_result}


@app.get("/api/status")
async def status():
    return {
        "last_seen": last_seen,
        "history": list(history),
    }


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    try:
        await websocket.send_json({"type": "history", "payload": list(history)})
        await websocket.send_json({"type": "targets", "payload": {"targets": TARGETS, "last_results": target_last_result}})
        while True:
            # L'UI n'envoie rien sur ce canal ; on attend juste la deconnexion.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connections.discard(websocket)


@app.get("/")
async def index():
    return RedirectResponse(url="/ui/index.html")


app.mount("/ui", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def _print_banner():
    print("=" * 64)
    print(" Shot Classifier — App terrain")
    print("=" * 64)
    print(f" Interface : http://localhost:{CONFIG['port']}/  (ou l'IP de cette tablette sur le wifi)")
    print(f" Cle API pour le Raspberry Pi (rpi_sender) : {CONFIG['api_key']}")
    print(f" (deja enregistree dans {CONFIG_PATH})")
    print(f" {len(TARGETS)} cibles configurees : {TARGETS[0]['ip']} a {TARGETS[-1]['ip']} (voir targets.py)")
    print("=" * 64)


def main():
    import uvicorn

    _print_banner()
    Timer(1.5, lambda: webbrowser.open(f"http://localhost:{CONFIG['port']}/")).start()
    uvicorn.run(app, host=CONFIG["host"], port=CONFIG["port"], log_level="info")


if __name__ == "__main__":
    main()
