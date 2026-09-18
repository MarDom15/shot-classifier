% Shot Classifier — Complete Project Manual
% Martial Domche
% September 2026

# 1. Overview

**Shot Classifier** is a machine learning pipeline that, from a raw waveform captured by an impact sensor (512 samples, 8-bit ADC), determines:

1. whether it is a **gunshot** or a **non-ballistic impact** (a thrown rock, spurious noise);
2. if it is a shot, **which weapon** fired it (G36, MP7, P8).

The project includes:

- a **data and training pipeline** (parsing, feature extraction, 9 models compared across 2 stages);
- a **demo app** (Streamlit) to test and compare the models;
- an **autonomous agent** that orchestrates the whole lifecycle (ingestion, retraining, rollback, drift) unattended;
- a **field app** for a Windows tablet, connected to 18 firing positions (Raspberry Pi) over the local wifi, with live classification;
- a **sender script** for the Raspberry Pi;
- a **monitoring** stack (Prometheus + Grafana);
- a **CI/CD** pipeline (GitHub Actions).

The public repository is on GitHub: <https://github.com/MarDom15/shot-classifier>

> **Important — data confidentiality.** The source data documents real live-fire tests with service weapons (G36, MP7, P8). The public repository does **not** contain the raw data or the trained models (see section 14) — they are provided separately to authorized parties.

## 1.1 Chosen architecture

```
waveform (512 pts) ──▶ [Stage 1: shot / non-shot] ──▶ if shot ──▶ [Stage 2: G36 / MP7 / P8]
```

This two-stage split avoids drowning the control class (« Steine », rocks — 14 examples out of 397) in an imbalanced multiclass problem. Each stage compares 9 models (8 classical + 1 1D CNN), validated with a split **by recording session** (never random, to avoid optimistic information leakage).

### Current results (test set = session 19090822)

| Stage | Best model | Accuracy | F1 macro |
|---|---|---|---|
| 1 — shot vs non-shot | Gradient Boosting | 0.976 | **0.827** |
| 2 — weapon identification | 1D CNN | 0.580 | **0.583** |

Stage 2 remains fragile outside the original recording conditions — this is documented and expected (see `CAHIER_DES_CHARGES.md`, Limitations section), not a hidden issue.

---

# 2. Prerequisites and installation

To pick this project up from scratch on a new machine, install:

| Tool | Purpose | Where to get it |
|---|---|---|
| **Git** | Clone the repository | <https://git-scm.com/downloads> |
| **Docker Desktop** | Run the whole stack (app, agent, monitoring) without installing anything else | <https://www.docker.com/products/docker-desktop/> |
| **Python 3.11 (64-bit)** | Optional: usage without Docker, or to build the field app executable | <https://www.python.org/downloads/> |
| **GitHub CLI (`gh`)** | Optional: push changes to GitHub from the command line | <https://cli.github.com/> |

**On Windows**, Python can also be installed via:

```powershell
winget install Python.Python.3.11
```

Verify the installations:

```bash
git --version
docker --version
docker compose version
python --version
```

## 2.1 Getting the project

```bash
git clone https://github.com/MarDom15/shot-classifier.git
cd shot-classifier
```

> The public repository contains only the **code** — `data/` and `models_store/` are empty (just a `.gitkeep`). For full usage (real training), the data archive must be obtained separately from the project owner and placed at `data/raw/200924_Brocksettel.zip`, then `make train` (section 5) rebuilds `models_store/`.

---

# 3. Quick start — Recommended option (Docker)

This is the simplest and most reliable way to run the whole project, with nothing to install besides Docker.

```bash
cd shot-classifier
docker compose up --build -d
```

This single command builds the image and starts **four containers**:

| Service | Local URL | Role |
|---|---|---|
| `app` | <http://localhost:8501> | Streamlit app (demo, prediction, comparison) |
| `agent` | — (runs in the background) | Periodic automatic retraining |
| `prometheus` | <http://localhost:9090> | Metrics collection |
| `grafana` | <http://localhost:3000> | Monitoring dashboards |

To stop cleanly:

```bash
docker compose down
```

To run only the app, without the agent or monitoring:

