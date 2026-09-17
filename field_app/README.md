# App terrain — Shot Classifier

Application Windows autonome pour tablette : reçoit les formes d'onde d'un
Raspberry Pi sur le wifi commun et affiche la classification (tir/non-tir,
puis arme) en temps réel, avec une interface tactile aux couleurs militaires
(olive/kaki, alerte rouge sur détection de tir).

Contrairement à `app/streamlit_app.py` (démonstrateur pour explorer/comparer
les modèles), cette app est pensée pour un usage opérationnel léger : un
seul écran, lisible de loin, qui réagit automatiquement à chaque nouvelle
capture envoyée par le capteur — sans manipulation.

## Architecture

```
Raspberry Pi (capteur)  --wifi commun-->  Tablette Windows (field_app)
  rpi_sender/send_waveform.py                  server.py (FastAPI)
  POST /ingest {values: [512 octets]}          --> classification (src/models/inference.py)
                                                --> push WebSocket --> navigateur (static/)
```

Un seul secret partagé (clé API générée au premier lancement, voir ci-dessous)
authentifie les envois du Raspberry Pi. L'interface web est servie localement
par le même processus — aucune connexion internet requise, tout tourne sur
le wifi local.

## Lancement en développement (avec Python déjà installé)

```bash
pip install -r field_app/requirements.txt
python field_app/server.py
```

Le navigateur par défaut s'ouvre automatiquement sur `http://localhost:8765/`.
La clé API à donner au Raspberry Pi s'affiche dans la console et est
enregistrée dans `field_app/instance/config.json`.

## Construire l'exécutable Windows autonome (pour la tablette)

Nécessite un Python natif Windows (pas seulement Docker) car PyInstaller ne
peut pas produire un `.exe` Windows depuis un conteneur Linux.

```bat
pip install -r field_app\requirements.txt
pip install pyinstaller
cd field_app\build
pyinstaller field_app.spec --noconfirm
```

Résultat : `field_app/build/dist/ShotClassifierTerrain/` — un dossier complet
(~900 Mo, à cause de PyTorch/scikit-learn/XGBoost/LightGBM embarqués) contenant
`ShotClassifierTerrain.exe`. **Copier tout le dossier** sur la tablette (clé
USB ou partage réseau) ; aucune installation de Python ni de Docker n'est
nécessaire sur la tablette elle-même.

Double-clic sur `ShotClassifierTerrain.exe` : le navigateur par défaut de
Windows s'ouvre automatiquement sur l'interface.

## Configuration

Au premier lancement (dev ou exe), un fichier `instance/config.json` est créé
à côté de l'exécutable :

```json
{
  "host": "0.0.0.0",
  "port": 8765,
  "api_key": "généré aléatoirement",
  "max_history": 50
}
```

- `api_key` : à copier dans la configuration du script `rpi_sender/` (voir
  son propre README).
- `port` : à changer si 8765 est déjà utilisé sur la tablette.
- Supprimer ce fichier régénère une nouvelle clé API au prochain lancement.

## Vérifier que tout fonctionne sans capteur

Le panneau **🧪 Test manuel** de l'interface permet de coller 512 octets
hexadécimaux (par exemple depuis l'onglet Prédiction de `app/streamlit_app.py`)
et de déclencher une classification sans matériel — utile pour valider le
déploiement avant de brancher le vrai capteur.

## Sécurité et limites

- La clé API protège contre un envoi accidentel ou trivial depuis un autre
  appareil du même wifi ; ce n'est pas un chiffrement de bout en bout — sur
  un wifi partagé non maîtrisé, le trafic entre le RPi et la tablette reste
  visible en clair (HTTP, pas HTTPS).
- Comme tout le reste du projet, ceci est un prototype de recherche : voir
  `CAHIER_DES_CHARGES.md` (limites, section 10) avant tout usage opérationnel.
