# 🎯 Shot Classifier

*[Version française](README.md)*

Shot classification (weapon identification + false-positive detection) from raw sensor impact signals, comparing several families of models, with a demo app and a CI/CD pipeline — all built on free tools, runnable entirely locally.

[![CI](https://github.com/MarDom15/shot-classifier/actions/workflows/ci.yml/badge.svg)](https://github.com/MarDom15/shot-classifier/actions/workflows/ci.yml)
[![CD](https://github.com/MarDom15/shot-classifier/actions/workflows/cd.yml/badge.svg)](https://github.com/MarDom15/shot-classifier/actions/workflows/cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)

The full specification document (context, objectives, requirements, methodology, known limitations, roadmap) lives in [`CAHIER_DES_CHARGES.md`](CAHIER_DES_CHARGES.md) (French) — read it first to understand the design choices.

## The problem

An impact sensor records a 512-sample window (8-bit ADC) on every trigger. The goal is to determine, from that waveform alone: (1) whether it is a gunshot or a non-ballistic impact (a thrown rock, spurious noise), and (2) if it is a shot, which weapon fired it (G36, MP7, P8).

The starting dataset has 397 labeled events across two recording sessions — see the data section of the specification document for details (class imbalance, distance/weapon confound, ADC saturation, etc.).

## Chosen architecture

Rather than a single 4-class classifier (which would drown the control class, 14 examples out of 397), the pipeline runs in two stages:

```
waveform (512 pts) ─▶ [Stage 1: shot / non-shot] ─▶ if shot ─▶ [Stage 2: G36 / MP7 / P8]
```

Each stage compares nine approaches on the same data, validated with a split **by recording session** (never a random split, to avoid optimistic information leakage):

- 8 classical models on features extracted from the signal (time-domain + spectral): logistic regression, k-NN, SVM (RBF), decision tree, random forest, gradient boosting, XGBoost, LightGBM.
- 1 1D CNN (PyTorch) trained directly on the 512 raw samples, with no manual feature extraction.

### Current results (test set = session 19090822)

| Stage | Best model | Accuracy | F1 macro |
|---|---|---|---|
| 1 — shot vs non-shot | Gradient Boosting | 0.976 | **0.827** |
| 2 — weapon identification | 1D CNN | 0.580 | **0.583** |

The full table (9 models × 2 stages) is regenerated on every run in `docs/reports/model_comparison_final.csv` / `.png`. Stage 2 remains fragile outside the original recording conditions — this is documented and expected, see the Limitations section of the specification document rather than a hidden issue.

## Quick start

### Option A — locally (Python)

```bash
git clone https://github.com/MarDom15/shot-classifier.git
cd shot-classifier
pip install -r requirements-dev.txt
pip install --index-url https://download.pytorch.org/whl/cpu torch   # CPU build, much lighter

make train      # rebuilds the dataset, trains the 9 models x 2 stages, compares them
make app        # launches the Streamlit app on http://localhost:8501
```

### Option B — with Docker (recommended, zero dependency to install)

```bash
git clone https://github.com/MarDom15/shot-classifier.git
cd shot-classifier
docker compose up --build -d
```

This single command starts **two containers**: the Streamlit app on [http://localhost:8501](http://localhost:8501), and the autonomous agent (next section) that runs in the background and periodically retrains the models. Watch the agent's logs with `docker compose logs -f agent`. To run only the app without the agent: `docker compose up app`.

## Repository structure

```
data/
  raw/                    original archive (raw waveforms) — not published, see below
  processed/              parsed CSVs + enriched features — not published, see below
src/
  data/                   parsing (parse_raw.py) + feature extraction (features.py)
  models/                 classical model registry, 1D CNN, unified inference service
  training/               training scripts (classical, CNN) and comparison
  monitoring/             data drift report (Evidently)
  agent/                  autonomous agent: orchestrates the whole lifecycle unattended
  utils/                  shared configuration, label definitions
app/
  streamlit_app.py        demo app: prediction, model comparison, monitoring
tests/                    unit tests (parsing, features, labels, inference)
docs/reports/             training results, charts, drift report
.github/workflows/        CI (tests + lint) and CD (build + publish the Docker image)
Dockerfile, docker-compose.yml
CAHIER_DES_CHARGES.md
```

> **Note on data**: `data/` and `models_store/` are not included in this public repository — the source data documents real live-fire tests with service weapons (G36, MP7, P8) and requires prior authorization before any redistribution (see `CAHIER_DES_CHARGES.md`, section 11). They are available to authorized parties on request, and are used as-is once placed in the repository.

## Data pipeline

```bash
python -m src.data.parse_raw     # .zip archive -> data/processed/brocksettel_waveforms_raw.csv
python -m src.data.features      # -> data/processed/brocksettel_features_enriched.csv
```

Parsing handles two known anomalies in the original format (see docstrings): files containing two events concatenated with no line break, and one orphan file outside the expected folder structure — both are documented and tested (`tests/test_parse_raw.py`).

## Training and model comparison

```bash
python -m src.training.train_classical   # 8 classical models, 2 stages
python -m src.training.train_cnn         # 1D CNN, 2 stages
python -m src.training.compare_models    # final comparison table + chart
```

All trained models are saved under `models_store/<stage>/<model>.{joblib,pt}`, with the best model's name in `best_model.txt` — the Streamlit app and the inference service (`src/models/inference.py`) rely on this to compare every model's predictions on the same example.

## Autonomous agent (ML/DL)

`src/agent/ml_agent.py` orchestrates the entire pipeline lifecycle unattended: rebuilding the dataset, training the 9 models across the 2 stages, selecting the best model per stage, drift detection, and logging a run report (`docs/reports/agent/run_log.jsonl`). Before each retraining, it saves a timestamped snapshot of the current models (`models_store_history/`); if the new model is significantly worse than the previous one, it automatically rolls back.

**How to run it:**

```bash
# A single cycle (useful for testing or triggering a retrain manually)
python -m src.agent.ml_agent run

# Autonomous mode: runs indefinitely, one cycle every 6h by default
python -m src.agent.ml_agent watch --interval 21600
```

Or, more simply, with Docker — the agent starts automatically in the background with `docker compose up` (the `agent` service in `docker-compose.yml`). To change the frequency without editing the file:

```bash
AGENT_INTERVAL_SECONDS=3600 docker compose up -d   # one cycle per hour
```

**Adding new data without touching the code**: drop a new `.zip` archive (same structure as the original archive) into `data/raw/incoming/`. The agent picks it up on the next cycle, merges it with the existing data (with automatic deduplication), and retrains all models on it.

### Claude Code agent

In addition to the Python orchestrator above, this repository ships a ready-to-use **Claude Code sub-agent**: [`.claude/agents/shot-classifier-agent.md`](.claude/agents/shot-classifier-agent.md). Open this repository in Claude Code and simply ask, in plain language: *"rerun the ML agent"*, *"retrain the models"*, *"check for drift"*, *"update the project with the new archive"*, etc. — Claude Code automatically invokes this sub-agent (via its `description` field), which runs the necessary commands directly (`python -m src.agent.ml_agent run`, tests, lint...) without waiting for step-by-step confirmation, then reports a structured summary (status, F1 macro per stage, any rollback, anomalies). No extra configuration needed: the file is detected automatically as soon as Claude Code opens the `shot-classifier/` folder.

## Monitoring

The **Monitoring** tab of the Streamlit app logs every prediction (`monitoring/prediction_log.jsonl`) and can generate, on demand, a data drift report ([Evidently](https://www.evidentlyai.com/)) comparing the features of the traffic received against the training set:

```bash
python -m src.monitoring.drift   # -> docs/reports/drift_report.html
```

In a real deployment, the report's "current" population would be replaced by features recomputed on recent predictions rather than the test session — see the specification document, monitoring section.

## CI/CD

- **CI** (`.github/workflows/ci.yml`): lint (ruff), unit tests (parsing, features, inference, **agent** — full cycle + rollback), full re-run of the data and training pipeline on every push/PR to `main` — guarantees the project stays reproducible end to end.
- **CD** (`.github/workflows/cd.yml`): builds the Docker image and publishes it to **GitHub Container Registry** (`ghcr.io/mardom15/shot-classifier`), free for a public repository — no paid cloud account required.

## Known limitations (summary — details in the specification document)

Modest research dataset (397 events), very minority control class (14 examples), shot distance confounded with weapon in the test protocol, ADC saturation on part of the P8 shots, and still-uncertain meaning of some source file prefixes (U, V, Ts) in the source data. This project is a research prototype, not a system qualified for operational use.

## License

[MIT](LICENSE) — © 2026 Martial Domche