```bash
docker compose up app
```

To watch the agent's logs live:

```bash
docker compose logs -f agent
```

## 3.1 Credentials and access

| Service | Credentials |
|---|---|
| Streamlit app (8501) | None |
| Prometheus (9090) | None |
| Grafana (3000) — **viewing** | None (anonymous access enabled) |
| Grafana (3000) — **administration** | `admin` / `admin` (a password change is prompted on first admin login) |

> **Security.** None of these services have robust password protection — this is intentional for a fully local setup. Never expose these ports to the internet without revisiting this configuration (change the Grafana password, disable anonymous access, add Prometheus authentication).

---

# 4. Option B — Native Python installation (without Docker)

```bash
cd shot-classifier
pip install -r requirements-dev.txt
pip install --index-url https://download.pytorch.org/whl/cpu torch   # CPU build, much lighter

make train      # rebuilds the dataset, trains the 9 models x 2 stages
make app        # launches the Streamlit app on http://localhost:8501
```

**On Windows**, if `python`/`pip` are not recognized after installation, this is usually because Python was not added to PATH — reinstall with "Add python.exe to PATH" checked, or use `winget install Python.Python.3.11`.

---

# 5. Data pipeline

```bash
python -m src.data.parse_raw     # .zip archive -> data/processed/brocksettel_waveforms_raw.csv
python -m src.data.features      # -> data/processed/brocksettel_features_enriched.csv
```

Parsing handles two known anomalies in the original format (documented and tested in `tests/test_parse_raw.py`):

- files containing two events concatenated with no line break;
- one orphan file outside the expected folder structure.

---

# 6. Training and model comparison

```bash
python -m src.training.train_classical   # 8 classical models, 2 stages
python -m src.training.train_cnn         # 1D CNN, 2 stages
python -m src.training.compare_models    # final comparison table + chart
```

All trained models are saved under `models_store/<stage>/<model>.{joblib,pt}`, with the best model's name in `best_model.txt`. The Streamlit app and the inference service (`src/models/inference.py`) rely on this to compare every model's predictions on the same example.

The full table is regenerated on every run in `docs/reports/model_comparison_final.csv` / `.png`.

---

# 7. Autonomous agent (ML/DL)

`src/agent/ml_agent.py` orchestrates the entire lifecycle unattended: rebuilding the dataset, training the 9 models across the 2 stages, selecting the best model per stage, saving with rollback, drift detection, logging.

## 7.1 Run modes

```bash
# A single cycle (useful for testing or triggering a retrain manually)
python -m src.agent.ml_agent run

# Autonomous mode: runs indefinitely, one cycle every 6h by default
python -m src.agent.ml_agent watch --interval 21600
```

With Docker, the agent starts automatically in `watch` mode via the `agent` service in `docker-compose.yml`. To change the frequency without editing the file:

```bash
AGENT_INTERVAL_SECONDS=3600 docker compose up -d   # one cycle per hour
```

## 7.2 Safety — automatic rollback

Before each retraining, the agent saves a timestamped snapshot of the current models (`models_store_history/`). If the new model is significantly worse than the previous one (F1 macro dropping by more than 0.02), it automatically rolls back and logs it — this is not an error, it is the safety net working as intended.

## 7.3 Adding new data without touching the code

Drop a new `.zip` archive (same structure as the original archive) into `data/raw/incoming/`. The agent picks it up on the next cycle, merges it with the existing data (automatic deduplication), and retrains all models on it.

## 7.4 Claude Code agent

A ready-to-use Claude Code sub-agent is provided: `.claude/agents/shot-classifier-agent.md`. Open this repository in Claude Code and ask, in plain language: *"rerun the ML agent"*, *"retrain the models"*, *"check for drift"* — Claude Code automatically invokes this sub-agent, which runs the necessary commands without waiting for step-by-step confirmation, then reports a structured summary.

---

# 8. Streamlit app (demo)

Available at <http://localhost:8501>. Four tabs:

- **🔮 Prediction** — test a waveform (example from the dataset, or paste 512 hexadecimal values), see the prediction from every model.
- **📊 Model comparison** — table and chart of the 9 models × 2 stages.
- **🩺 Monitoring** — log of predictions made, on-demand generation of a data drift report (Evidently).
- **ℹ️ About** — project context.

