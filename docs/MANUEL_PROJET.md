% Shot Classifier — Manuel complet du projet
% Martial Domche
% Septembre 2026

# 1. Vue d'ensemble

**Shot Classifier** est un pipeline de machine learning qui, à partir d'une forme d'onde brute captée par un capteur d'impact (512 échantillons, ADC 8 bits), détermine :

1. s'il s'agit d'un **tir** ou d'un **impact non balistique** (pierre, bruit parasite) ;
2. si c'est un tir, **avec quelle arme** il a été tiré (G36, MP7, P8).

Le projet comprend :

- un **pipeline de données et d'entraînement** (parsing, extraction de caractéristiques, 9 modèles comparés sur 2 étages) ;
- une **app de démonstration** (Streamlit) pour tester et comparer les modèles ;
- un **agent autonome** qui orchestre tout le cycle de vie (ingestion, ré-entraînement, rollback, dérive) sans intervention manuelle ;
- une **app terrain** pour tablette Windows, connectée à 18 postes de tir (Raspberry Pi) sur le wifi local, avec classification en temps réel ;
- un **script d'envoi** pour Raspberry Pi ;
- une pile de **monitoring** (Prometheus + Grafana) ;
- un pipeline **CI/CD** (GitHub Actions).

Le dépôt public est sur GitHub : <https://github.com/MarDom15/shot-classifier>

> **Important — confidentialité des données.** Les données sources documentent des essais de tir réels avec des armes de service (G36, MP7, P8). Le dépôt public ne contient **pas** les données brutes ni les modèles entraînés (voir section 14) — ils sont fournis séparément aux personnes autorisées.

## 1.1 Architecture retenue

```
forme d'onde (512 pts) ──▶ [Étage 1 : tir / non-tir] ──▶ si tir ──▶ [Étage 2 : G36 / MP7 / P8]
```

Ce découpage en deux étages évite de noyer la classe témoin (« Steine », pierres — 14 exemples sur 397) dans un problème multiclasse déséquilibré. Chaque étage compare 9 modèles (8 classiques + 1 CNN 1D), validés par un split **par session d'enregistrement** (jamais aléatoire, pour éviter une fuite d'information optimiste).

### Résultats actuels (jeu de test = session 19090822)

| Étage | Meilleur modèle | Accuracy | F1 macro |
|---|---|---|---|
| 1 — tir vs non-tir | Gradient Boosting | 0.976 | **0.827** |
| 2 — identification de l'arme | CNN 1D | 0.580 | **0.583** |

L'étage 2 reste fragile hors des conditions d'enregistrement d'origine — c'est documenté et attendu (voir `CAHIER_DES_CHARGES.md`, section Limites), pas un problème caché.

---

# 2. Prérequis et installation

Pour reprendre ce projet de zéro sur une nouvelle machine, il faut installer :

| Outil | Usage | Où l'obtenir |
|---|---|---|
| **Git** | Cloner le dépôt | <https://git-scm.com/downloads> |
| **Docker Desktop** | Lancer toute la stack (app, agent, monitoring) sans rien installer d'autre | <https://www.docker.com/products/docker-desktop/> |
| **Python 3.11 (64 bits)** | Optionnel : usage sans Docker, ou pour construire l'exécutable de l'app terrain | <https://www.python.org/downloads/> |
| **GitHub CLI (`gh`)** | Optionnel : pousser des changements vers GitHub en ligne de commande | <https://cli.github.com/> |

**Sur Windows**, Python peut aussi s'installer via :

```powershell
winget install Python.Python.3.11
```

Vérifier les installations :

```bash
git --version
docker --version
docker compose version
python --version
```

## 2.1 Récupérer le projet

```bash
git clone https://github.com/MarDom15/shot-classifier.git
cd shot-classifier
```

> Le dépôt public ne contient que le **code** — `data/` et `models_store/` sont vides (juste un `.gitkeep`). Pour un usage complet (entraînement réel), il faut obtenir séparément l'archive de données auprès du responsable du projet et la placer dans `data/raw/200924_Brocksettel.zip`, puis lancer `make train` (section 5) pour reconstruire `models_store/`.

---

# 3. Démarrage rapide — Option recommandée (Docker)

C'est la manière la plus simple et la plus fiable de lancer tout le projet, sans rien installer d'autre que Docker.

