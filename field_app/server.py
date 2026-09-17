"""App terrain : recoit les formes d'onde d'un Raspberry Pi via le wifi
commun, classe chaque tir en direct avec le pipeline entraine, et pousse le
resultat en temps reel a l'interface web (tablette Windows).

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
import webbrowser
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Timer

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Repo root : field_app/ est au meme niveau que src/, app/, models_store/.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import CONFIG_PATH, load_config

from src.models.inference import predict_pipeline

CONFIG = load_config()
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Shot Classifier — Terrain")

history: deque[dict] = deque(maxlen=CONFIG["max_history"])
connections: set[WebSocket] = set()
last_seen: str | None = None


class IngestPayload(BaseModel):
    values: list[int] = Field(..., description="512 echantillons ADC 8 bits (0-255)")
    sensor_id: str | None = None
    captured_at: str | None = None


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
async def ingest(payload: IngestPayload, x_api_key: str | None = Header(default=None)):
    """Point d'entree pour le Raspberry Pi : une forme d'onde -> une classification."""
    _check_key(x_api_key)
    if len(payload.values) != 512:
        raise HTTPException(status_code=422, detail=f"512 valeurs attendues, {len(payload.values)} recues.")
    if any(v < 0 or v > 255 for v in payload.values):
        raise HTTPException(status_code=422, detail="Valeurs hors plage ADC 8 bits (0-255).")

    global last_seen
    last_seen = _now()

    out = predict_pipeline(payload.values)
    entry = {
        "received_at": last_seen,
        "sensor_id": payload.sensor_id,
        "captured_at": payload.captured_at,
        "values": payload.values,
        "summary": _summarize(out),
    }
    history.appendleft(entry)
    await _broadcast({"type": "result", "payload": entry})
    return {"ok": True, "result": entry["summary"]}


@app.post("/api/manual-predict")
async def manual_predict(payload: IngestPayload):
    """Utilise par le panneau 'Test manuel' de l'UI (meme origine, pas de cle requise)."""
    if len(payload.values) != 512:
        raise HTTPException(status_code=422, detail=f"512 valeurs attendues, {len(payload.values)} recues.")
    out = predict_pipeline(payload.values)
    entry = {
        "received_at": _now(),
        "sensor_id": "manuel (UI)",
        "captured_at": None,
        "values": payload.values,
        "summary": _summarize(out),
    }
    history.appendleft(entry)
    await _broadcast({"type": "result", "payload": entry})
    return {"ok": True, "result": entry["summary"]}


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
    print("=" * 64)


def main():
    import uvicorn

    _print_banner()
    Timer(1.5, lambda: webbrowser.open(f"http://localhost:{CONFIG['port']}/")).start()
    uvicorn.run(app, host=CONFIG["host"], port=CONFIG["port"], log_level="info")


if __name__ == "__main__":
    main()