The interface is **bilingual FR/EN** (selector in the sidebar, preference remembered in the browser).

---

# 9. Monitoring — Prometheus and Grafana

## 9.1 What is measured

**Streamlit app** (`/metrics` on port 8000, exposed on the host as **8002** — port 8000 is often already used by something else on the machine):

- number of predictions, by result (shot/non-shot) and by weapon;
- inference latency.

**Agent** (`/metrics` on port **8001**, active only in `watch` mode):

- number of cycles by status (success/error);
- F1 macro of the best model per stage, at the last cycle;
- dataset size;
- number of automatic rollbacks triggered;
- full cycle duration.

## 9.2 Dashboard

A **"Shot Classifier"** dashboard is auto-provisioned in Grafana (no manual setup): <http://localhost:3000/d/shot-classifier/shot-classifier>

Six panels: predictions by result, p95 latency, F1 macro per stage, agent cycles by status, rollbacks, dataset events, last agent run, predictions by weapon.

## 9.3 A quirk worth knowing

The Streamlit app's `/metrics` only comes alive **once a real browser has opened the page at least once** — Streamlit only runs its Python script on a real browser session (WebSocket), not on a plain HTTP request. Prometheus will show that target as `down` until then; this is not a bug, just open <http://localhost:8501> once.

---

# 10. Field app (Windows tablet + Raspberry Pi)

For live field use rather than exploration, `field_app/` is a standalone Windows app (packageable as a `.exe` with PyInstaller — no Python or Docker needed on the tablet) that receives waveforms from **18 firing positions** (Raspberry Pi) over the local wifi and classifies each shot live.

## 10.1 The 18 targets

Each firing position has a fixed IP address, from **192.168.0.41 to 192.168.0.58** (`field_app/targets.py`). Identification is done by the **source IP address** of the incoming request — not by a value sent in the JSON — so a misconfigured Raspberry Pi cannot impersonate another target.

The interface shows a grid of 18 control boxes (number, IP, colored indicator: grey = no data, green = last event non-shot, red = last shot detected with the weapon). Clicking a box "pins" its detail (waveform, confidence); a button lets you go back to automatically following the most recent event across all targets.

To change the number of targets or the IP range: edit `FIRST_OCTET` and `N_TARGETS` in `field_app/targets.py`.

## 10.2 Running in development

```bash
pip install -r field_app/requirements.txt
python field_app/server.py
```

The default browser opens automatically at <http://localhost:8765/>. The API key to give the Raspberry Pi is shown in the console and saved in `field_app/instance/config.json`.

## 10.3 Building the standalone Windows executable

Requires a **native Windows Python** (PyInstaller cannot produce a Windows `.exe` from a Linux/Docker container).

```bat
pip install -r field_app\requirements.txt
pip install pyinstaller
cd field_app\build
pyinstaller field_app.spec --noconfirm
```

Result: `field_app/build/dist/ShotClassifierTerrain/` — a complete folder (~900 MB, due to bundled PyTorch/scikit-learn/XGBoost/LightGBM) containing `ShotClassifierTerrain.exe`. **Copy the whole folder** to the tablet (USB drive or network share). Double-click the exe: the browser opens automatically.

**Compatibility**: Windows 10/11, **x64 processor** only (not iPad, not Android, not guaranteed on Windows ARM).

> **Prerequisite on the target tablet, tested only on the development machine.** PyTorch and the other bundled native libraries generally need the **Microsoft Visual C++ Redistributable** (2015-2022) present on the system. Most recent Windows 10/11 installs already have it (installed via Windows Update), but this is not guaranteed on a tablet that has never been updated. If the exe refuses to start (a missing-DLL error), installing it fixes the problem: <https://aka.ms/vs/17/release/vc_redist.x64.exe> (free, ~15 MB, one time).

## 10.4 Networking with the Raspberry Pi

The connection direction is **RPi → tablet**: the RPi needs to know the tablet's IP.