```bash
cd shot-classifier
docker compose up --build -d
```

Cette seule commande construit l'image et démarre **quatre conteneurs** :

| Service | URL locale | Rôle |
|---|---|---|
| `app` | <http://localhost:8501> | App Streamlit (démonstrateur, prédiction, comparaison) |
| `agent` | — (tourne en arrière-plan) | Ré-entraînement automatique périodique |
| `prometheus` | <http://localhost:9090> | Collecte des métriques |
| `grafana` | <http://localhost:3000> | Tableaux de bord de monitoring |

Pour arrêter proprement :

```bash
docker compose down
```

Pour ne lancer que l'app sans l'agent ni le monitoring :

```bash
docker compose up app
```

Pour voir les logs de l'agent en direct :

```bash
docker compose logs -f agent
```

## 3.1 Identifiants et accès

| Service | Identifiants |
|---|---|
| App Streamlit (8501) | Aucun |
| Prometheus (9090) | Aucun |
| Grafana (3000) — **consulter** | Aucun (accès anonyme activé) |
| Grafana (3000) — **administrer** | `admin` / `admin` (change de mot de passe demandé à la première connexion admin) |

> **Sécurité.** Aucun de ces services n'a de protection robuste par mot de passe — c'est voulu pour un usage 100 % local. Ne jamais exposer ces ports sur internet sans revoir cette configuration (changer le mot de passe Grafana, désactiver l'accès anonyme, ajouter une authentification Prometheus).

---

# 4. Option B — Installation Python native (sans Docker)

```bash
cd shot-classifier
pip install -r requirements-dev.txt
pip install --index-url https://download.pytorch.org/whl/cpu torch   # build CPU, plus léger

make train      # reconstruit le dataset, entraîne les 9 modèles x 2 étages
make app        # lance l'app Streamlit sur http://localhost:8501
```

**Sur Windows**, si `python`/`pip` ne sont pas reconnus après installation, c'est généralement que Python n'a pas été ajouté au PATH — réinstaller en cochant « Add python.exe to PATH », ou utiliser `winget install Python.Python.3.11`.

---

# 5. Pipeline de données

```bash
python -m src.data.parse_raw     # archive .zip -> data/processed/brocksettel_waveforms_raw.csv
python -m src.data.features      # -> data/processed/brocksettel_features_enriched.csv
```

Le parsing gère deux anomalies connues du format d'origine (documentées et testées dans `tests/test_parse_raw.py`) :

- des fichiers contenant deux événements concaténés sans saut de ligne ;
- un fichier orphelin hors arborescence attendue.

---

# 6. Entraînement et comparaison des modèles

```bash
python -m src.training.train_classical   # 8 modèles classiques, 2 étages
python -m src.training.train_cnn         # CNN 1D, 2 étages
python -m src.training.compare_models    # tableau + graphique comparatif final
```

Tous les modèles entraînés sont sauvegardés dans `models_store/<étage>/<modèle>.{joblib,pt}`, avec le nom du meilleur dans `best_model.txt`. L'app Streamlit et le service d'inférence (`src/models/inference.py`) s'appuient dessus pour comparer les prédictions de tous les modèles sur un même exemple.

Le tableau complet est régénéré à chaque exécution dans `docs/reports/model_comparison_final.csv` / `.png`.

---

# 7. Agent autonome (ML/DL)

`src/agent/ml_agent.py` orchestre tout le cycle de vie sans intervention manuelle : reconstruction du dataset, entraînement des 9 modèles sur les 2 étages, sélection du meilleur par étage, sauvegarde avec rollback, détection de dérive, journalisation.

## 7.1 Modes de lancement

```bash
# Un seul cycle (utile pour tester ou déclencher un ré-entraînement à la main)
python -m src.agent.ml_agent run

# Mode autonome : tourne indéfiniment, un cycle toutes les 6h par défaut
python -m src.agent.ml_agent watch --interval 21600
```

Avec Docker, l'agent démarre automatiquement en mode `watch` via le service `agent` de `docker-compose.yml`. Pour changer la fréquence sans modifier le fichier :

```bash
AGENT_INTERVAL_SECONDS=3600 docker compose up -d   # un cycle par heure
```

## 7.2 Sécurité — rollback automatique

Avant chaque ré-entraînement, l'agent sauvegarde une copie horodatée des modèles courants (`models_store_history/`). Si le nouveau modèle est significativement moins bon que le précédent (F1 macro en baisse de plus de 0.02), il revient automatiquement en arrière et le journalise — ce n'est pas une erreur, c'est le garde-fou qui fonctionne comme prévu.

## 7.3 Ajouter de nouvelles données sans toucher au code

Déposer une nouvelle archive `.zip` (même structure que l'archive d'origine) dans `data/raw/incoming/`. L'agent la détecte au cycle suivant, la fusionne avec les données existantes (déduplication automatique), et ré-entraîne tous les modèles dessus.

## 7.4 Agent Claude Code

Un sub-agent Claude Code prêt à l'emploi est fourni : `.claude/agents/shot-classifier-agent.md`. Ouvrir ce dépôt dans Claude Code et demander, en langage naturel : *« relance l'agent ML »*, *« ré-entraîne les modèles »*, *« vérifie la dérive »* — Claude Code invoque automatiquement ce sub-agent, qui exécute les commandes nécessaires sans attendre de validation étape par étape, puis rapporte un résumé structuré.

---

# 8. App Streamlit (démonstrateur)

Accessible sur <http://localhost:8501>. Quatre onglets :

- **🔮 Prédiction** — tester une forme d'onde (exemple du jeu de données, ou coller 512 valeurs hexadécimales), voir la prédiction de tous les modèles.
- **📊 Comparaison des modèles** — tableau et graphique des 9 modèles × 2 étages.
- **🩺 Monitoring** — journal des prédictions effectuées, génération à la demande d'un rapport de dérive des données (Evidently).
- **ℹ️ À propos** — contexte du projet.

L'interface est **bilingue FR/EN** (sélecteur dans la barre latérale, préférence mémorisée dans le navigateur).

---

# 9. Monitoring — Prometheus et Grafana

## 9.1 Ce qui est mesuré

**App Streamlit** (`/metrics` sur le port 8000, exposé côté hôte sur **8002** — le port 8000 est souvent déjà utilisé par autre chose sur la machine) :

- nombre de prédictions, par résultat (tir/non-tir) et par arme ;
- latence d'inférence.

**Agent** (`/metrics` sur le port **8001**, actif uniquement en mode `watch`) :

- nombre de cycles par statut (succès/erreur) ;
- F1 macro du meilleur modèle par étage, au dernier cycle ;
- taille du jeu de données ;
- nombre de rollbacks automatiques déclenchés ;
- durée d'un cycle complet.

## 9.2 Tableau de bord

Un dashboard **« Shot Classifier »** est provisionné automatiquement dans Grafana (aucune configuration manuelle) : <http://localhost:3000/d/shot-classifier/shot-classifier>

Six panneaux : prédictions par résultat, latence p95, F1 macro par étage, cycles de l'agent par statut, rollbacks, événements dans le dataset, dernière exécution de l'agent, prédictions par arme.

## 9.3 Particularité à connaître

Le `/metrics` de l'app Streamlit ne s'active **qu'après qu'un vrai navigateur ait ouvert la page au moins une fois** — Streamlit n'exécute son script Python que sur une session de navigateur réelle (WebSocket), pas sur une simple requête HTTP. Prometheus affichera cette cible comme `down` jusque-là ; ce n'est pas un bug, il suffit d'ouvrir <http://localhost:8501> une fois.

---

# 10. App terrain (tablette Windows + Raspberry Pi)

Pour un usage sur le terrain plutôt que l'exploration, `field_app/` est une application Windows autonome (empaquetable en `.exe` avec PyInstaller — aucun Python ni Docker requis sur la tablette) qui reçoit les formes d'onde de **18 postes de tir** (Raspberry Pi) sur le wifi local et classe chaque tir en direct.

## 10.1 Les 18 cibles

Chaque poste de tir a une adresse IP fixe, de **192.168.0.41 à 192.168.0.58** (`field_app/targets.py`). L'identification se fait par **l'adresse IP source** de la requête reçue — pas par une valeur envoyée dans le JSON — donc un Raspberry Pi mal configuré ne peut pas usurper l'identité d'une autre cible.

L'interface affiche une grille de 18 boîtes de contrôle (numéro, IP, indicateur coloré : gris = pas de donnée, vert = dernier évènement non-tir, rouge = dernier tir détecté avec l'arme). Cliquer sur une boîte « épingle » son détail (forme d'onde, confiance) ; un bouton permet de revenir au suivi automatique du dernier évènement toutes cibles confondues.

Pour changer le nombre de cibles ou la plage d'IP : modifier `FIRST_OCTET` et `N_TARGETS` dans `field_app/targets.py`.

## 10.2 Lancer en développement

```bash
pip install -r field_app/requirements.txt
python field_app/server.py
```

Le navigateur par défaut s'ouvre automatiquement sur <http://localhost:8765/>. La clé API à donner au Raspberry Pi s'affiche dans la console et est enregistrée dans `field_app/instance/config.json`.

## 10.3 Construire l'exécutable Windows autonome

Nécessite un **Python natif Windows** (PyInstaller ne peut pas produire un `.exe` Windows depuis un conteneur Linux/Docker).

```bat
pip install -r field_app\requirements.txt
pip install pyinstaller
cd field_app\build
pyinstaller field_app.spec --noconfirm
```

Résultat : `field_app/build/dist/ShotClassifierTerrain/` — un dossier complet (~900 Mo, à cause de PyTorch/scikit-learn/XGBoost/LightGBM embarqués) contenant `ShotClassifierTerrain.exe`. **Copier tout le dossier** sur la tablette (clé USB ou partage réseau). Double-clic sur l'exe : le navigateur s'ouvre automatiquement.

**Compatibilité** : Windows 10/11, **processeur x64** uniquement (pas iPad, pas Android, pas garanti sur Windows ARM).

> **Prérequis sur la tablette cible, testé uniquement sur la machine de développement.** PyTorch et les autres bibliothèques natives embarquées ont généralement besoin du **Microsoft Visual C++ Redistributable** (2015-2022) présent sur le système. La plupart des Windows 10/11 récents l'ont déjà (installé par Windows Update), mais ce n'est pas garanti sur une tablette jamais mise à jour. Si l'exe refuse de démarrer (erreur de DLL manquante), l'installer résout le problème : <https://aka.ms/vs/17/release/vc_redist.x64.exe> (gratuit, ~15 Mo, une seule fois).

## 10.4 Mise en réseau avec le Raspberry Pi

Le sens de la connexion est **RPi → tablette** : le RPi doit connaître l'IP de la tablette.

1. **Vérifier que les deux appareils sont sur le même réseau.**
2. **Trouver l'IP de la tablette** :
   ```bat
   ipconfig
   ```
   Chercher la ligne « Adresse IPv4 » de l'adaptateur wifi actif. *Attention* : sur un réseau `192.168.0.0/24`, `192.168.0.1` est presque toujours le **routeur**, pas la tablette — ne pas utiliser cette adresse.
3. **Autoriser le port dans le pare-feu Windows** (une fois, en PowerShell administrateur) :
   ```powershell
   New-NetFirewallRule -DisplayName "Shot Classifier Terrain" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow -Profile Private
   ```
4. **Configurer le RPi** avec l'IP de la tablette et la clé API affichée au démarrage :
   ```bash
   python send_waveform.py --host 192.168.0.42 --api-key <clé> --simulate
   ```
5. **Tester la connectivité avant le code** :
   ```bash
   ping 192.168.0.42
   curl http://192.168.0.42:8765/api/status
   ```

**Sans routeur disponible** : la tablette peut diffuser son propre point d'accès mobile (Paramètres → Réseau et Internet → Point d'accès mobile) ; le RPi s'y connecte directement.

