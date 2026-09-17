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

## Langue

L'interface est bilingue FR/EN — sélecteur **FR | EN** en haut à droite. Le
choix est mémorisé dans le navigateur (`localStorage`) et survit à un
redémarrage de l'app.

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

## Mise en réseau avec le Raspberry Pi

Le sens de la connexion est **RPi → tablette** : le RPi doit connaître
l'adresse IP de la tablette (pas l'inverse). Sur un réseau `192.168.0.0/24`,
`192.168.0.1` est presque toujours l'adresse du **routeur/box**, pas celle de
la tablette ni du RPi — ne pas la mettre dans la config du RPi sauf cas
particulier (voir plus bas).

**1. Vérifier que les deux appareils sont sur le même réseau**, connectés au
même wifi/routeur (le RPi peut être en wifi ou en Ethernet, peu importe, du
moment que c'est le même réseau IP que la tablette).

**2. Trouver l'IP de la tablette** (c'est celle-ci qu'il faut donner au RPi) :

```bat
ipconfig
```

Chercher la ligne `Adresse IPv4` de l'adaptateur wifi actif — quelque chose
comme `192.168.0.42`. C'est cette adresse (pas `192.168.0.1`) qui va dans la
config du RPi.

**3. Autoriser le port dans le pare-feu Windows** (bloqué par défaut pour les
connexions entrantes) — à faire une fois, en PowerShell administrateur sur la
tablette :

```powershell
New-NetFirewallRule -DisplayName "Shot Classifier Terrain" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow -Profile Private
```

**4. Configurer le RPi** (`rpi_sender/instance/config.json` ou `--host`) avec
l'IP trouvée à l'étape 2 et la clé API affichée au démarrage de
`field_app` :

```bash
python send_waveform.py --host 192.168.0.42 --api-key <clé> --simulate
```

**5. Tester la connectivité avant le code Python**, directement depuis le
RPi, pour isoler un problème réseau d'un problème applicatif :

```bash
ping 192.168.0.42
curl http://192.168.0.42:8765/api/status
```

Si `ping` échoue : ce n'est pas un problème de ce projet, mais de réseau
(pas le même wifi, isolation clients activée sur le routeur — fréquent sur
les box grand public en mode "invité" — ou pare-feu). Si `ping` fonctionne
mais pas `curl` : revoir l'étape 3 (pare-feu) ou le port dans la config.

### Cas particulier : pas de routeur disponible sur le terrain

Si aucune infrastructure wifi n'est disponible, la tablette Windows peut
elle-même diffuser son propre point d'accès (**Paramètres → Réseau et
Internet → Point d'accès mobile**) : le RPi s'y connecte comme à n'importe
quel wifi. Dans ce cas, l'IP à utiliser côté RPi n'est pas `192.168.0.1`
mais celle affichée dans les paramètres du point d'accès de la tablette
(souvent `192.168.137.1` par défaut sous Windows) — à vérifier avec
`ipconfig` comme à l'étape 2. C'est l'option la plus simple à déployer sur
le terrain : aucune dépendance à un routeur tiers.

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
