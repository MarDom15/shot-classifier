# 🎯 Shot Classifier

*[English version](README.md)*

Classification de tirs (arme + détection de faux positifs) à partir de signaux d'impact capteur bruts, avec comparaison de plusieurs familles de modèles, une app de démonstration, et un pipeline CI/CD — le tout sur des outils gratuits, exécutable en local.

[![CI](https://github.com/MarDom15/shot-classifier/actions/workflows/ci.yml/badge.svg)](https://github.com/MarDom15/shot-classifier/actions/workflows/ci.yml)
[![CD](https://github.com/MarDom15/shot-classifier/actions/workflows/cd.yml/badge.svg)](https://github.com/MarDom15/shot-classifier/actions/workflows/cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)

Le cahier des charges complet (contexte, objectifs, exigences, méthodologie, limites connues, feuille de route) est dans [`CAHIER_DES_CHARGES.md`](CAHIER_DES_CHARGES.md) — à lire en premier pour comprendre les choix de conception.

## Le problème

Un capteur d'impact enregistre une fenêtre de 512 échantillons (ADC 8 bits) à chaque déclenchement. L'objectif est de déterminer, à partir de cette seule forme d'onde : (1) s'il s'agit d'un tir ou d'un impact non balistique (pierre, bruit parasite), et (2) si c'est un tir, avec quelle arme il a été tiré (G36, MP7, P8).

Le jeu de données de départ compte 397 événements étiquetés, répartis sur deux sessions d'enregistrement — voir la section données du cahier des charges pour le détail (déséquilibre des classes, confusion distance/arme, saturation ADC, etc.).

## Architecture retenue

Plutôt qu'un classifieur unique à 4 classes (qui noierait la classe témoin, 14 exemples sur 397), le pipeline est en deux étages :

```
forme d'onde (512 pts) ─▶ [Étage 1 : tir / non-tir] ─▶ si tir ─▶ [Étage 2 : G36 / MP7 / P8]
```

Chaque étage compare neuf approches sur les mêmes données, validées par un split **par session d'enregistrement** (jamais un tirage aléatoire, pour éviter une fuite d'information optimiste) :

- 8 modèles classiques sur des caractéristiques extraites du signal (temporelles + spectrales) : régression logistique, k-NN, SVM (RBF), arbre de décision, random forest, gradient boosting, XGBoost, LightGBM.
- 1 CNN 1D (PyTorch) entraîné directement sur les 512 échantillons bruts, sans extraction manuelle de caractéristiques.

### Résultats actuels (jeu de test = session 19090822)

| Étage | Meilleur modèle | Accuracy | F1 macro |
|---|---|---|---|
| 1 — tir vs non-tir | Gradient Boosting | 0.976 | **0.827** |
| 2 — identification de l'arme | CNN 1D | 0.580 | **0.583** |

Le tableau complet (9 modèles × 2 étages) est régénéré à chaque exécution dans `docs/reports/model_comparison_final.csv` / `.png`. L'étage 2 reste fragile hors des conditions d'enregistrement d'origine — c'est documenté et attendu, voir la section Limites du cahier des charges plutôt qu'un problème caché.

## Démarrage rapide

### Option A — en local (Python)

```bash
git clone https://github.com/MarDom15/shot-classifier.git
cd shot-classifier
pip install -r requirements-dev.txt
pip install --index-url https://download.pytorch.org/whl/cpu torch   # build CPU, plus léger

make train      # reconstruit le dataset, entraîne les 9 modèles x 2 étages, compare
make app        # lance l'app Streamlit sur http://localhost:8501
```

### Option B — avec Docker (recommandé, zéro dépendance à installer)

```bash
git clone https://github.com/MarDom15/shot-classifier.git
cd shot-classifier
docker compose up --build -d
```

Cette seule commande lance **deux conteneurs** : l'app Streamlit sur [http://localhost:8501](http://localhost:8501), et l'agent autonome (section suivante) qui tourne en arrière-plan et ré-entraîne périodiquement les modèles. Voir les logs de l'agent avec `docker compose logs -f agent`. Pour ne lancer que l'app sans l'agent : `docker compose up app`.

## Structure du dépôt

```
data/
  raw/                    archive d'origine (formes d'onde brutes)
  processed/              CSV parsés + caractéristiques enrichies
src/
  data/                   parsing (parse_raw.py) + extraction de caractéristiques (features.py)
  models/                 registre des modèles classiques, CNN 1D, service d'inférence unifié
  training/               scripts d'entraînement (classique, CNN) et de comparaison
  monitoring/             rapport de dérive des données (Evidently)
  agent/                  agent autonome : orchestre tout le cycle sans intervention manuelle
  utils/                  configuration partagée, définition des étiquettes
app/
  streamlit_app.py        démonstrateur : prédiction, comparaison des modèles, monitoring
tests/                    tests unitaires (parsing, features, labels, inférence)
docs/reports/             résultats d'entraînement, graphiques, rapport de dérive
.github/workflows/        CI (tests + lint) et CD (build + publication de l'image Docker)
Dockerfile, docker-compose.yml
CAHIER_DES_CHARGES.md
```

> **Note sur les données** : `data/` et `models_store/` ne sont pas inclus dans ce dépôt public — les données sources documentent des essais de tir réels avec du matériel militaire (G36, MP7, P8) et nécessitent une autorisation préalable avant toute diffusion (voir `CAHIER_DES_CHARGES.md`, section 11). Elles sont fournies séparément aux personnes autorisées, et utilisées telles quelles une fois placées dans le dépôt.

## Pipeline de données

```bash
python -m src.data.parse_raw     # archive .zip -> data/processed/brocksettel_waveforms_raw.csv
python -m src.data.features      # -> data/processed/brocksettel_features_enriched.csv
```

Le parsing gère deux anomalies connues du format d'origine (voir docstrings) : des fichiers contenant deux événements concaténés sans saut de ligne, et un fichier orphelin hors arborescence — les deux sont documentés et testés (`tests/test_parse_raw.py`).

## Entraînement et comparaison des modèles

```bash
python -m src.training.train_classical   # 8 modèles classiques, 2 étages
python -m src.training.train_cnn         # CNN 1D, 2 étages
python -m src.training.compare_models    # tableau + graphique comparatif final
```

Tous les modèles entraînés sont sauvegardés dans `models_store/<étage>/<modèle>.{joblib,pt}`, avec le nom du meilleur dans `best_model.txt` — l'app Streamlit et le service d'inférence (`src/models/inference.py`) s'appuient dessus pour comparer les prédictions de tous les modèles sur un même exemple.

## Agent autonome (ML/DL)

`src/agent/ml_agent.py` orchestre tout le cycle de vie du pipeline sans intervention manuelle : reconstruction du jeu de données, entraînement des 9 modèles sur les 2 étages, sélection du meilleur par étage, détection de dérive, et journalisation d'un rapport de run (`docs/reports/agent/run_log.jsonl`). Avant chaque ré-entraînement, il sauvegarde une copie horodatée des modèles courants (`models_store_history/`) ; si le nouveau modèle est significativement moins bon que le précédent, il revient automatiquement en arrière (rollback).

**Comment le lancer :**

```bash
# Un seul cycle (utile pour tester ou déclencher un ré-entraînement à la main)
python -m src.agent.ml_agent run

# Mode autonome : tourne indéfiniment, un cycle toutes les 6h par défaut
python -m src.agent.ml_agent watch --interval 21600
```

Ou, plus simplement, avec Docker — l'agent démarre automatiquement en arrière-plan avec `docker compose up` (service `agent` dans `docker-compose.yml`). Pour changer la fréquence sans modifier le fichier :

```bash
AGENT_INTERVAL_SECONDS=3600 docker compose up -d   # un cycle par heure
```

**Ajouter de nouvelles données sans toucher au code** : déposer une nouvelle archive `.zip` (même structure que l'archive d'origine) dans `data/raw/incoming/`. L'agent la détecte au cycle suivant, la fusionne avec les données existantes (avec déduplication automatique), et ré-entraîne tous les modèles dessus.

### Agent Claude Code

En plus de l'orchestrateur Python ci-dessus, ce dépôt fournit un **sub-agent Claude Code** prêt à l'emploi : [`.claude/agents/shot-classifier-agent.md`](.claude/agents/shot-classifier-agent.md). Ouvre ce dépôt dans Claude Code et demande simplement, en langage naturel : *"relance l'agent ML"*, *"ré-entraîne les modèles"*, *"vérifie la dérive"*, *"mets à jour le projet avec la nouvelle archive"*, etc. — Claude Code invoque automatiquement ce sub-agent (grâce à son champ `description`), qui exécute directement les commandes nécessaires (`python -m src.agent.ml_agent run`, tests, lint...) sans attendre de validation étape par étape, puis rapporte un résumé structuré (statut, F1 macro par étage, rollback éventuel, anomalies). Aucune configuration supplémentaire : le fichier est détecté automatiquement dès que Claude Code ouvre le dossier `shot-classifier/`.

## Monitoring

L'onglet **Monitoring** de l'app Streamlit journalise chaque prédiction (`monitoring/prediction_log.jsonl`) et peut générer à la demande un rapport de dérive des données ([Evidently](https://www.evidentlyai.com/)) comparant les caractéristiques du trafic reçu à celles du jeu d'entraînement :

```bash
python -m src.monitoring.drift   # -> docs/reports/drift_report.html
```

En conditions réelles, la population « courante » du rapport serait remplacée par les caractéristiques recalculées sur les prédictions récentes plutôt que par la session de test — voir le cahier des charges, section monitoring.

## CI/CD

- **CI** (`.github/workflows/ci.yml`) : lint (ruff), tests unitaires (parsing, features, inférence, **agent** — cycle complet + rollback), ré-exécution complète du pipeline de données et d'entraînement sur chaque push/PR vers `main` — garantit que le projet reste reproductible de bout en bout.
- **CD** (`.github/workflows/cd.yml`) : construit l'image Docker et la publie sur **GitHub Container Registry** (`ghcr.io/mardom15/shot-classifier`), gratuit pour un dépôt public — aucun compte cloud payant nécessaire.

## Limites connues (résumé — détail dans le cahier des charges)

Jeu de données de recherche modeste (397 événements), classe témoin très minoritaire (14 exemples), distance de tir confondue avec l'arme dans le protocole d'essai, saturation ADC sur une partie des tirs P8, et signification encore incertaine de certains préfixes de fichiers (U, V, Ts) dans les données sources. Ce projet est un prototype de recherche, pas un système qualifié pour un usage opérationnel.

## Licence

[MIT](LICENSE) — © 2026 Martial Domche