## 10.5 Tester sans capteur — panneau « Test manuel »

Trois façons de fournir une forme d'onde de test :

- **Coller** 512 octets hexadécimaux séparés par des espaces.
- **Importer un fichier** (📁) : fichier brut du capteur (`Triggered:XX XX...`), JSON `{"values": [...]}`, ou texte hexadécimal — format détecté automatiquement.
- **Importer une image du signal** (🖼️) : extraction *approximative* d'une courbe tracée sur fond uni. La calibration suppose par défaut que le bas de l'image vaut 0 et le haut 255 (ajustable) ; un graphique de la courbe extraite s'affiche systématiquement pour vérification visuelle avant classification. Fiable sur une image nette à fond uni ; peu fiable sur une photo (angle, éclairage).

Un sélecteur permet de choisir quelle cible simuler.

## 10.6 Stockage des captures et amélioration des modèles

Chaque capture reçue est enregistrée durablement dans `field_app/data/captures.jsonl` (forme d'onde + prédiction), et chaque validation d'un opérateur dans `field_app/data/confirmations.jsonl` — deux fichiers en ajout seul, qui survivent aux redémarrages.

**Point important** : une prédiction seule n'est pas une vérité terrain. Chaque ligne de l'historique a un bouton **Vérifier** permettant à un opérateur de confirmer ou corriger ce que le modèle a proposé. Seules les captures **confirmées** constituent une donnée labellisée exploitable.

Ces données de terrain vérifiées alimentent **automatiquement** le ré-entraînement : à chaque cycle, l'agent (`src/agent/ml_agent.py`) convertit les captures confirmées en une archive compatible avec `src/data/parse_raw.py` (`src/data/import_field_captures.py`), déposée dans `data/raw/incoming/` — aucune étape manuelle nécessaire. Elles forment une session `field` à part, toujours ajoutée à l'entraînement, jamais au jeu de test tenu à l'écart.

---

# 11. Script d'envoi Raspberry Pi (`rpi_sender/`)

Ne dépend d'aucun paquet externe (bibliothèque standard uniquement).

```bash
# Test sans matériel (génère des formes d'onde simulées)
python send_waveform.py --host 192.168.0.42 --api-key <clé> --simulate

# Usage réel
python send_waveform.py --host 192.168.0.42 --api-key <clé>
```

**Ce qui manque pour un usage réel** : la fonction `capture_waveform()` dans `send_waveform.py` est un point d'intégration à compléter avec la lecture matérielle réelle du capteur (ADC, GPIO, port série) — ce dépôt ne contient pas le code d'acquisition d'origine, seulement le pipeline de classification à partir de formes d'onde déjà capturées.

Pour un fonctionnement autonome au démarrage du Raspberry Pi, ajouter ce script à un service `systemd` ou à `@reboot` dans `crontab`.

---

# 12. CI/CD

- **CI** (`.github/workflows/ci.yml`) : lint (ruff), tests unitaires, ré-exécution complète du pipeline de données et d'entraînement sur chaque push/PR vers `main`.
- **CD** (`.github/workflows/cd.yml`) : construit l'image Docker et la publie sur GitHub Container Registry (`ghcr.io/mardom15/shot-classifier`), gratuit pour un dépôt public.

Pour pousser des changements :

```bash
git add -A
git commit -m "message"
git push origin main
```

---

# 13. Structure du dépôt

```
data/
  raw/                    archive d'origine (non incluse dans le dépôt public)
  processed/              CSV parsés + caractéristiques enrichies
src/
  data/                   parsing (parse_raw.py) + extraction de features
                          + import_field_captures.py (reintegration des
                            captures terrain confirmees)
  models/                 registre des modèles classiques, CNN 1D, inférence
  training/               scripts d'entraînement et de comparaison
  monitoring/             dérive des données (Evidently) + métriques Prometheus
  agent/                  agent autonome
  utils/                  configuration partagée, définition des étiquettes
app/
  streamlit_app.py        démonstrateur bilingue
field_app/                app terrain (tablette Windows), 18 cibles
  server.py               serveur FastAPI
  targets.py              configuration des 18 postes
  storage.py              persistance des captures/confirmations
  static/                 interface web (HTML/CSS/JS, thème militaire)
  build/                  configuration PyInstaller
rpi_sender/                script d'envoi côté Raspberry Pi
tests/                    tests unitaires
docs/reports/             résultats d'entraînement, graphiques, dérive
docker/
  prometheus/             configuration Prometheus
  grafana/                provisioning + dashboard Grafana
.github/workflows/        CI/CD
Dockerfile, docker-compose.yml
CAHIER_DES_CHARGES.md      spécifications complètes du projet
README.md / README.fr.md   documentation (EN principal, FR secondaire)
```

---

# 14. Confidentialité et propriété intellectuelle

Les données sources documentent des essais réels avec des armes de service (G36, MP7, P8). Le dépôt GitHub public (<https://github.com/MarDom15/shot-classifier>) est un **historique Git à part**, distinct de l'historique local complet : `data/` et `models_store/` ont été explicitement exclus (jamais présents dans l'historique poussé), et le `.gitignore` empêche toute réintroduction accidentelle.

**Pour toute personne reprenant ce projet** : les données brutes et les modèles entraînés doivent être obtenus séparément auprès du responsable du projet, puis placés localement dans `data/raw/` et régénérés via `make train` — ils ne sont jamais ajoutés à un commit destiné à être publié.

---

# 15. Limites connues du projet

- Jeu de données de recherche modeste (397 événements) pour une tâche à 4 classes effectives.
- Classe témoin très minoritaire (14 exemples).
- Distance de tir confondue avec l'arme dans le protocole d'essai — l'étage 2 doit être interprété avec prudence.
- Fréquence d'échantillonnage du capteur inconnue — les caractéristiques spectrales sont relatives, pas physiques.
- L'agent autonome ne fait pas de validation humaine avant de promouvoir un nouveau modèle — seul un seuil de régression sur le F1 macro le retient.
- **Prototype de recherche : non qualifié pour un usage opérationnel** sans validation supplémentaire.

Détail complet dans `CAHIER_DES_CHARGES.md`, section 10.

---

# 16. Pièges rencontrés et résolus pendant le développement

Ce projet a été audité et étendu de façon itérative ; plusieurs problèmes réels ont été trouvés et corrigés en testant systématiquement chaque fonctionnalité plutôt qu'en supposant qu'elle marchait. Les connaître évite de perdre du temps à les redécouvrir :

1. **Chemins Windows mal interprétés par Git Bash** — les commandes Docker lancées depuis Git Bash (MSYS) traduisent automatiquement certains chemins commençant par `/`, cassant les montages de volumes (`-v`). Solution : préfixer avec `MSYS_NO_PATHCONV=1`, ou utiliser PowerShell pour les commandes Docker avec montages.
2. **NaN sur signal plat** — `scipy.stats.skew`/`kurtosis` renvoient NaN pour un signal à variance nulle (ex. capteur déconnecté), ce qui fait planter l'entraînement (« Input X contains NaN »). Corrigé dans `src/data/features.py` (0.0 par convention plutôt que NaN).
3. **Captures terrain malformées** — une capture de longueur différente de 512 échantillons, si elle atteignait l'entraînement, y introduirait des NaN. `src/data/import_field_captures.py` filtre maintenant ces captures avant export.
4. **Calibration de la digitalisation d'image** — normaliser sur l'étendue verticale *observée* de la trace écrase une ligne de base plate avec un pic isolé (erreur moyenne ~120/255 sur un signal de test). Corrigé : normalisation sur la **hauteur totale de l'image** (bas=0, haut=255 par défaut, ajustable).
5. **`/metrics` de Streamlit inactif au démarrage** — le script Streamlit ne s'exécute que sur une vraie session navigateur ; Prometheus affiche la cible comme `down` tant que personne n'a ouvert l'app au moins une fois.
6. **Port 8000 déjà utilisé** — souvent pris par un autre service sur la machine hôte ; remappé sur le port hôte 8002 (le port interne au réseau Docker, utilisé par Prometheus, reste 8000).
7. **Historique Git et confidentialité** — supprimer un fichier dans un nouveau commit ne l'efface pas de l'historique Git ; un historique propre (sans les données) a été reconstruit spécifiquement pour la publication.

---

# 17. Référence rapide — commandes et ports

## Commandes essentielles

```bash
docker compose up --build -d      # tout lancer
docker compose down               # tout arrêter
docker compose logs -f agent      # logs de l'agent en direct
make train                        # ré-entraîner tous les modèles (sans Docker)
make test                         # lancer les tests
make lint                         # vérifier le style du code (ruff)
python -m src.agent.ml_agent run  # un cycle d'agent manuel
```

## Ports utilisés

| Port | Service |
|---|---|
| 8501 | App Streamlit |
| 8002 (interne au réseau Docker : 8000) | Métriques Prometheus de l'app |
| 8001 | Métriques Prometheus de l'agent |
| 8765 | App terrain (field_app) |
| 9090 | Prometheus |
| 3000 | Grafana |

---

*Document généré pour accompagner le dépôt <https://github.com/MarDom15/shot-classifier>. Pour toute question de méthodologie ou de limites du projet, se référer en priorité à `CAHIER_DES_CHARGES.md`.*