1. **Check that both devices are on the same network.**
2. **Find the tablet's IP**:
   ```bat
   ipconfig
   ```
   Look for the "IPv4 Address" line of the active wifi adapter. *Careful*: on a `192.168.0.0/24` network, `192.168.0.1` is almost always the **router**, not the tablet — don't use that address.
3. **Allow the port through the Windows Firewall** (once, in an administrator PowerShell):
   ```powershell
   New-NetFirewallRule -DisplayName "Shot Classifier Terrain" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow -Profile Private
   ```
4. **Configure the RPi** with the tablet's IP and the API key shown at startup:
   ```bash
   python send_waveform.py --host 192.168.0.42 --api-key <key> --simulate
   ```
5. **Test connectivity before the code**:
   ```bash
   ping 192.168.0.42
   curl http://192.168.0.42:8765/api/status
   ```

**No router available**: the tablet can broadcast its own mobile hotspot (Settings → Network & Internet → Mobile hotspot); the RPi connects to it directly.

## 10.5 Testing without a sensor — the "Manual test" panel

Three ways to provide a test waveform:

- **Paste** 512 hexadecimal bytes separated by spaces.
- **Import a file** (📁): raw sensor file (`Triggered:XX XX...`), JSON `{"values": [...]}`, or hexadecimal text — format detected automatically.
- **Import a signal image** (🖼️): *approximate* extraction of a curve drawn on a solid background. Calibration defaults to assuming the bottom of the image is 0 and the top is 255 (adjustable); a chart of the extracted curve is always shown for visual verification before classifying. Reliable on a clean image with a solid background; not reliable on a photo (angle, lighting).

A selector lets you choose which target to simulate.

## 10.6 Storing captures and improving the models

Every capture received is durably logged in `field_app/data/captures.jsonl` (waveform + prediction), and every operator confirmation in `field_app/data/confirmations.jsonl` — two append-only files that survive restarts.

**Important point**: a prediction alone is not ground truth. Every history row has a **Verify** button letting an operator confirm or correct what the model proposed. Only **confirmed** captures constitute usable labeled data.

This verified field data **automatically** feeds retraining: on every cycle, the agent (`src/agent/ml_agent.py`) converts confirmed captures into an archive compatible with `src/data/parse_raw.py` (`src/data/import_field_captures.py`), dropped into `data/raw/incoming/` — no manual step needed. They form a separate `field` session, always added to training, never to the held-out test set.

---

# 11. Raspberry Pi sender script (`rpi_sender/`)

Depends on no external package (standard library only).

```bash
# Test without hardware (generates simulated waveforms)
python send_waveform.py --host 192.168.0.42 --api-key <key> --simulate

# Real usage
python send_waveform.py --host 192.168.0.42 --api-key <key>
```

**What's missing for real use**: the `capture_waveform()` function in `send_waveform.py` is an integration point to complete with the real hardware reading of the sensor (ADC, GPIO, serial port) — this repository does not contain the original acquisition code, only the classification pipeline from already-captured waveforms.

For unattended operation on Raspberry Pi boot, add this script to a `systemd` service or to `@reboot` in `crontab`.

---

# 12. CI/CD

- **CI** (`.github/workflows/ci.yml`): lint (ruff), unit tests, full re-run of the data and training pipeline on every push/PR to `main`.
- **CD** (`.github/workflows/cd.yml`): builds the Docker image and publishes it to GitHub Container Registry (`ghcr.io/mardom15/shot-classifier`), free for a public repository.

To push changes:

```bash
git add -A
git commit -m "message"
git push origin main
```

---

# 13. Repository structure

```
data/
  raw/                    original archive (not included in the public repo)
  processed/              parsed CSVs + enriched features
src/
  data/                   parsing (parse_raw.py) + feature extraction
                          + import_field_captures.py (reintegration of
                            confirmed field captures)
  models/                 classical model registry, 1D CNN, inference
  training/               training and comparison scripts
  monitoring/             data drift (Evidently) + Prometheus metrics
  agent/                  autonomous agent
  utils/                  shared configuration, label definitions
app/
  streamlit_app.py        bilingual demo app
field_app/                field app (Windows tablet), 18 targets
  server.py               FastAPI server
  targets.py              configuration of the 18 firing positions
  storage.py              capture/confirmation persistence
  static/                 web interface (HTML/CSS/JS, tactical theme)
  build/                  PyInstaller configuration
rpi_sender/                Raspberry Pi sender script
tests/                    unit tests
docs/reports/             training results, charts, drift
docker/
  prometheus/             Prometheus configuration
  grafana/                Grafana provisioning + dashboard
.github/workflows/        CI/CD
Dockerfile, docker-compose.yml
CAHIER_DES_CHARGES.md      full project specification (French)
README.md / README.fr.md   documentation (EN primary, FR secondary)
```

