# Cahier des charges — Shot Classifier

**Projet :** Classification de tirs à partir de signaux d'impact capteur
**Porteur :** Martial Domche
**Statut :** Prototype de recherche (v0.1)
**Dernière mise à jour :** Septembre 2026

---

## 1. Contexte

Un capteur d'impact (probablement piézo-électrique ou accéléromètre, d'après la forme du signal) enregistre une fenêtre de 512 échantillons codés sur 8 bits à chaque déclenchement. Un jeu de données d'essais en conditions réelles a été constitué sur deux sessions d'enregistrement, avec trois armes (G36, MP7, P8) et une classe témoin d'impacts non balistiques (« Steine », des pierres), dans le but de déterminer si un modèle de machine learning peut, à partir de la seule forme d'onde, distinguer un tir d'un bruit parasite puis identifier l'arme utilisée.

Ce document formalise les objectifs, le périmètre, les exigences et la méthodologie retenue pour construire, comparer et déployer les modèles de classification correspondants. Il s'appuie sur l'analyse exploratoire des données déjà réalisée (voir `data/processed/` et l'historique du projet) et sur les résultats d'entraînement produits par ce dépôt (`docs/reports/`).

> ⚠️ **Point d'attention avant toute publication.** Ces données proviennent d'essais de tir réels avec du matériel militaire. Avant de rendre ce dépôt public ou de le partager en dehors d'un cercle restreint, il convient de vérifier auprès de l'organisation ayant produit les données (propriété intellectuelle, confidentialité, réglementation export-control le cas échéant) que leur diffusion — y compris sous forme dérivée (CSV, caractéristiques statistiques, modèles entraînés) — est autorisée. Ce point est développé en section 11.

## 2. Objectifs

### 2.1 Objectif général

Disposer d'un pipeline reproductible qui, à partir d'une forme d'onde brute, détecte un tir puis identifie l'arme, avec une comparaison objective de plusieurs familles de modèles pour justifier le choix retenu — et un démonstrateur déployable pour évaluer la faisabilité en conditions réelles.

### 2.2 Objectifs mesurables (critères de succès du prototype)

| # | Objectif | Critère de succès | Statut actuel |
|---|---|---|---|
| O1 | Détecter un tir vs un impact non balistique | F1 macro ≥ 0.80 en validation inter-session | ✅ Atteint (Gradient Boosting, 0.827) |
| O2 | Identifier l'arme utilisée parmi 3 | F1 macro ≥ 0.80 en validation inter-session | ❌ Non atteint (meilleur : CNN 1D, 0.583) — voir section 9 |
| O3 | Comparer objectivement plusieurs familles de modèles | ≥ 5 modèles distincts évalués avec la même méthodologie | ✅ 9 modèles (8 classiques + 1 CNN) |
| O4 | Fournir un démonstrateur utilisable sans compétence ML | App accessible via navigateur, prédiction en < 2 s | ✅ App Streamlit |
| O5 | Rendre le pipeline reproductible et automatisé | CI qui re-génère les données et ré-entraîne les modèles à chaque changement | ✅ GitHub Actions |
| O6 | Permettre un déploiement sans coût d'infrastructure | Fonctionne entièrement en local via Docker, aucun service payant requis | ✅ Docker + GHCR (gratuit pour dépôt public) |

L'objectif O2 n'étant pas atteint, ce projet reste au stade *prototype de recherche* : il ne doit pas être présenté comme un système de détection fiable pour un usage opérationnel (voir section 10, Limites).

## 3. Périmètre

**Inclus dans ce projet :**
- Parsing et validation du jeu de données brut (formes d'onde + métadonnées).
- Extraction de caractéristiques temporelles et spectrales.
- Entraînement et comparaison de 9 modèles de classification sur 2 étages.
- Application de démonstration (Streamlit) : prédiction interactive, comparaison des modèles, journal de monitoring, rapport de dérive des données.
- Conteneurisation (Docker) et pipeline CI/CD (GitHub Actions) reposant uniquement sur des outils gratuits.

**Explicitement hors périmètre (pour une version ultérieure) :**
- Acquisition de nouvelles données (notamment pour enrichir la classe témoin, très minoritaire).
- Calibration physique du capteur (fréquence d'échantillonnage réelle, conversion en unités physiques).
- Déploiement sur du matériel embarqué temps réel (le capteur final utiliserait probablement un microcontrôleur, pas un serveur Docker — voir la note d'architecture en section 8.4).
- Certification / qualification du système pour un usage opérationnel.
- Authentification, gestion multi-utilisateurs ou tout aspect « produit » de l'app de démonstration (elle est conçue comme un outil d'évaluation interne, pas comme un service exposé publiquement).

## 4. Données

Résumé (voir l'analyse exploratoire complète dans l'historique du projet pour le détail) :

- **397 événements** exploitables, répartis en G36 (141), MP7 (140), P8 (102), Steine/pierres (14).
- **Deux sessions d'enregistrement** distinctes (probablement 2019-08-04 et 2019-09-08), utilisées comme découpage train/test — jamais un tirage aléatoire (section 8.1).
- **Format** : 512 échantillons ADC 8 bits par événement, ligne de base ≈ 128 (signal centré, capteur AC-couplé). Fréquence d'échantillonnage réelle inconnue — les caractéristiques spectrales sont donc exprimées en cycles/fenêtre, pas en Hz.
- **Anomalies connues et gérées** : fichiers contenant deux événements concaténés sans saut de ligne (31 fichiers, séparés automatiquement par le parseur), un fichier orphelin hors arborescence (exclu, documenté), saturation ADC sur une partie des tirs P8 en mode K (jusqu'à ~59 % des échantillons saturés sur certains fichiers).
- **Déséquilibre et confusions structurelles** : la classe témoin (Steine) ne représente que 3,5 % des exemples ; la distance de tir est confondue avec l'arme (chaque arme n'a été testée qu'à un sous-ensemble de distances qui se recoupe à peine avec les autres armes).
- **Zones d'ombre** : la signification exacte des variables H/K (mode de tir ? munition ?) et des préfixes de fichiers minoritaires (U, V, Ts) reste à confirmer avec l'équipe ayant conduit les essais.

## 5. Architecture fonctionnelle

```
                 ┌───────────────────────────┐
 forme d'onde ──▶│  Extraction caractéristiques │──▶ features (temporelles + spectrales)
 (512 pts)       └───────────────────────────┘
                              │
                              ▼
                 ┌───────────────────────────┐
                 │  Étage 1 : Tir / Non-tir    │  (Gradient Boosting recommandé)
                 └──────────────┬────────────┘
                                │ si "tir"
                                ▼
                 ┌───────────────────────────┐
                 │  Étage 2 : G36 / MP7 / P8   │  (CNN 1D recommandé, avec réserves)
                 └───────────────────────────┘
```

Ce découpage en deux étages a été retenu (plutôt qu'un classifieur unique à 4 classes) pour éviter que la classe témoin, très minoritaire, ne soit noyée dans un problème multiclasse déséquilibré, et parce qu'il correspond à l'usage opérationnel probable : d'abord écarter les fausses alertes, ensuite qualifier le tir.

## 6. Exigences fonctionnelles

| ID | Exigence | Implémentation |
|---|---|---|
| F1 | Reconstruire le jeu de données tabulaire à partir de l'archive brute | `src/data/parse_raw.py` |
| F2 | Extraire des caractéristiques exploitables par les modèles classiques | `src/data/features.py` |
| F3 | Entraîner et sauvegarder plusieurs modèles classiques par étage | `src/training/train_classical.py` |
| F4 | Entraîner un modèle sur le signal brut sans extraction manuelle | `src/training/train_cnn.py` (CNN 1D) |
| F5 | Comparer tous les modèles sur une métrique commune | `src/training/compare_models.py` |
| F6 | Prédire à partir d'une forme d'onde arbitraire, avec tous les modèles disponibles | `src/models/inference.py` |
| F7 | Interface utilisateur pour tester une prédiction sans coder | `app/streamlit_app.py`, onglet Prédiction |
| F8 | Visualiser la comparaison des modèles dans l'interface | `app/streamlit_app.py`, onglet Comparaison |
| F9 | Journaliser les prédictions effectuées | `monitoring/prediction_log.jsonl` |
| F10 | Détecter une dérive des données par rapport au jeu d'entraînement | `src/monitoring/drift.py` (Evidently) |
| F11 | Orchestrer le cycle complet (données → entraînement → comparaison → dérive) sans intervention manuelle | `src/agent/ml_agent.py`, commande `run` |
| F12 | Tourner en continu et se relancer périodiquement sans supervision | `src/agent/ml_agent.py`, commande `watch` |
| F13 | Ingérer de nouvelles sessions d'enregistrement sans modification de code | `data/raw/incoming/` (archives `.zip` détectées et fusionnées automatiquement) |
| F14 | Revenir automatiquement sur la version précédente d'un modèle en cas de régression de performance | `src/agent/ml_agent.py` : snapshot avant ré-entraînement + rollback si F1 macro chute de plus de 0.02 |

## 7. Exigences non-fonctionnelles

- **NF1 — Coût nul d'infrastructure.** Aucune dépendance à un service cloud payant : Docker en local, GitHub Actions (gratuit pour dépôt public, 2000 min/mois pour un dépôt privé), GitHub Container Registry (gratuit pour dépôt public).
- **NF2 — Reproductibilité.** Toute personne clonant le dépôt doit pouvoir reconstruire le jeu de données et ré-entraîner tous les modèles avec `make train`, sans étape manuelle cachée. Vérifié par la CI à chaque push.
- **NF3 — Portabilité.** Fonctionne sur Linux/Mac/Windows via Docker ; installation Python pure documentée comme alternative.
- **NF4 — Traçabilité des résultats.** Chaque exécution d'entraînement écrit ses métriques et sa matrice de confusion dans `docs/reports/`, horodatées implicitement par l'historique Git.
- **NF5 — Lisibilité et maintenabilité.** Code organisé en modules à responsabilité unique (`data/`, `models/`, `training/`, `monitoring/`), lint automatique (ruff) en CI.
- **NF6 — Temps de réponse de l'app.** Une prédiction (tous modèles confondus) doit s'afficher en moins de 2 secondes sur un poste standard (mesuré : < 1 s pour les modèles classiques, CNN inclus).
- **NF7 — Confidentialité des données.** Voir section 11 — les données sources ne doivent pas être supposées librement diffusables sans vérification préalable.
- **NF8 — Autonomie supervisable.** L'agent (section 8.6) fonctionne sans intervention manuelle, mais chaque action qu'il prend (ré-entraînement, rollback) doit rester traçable a posteriori (journal `docs/reports/agent/run_log.jsonl`) — pas de boîte noire.

## 8. Méthodologie

### 8.1 Découpage train/test

Le split se fait **par session d'enregistrement** (`GROUP_COL = "session"` dans `src/utils/config.py`), jamais par tirage aléatoire. Justification : les deux sessions ont pu avoir des conditions légèrement différentes (gain du capteur, montage, météo) ; un split aléatoire mélangerait ces conditions entre train et test et donnerait un score de généralisation artificiellement optimiste. La session la plus récente (19090822) sert de jeu de test.

### 8.2 Modèles comparés

**Sur caractéristiques extraites** (`src/models/classical.py`) : régression logistique, k-NN, SVM à noyau RBF, arbre de décision, random forest, gradient boosting, XGBoost, LightGBM — tous encapsulés dans un pipeline scikit-learn avec standardisation.

**Sur signal brut** (`src/models/cnn1d.py`) : un CNN 1D compact (3 blocs convolution/pooling, ~15k paramètres), volontairement petit pour limiter le sur-apprentissage vu la taille du jeu de données.

### 8.3 Caractéristiques extraites

Temporelles : moyenne, écart-type, min/max, amplitude crête à crête, position et amplitude du pic, énergie, écart absolu moyen, taux de saturation ADC, taux de passages par zéro, temps de montée, asymétrie (skewness), aplatissement (kurtosis).

Spectrales (FFT sur la fenêtre de 512 points, en cycles/fenêtre faute de fréquence d'échantillonnage connue) : fréquence dominante, centroïde spectral, énergie dans les tiers bas/moyen/haut du spectre, planéité spectrale.

### 8.4 Note d'architecture — vers l'embarqué

Ce prototype tourne sur un serveur (conteneur Docker). Si l'objectif final est une détection temps réel sur le terrain, le modèle retenu (probablement Gradient Boosting pour l'étage 1, qui est un modèle léger à évaluer) devrait être réimplémenté ou exporté (ONNX, ou règles d'arbres traduites en C) pour tourner sur le microcontrôleur du capteur plutôt que sur un serveur — ce point n'est pas traité dans ce dépôt et constitue une étape ultérieure distincte.

### 8.5 Métriques

Le F1 macro est retenu comme métrique de comparaison principale (plutôt que l'accuracy seule), car il ne surestime pas la performance sur la classe majoritaire dans un contexte déséquilibré — en particulier pour l'étage 1, où la classe « non-tir » ne représente que 3,5 % des exemples.

### 8.6 Agent autonome

`src/agent/ml_agent.py` automatise l'exécution répétée de tout ce qui précède (8.1 à 8.5) pour qu'aucune étape ne dépende d'une action manuelle :

1. **Ingestion** — détecte toute nouvelle archive `.zip` déposée dans `data/raw/incoming/`, la fusionne avec l'archive d'origine (déduplication par session/dossier/fichier/index d'événement), et reconstruit `data/processed/`.
2. **Entraînement** — relance `train_classical`, `train_cnn` et `compare_models` dans l'ordre.
3. **Sécurité** — avant d'écraser les modèles courants, sauvegarde un instantané horodaté (`models_store_history/`) ; si le nouveau F1 macro d'un étage chute de plus de 0.02 par rapport au précédent, revient automatiquement à l'instantané (rollback), en le journalisant.
4. **Supervision** — régénère le rapport de dérive des données (Evidently) et écrit une entrée JSON par cycle dans `docs/reports/agent/run_log.jsonl` (statut, métriques avant/après, décision de rollback, erreurs éventuelles).

Deux modes d'exécution : `run` (un cycle, puis arrêt — pour déclencher un ré-entraînement à la demande) et `watch --interval N` (boucle indéfiniment, un cycle toutes les N secondes — pour un fonctionnement totalement autonome, typiquement comme service Docker en arrière-plan). Le seuil de tolérance à la régression (0.02) et l'intervalle par défaut (6h) sont des valeurs de départ raisonnables pour un prototype, à ajuster une fois des données de production disponibles.

**Limite assumée** : l'agent ne fait aucune hypothèse sur *pourquoi* une nouvelle session de données a été déposée (nouvelle arme, nouveau site, recalibration du capteur...) — il se contente de fusionner et de ré-entraîner. Une vraie mise en production demanderait une validation humaine avant promotion, pas seulement un garde-fou automatique sur le F1 macro.

## 9. Résultats actuels et interprétation

Voir `docs/reports/model_comparison_final.csv` et `.png` pour les chiffres à jour (régénérés à chaque exécution). Au moment de la rédaction :

**Étage 1 (tir vs non-tir)** : Gradient Boosting arrive en tête (F1 macro 0.827, accuracy 97.6 %), suivi de XGBoost (0.794). Le CNN 1D sur signal brut est en retrait (0.671) — plausible vu le très petit nombre d'exemples de la classe témoin (14 au total, dont une poignée seulement dans le jeu de test), insuffisant pour qu'un réseau de neurones apprenne une représentation robuste, alors qu'une caractéristique simple et explicite (la position du pic, très tôt dans la fenêtre pour les pierres) suffit à un arbre pour bien séparer les classes.

**Étage 2 (identification de l'arme)** : aucun modèle ne dépasse 0.58 de F1 macro. Le CNN 1D est en tête (0.583) devant les modèles classiques (0.47–0.49). Ce résultat, décevant au regard de l'objectif O2, s'explique probablement par la confusion structurelle entre distance et arme dans le protocole d'essai (section 4) : les modèles ont pu apprendre des artefacts propres aux distances testées dans la session d'entraînement plutôt qu'une signature intrinsèque de l'arme, et échouent à généraliser à la session de test qui ne couvre pas les mêmes distances pour chaque arme.

**Conclusion méthodologique** : ce résultat n'est pas un échec du pipeline mais une découverte utile — il indique clairement qu'il faut soit collecter des données croisées (les trois armes à toutes les distances) avant d'espérer un modèle d'identification d'arme fiable, soit restreindre l'étage 2 à des distances comparables entre armes.

## 10. Limites connues

- Jeu de données de taille modeste (397 événements) pour une tâche à 4 classes effectives.
- Classe témoin très minoritaire (14 exemples) — risque de sur-optimisme sur l'étage 1 malgré la validation inter-session.
- Distance de tir confondue avec l'arme (section 4) — l'étage 2 doit être interprété avec prudence.
- Fréquence d'échantillonnage du capteur inconnue — les caractéristiques spectrales sont relatives, pas physiques.
- Signification incertaine des modes H/K et des préfixes de fichiers minoritaires (U, V, Ts).
- Le rapport de dérive des données (section monitoring) compare à la session de test faute de véritable flux de production ; à remplacer par un historique réel de prédictions dès que disponible.
- L'agent autonome (8.6) ne fait pas de validation humaine avant de promouvoir un nouveau modèle — seul un seuil de régression sur le F1 macro le retient. Suffisant pour ce prototype, pas pour une mise en production.
- Prototype de recherche : **non qualifié pour un usage opérationnel** sans validation supplémentaire (données, robustesse, tests terrain).

## 11. Confidentialité et propriété intellectuelle

Les données sources documentent des essais réels avec des armes de service (G36, MP7, P8) sur un terrain d'essai. Selon leur origine (essai interne d'un fabricant, d'un centre d'essai militaire, etc.), elles peuvent être soumises à des règles de confidentialité, de propriété intellectuelle, voire à une réglementation de contrôle des exportations. **Avant de rendre ce dépôt public sur GitHub**, il est recommandé de :

1. Confirmer auprès de l'organisation propriétaire des données que leur diffusion (y compris sous forme dérivée : CSV parsés, caractéristiques statistiques, modèles entraînés qui encodent implicitement des propriétés du signal) est autorisée.
2. À défaut, créer le dépôt en **privé** (gratuit sur GitHub, y compris pour les Actions dans une certaine limite de minutes/mois), ou publier uniquement le code (`src/`, `app/`, tests, CI/CD) sans les dossiers `data/` ni `models_store/`, qui peuvent être ajoutés au `.gitignore` et fournis séparément aux personnes autorisées.
3. Vérifier si le nom du site d'essai ou d'autres métadonnées (noms de dossiers, dates) doivent être anonymisés avant publication.

Ce point n'engage pas la validité technique du projet, mais conditionne la façon dont il peut être partagé.

## 12. Feuille de route

| Priorité | Action | Objectif visé |
|---|---|---|
| Haute | Trancher la question de confidentialité (section 11) avant toute publication publique | — |
| Haute | Collecter des tirs des trois armes à des distances communes | Lever la confusion distance/arme, améliorer O2 |
| Haute | Enrichir la classe témoin (autres bruits parasites que les pierres) | Fiabiliser l'étage 1 en conditions réelles |
| Moyenne | Faire confirmer par l'équipe terrain la signification de H/K et des préfixes U/V/Ts | Fiabiliser les caractéristiques utilisées |
| Moyenne | Obtenir la fréquence d'échantillonnage réelle du capteur | Passer des caractéristiques spectrales relatives à des unités physiques (Hz) |
| Moyenne | Étudier l'export du modèle de l'étage 1 vers une cible embarquée | Préparer un futur déploiement temps réel (section 8.4) |
| Basse | Étendre le monitoring à un vrai flux de prédictions en production | Rapport de dérive plus représentatif (section 10) |

## 13. Glossaire

- **Étage / stage** : une des deux étapes du pipeline de classification (détection puis identification).
- **F1 macro** : moyenne non pondérée du F1-score de chaque classe — pénalise les modèles qui négligent les classes minoritaires.
- **Split par session** : découpage train/test qui garde toutes les données d'une session d'enregistrement ensemble, par opposition à un tirage aléatoire ligne par ligne.
- **Dérive des données (data drift)** : changement de la distribution statistique des données reçues en production par rapport aux données d'entraînement, signe potentiel de dégradation du modèle.