---

# 14. Confidentiality and intellectual property

The source data documents real tests with service weapons (G36, MP7, P8). The public GitHub repository (<https://github.com/MarDom15/shot-classifier>) has a **separate Git history**, distinct from the full local history: `data/` and `models_store/` were explicitly excluded (never present in the pushed history), and `.gitignore` prevents any accidental reintroduction.

**For anyone picking up this project**: the raw data and trained models must be obtained separately from the project owner, then placed locally in `data/raw/` and regenerated via `make train` — they are never added to a commit meant to be published.

---

# 15. Known limitations

- Modest research dataset (397 events) for an effectively 4-class task.
- Very minority control class (14 examples).
- Shot distance confounded with weapon in the test protocol — stage 2 must be interpreted with caution.
- Unknown sensor sampling frequency — spectral features are relative, not physical.
- The autonomous agent does not perform human validation before promoting a new model — only an F1 macro regression threshold holds it back.
- **Research prototype: not qualified for operational use** without further validation.

Full detail in `CAHIER_DES_CHARGES.md`, section 10.

---

# 16. Pitfalls found and fixed during development

This project was audited and extended iteratively; several real issues were found and fixed by systematically testing each feature rather than assuming it worked. Knowing them saves time rediscovering them:

1. **Windows paths misinterpreted by Git Bash** — Docker commands launched from Git Bash (MSYS) automatically translate certain paths starting with `/`, breaking volume mounts (`-v`). Fix: prefix with `MSYS_NO_PATHCONV=1`, or use PowerShell for Docker commands with mounts.
2. **NaN on a flat signal** — `scipy.stats.skew`/`kurtosis` return NaN for a zero-variance signal (e.g. a disconnected sensor), which crashes training ("Input X contains NaN"). Fixed in `src/data/features.py` (0.0 by convention instead of NaN).
3. **Malformed field captures** — a capture with a length other than 512 samples, if it reached training, would introduce NaNs there. `src/data/import_field_captures.py` now filters these captures before export.
4. **Image digitization calibration** — normalizing on the *observed* vertical span of the trace crushes a flat baseline with an isolated peak (mean error ~120/255 on a test signal). Fixed: normalization on the **full image height** (bottom=0, top=255 by default, adjustable).
5. **Streamlit's `/metrics` inactive at startup** — the Streamlit script only runs on a real browser session; Prometheus shows the target as `down` until someone has opened the app at least once.
6. **Port 8000 already in use** — often taken by another service on the host machine; remapped to host port 8002 (the port internal to the Docker network, used by Prometheus, stays 8000).
7. **Git history and confidentiality** — deleting a file in a new commit does not erase it from Git history; a clean history (without the data) was specifically rebuilt for publication.

---

# 17. Quick reference — commands and ports

## Essential commands

```bash
docker compose up --build -d      # start everything
docker compose down               # stop everything
docker compose logs -f agent      # watch the agent's logs live
make train                        # retrain all models (without Docker)
make test                         # run the tests
make lint                         # check code style (ruff)
python -m src.agent.ml_agent run  # one manual agent cycle
```

## Ports used

| Port | Service |
|---|---|
| 8501 | Streamlit app |
| 8002 (internal to the Docker network: 8000) | App's Prometheus metrics |
| 8001 | Agent's Prometheus metrics |
| 8765 | Field app (field_app) |
| 9090 | Prometheus |
| 3000 | Grafana |

---

*Document generated to accompany the repository <https://github.com/MarDom15/shot-classifier>. For any question about methodology or the project's limitations, refer first to `CAHIER_DES_CHARGES.md`.*
