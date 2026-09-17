# Envoi Raspberry Pi — Shot Classifier

Script à exécuter sur le Raspberry Pi connecté au capteur d'impact : il
capture une forme d'onde et l'envoie à l'app terrain qui tourne sur la
tablette Windows (`field_app/`), sur le wifi commun, pour classification
immédiate.

**Ne dépend d'aucun paquet externe** (seulement la bibliothèque standard
Python), pour rester simple à déployer sur un Raspberry Pi.

## Ce qui est fourni et ce qui ne l'est pas

- ✅ La partie réseau : configuration, envoi HTTP authentifié, gestion des
  erreurs de connexion, boucle continue.
- ✅ Un mode `--simulate` qui génère des formes d'onde plausibles pour tester
  toute la chaîne (RPi → wifi → tablette → classification → affichage) sans
  aucun capteur branché.
- ❌ La lecture réelle du capteur (ADC, GPIO, port série...) : ce dépôt ne
  contient pas le code d'acquisition matérielle d'origine — seulement le
  pipeline de classification à partir de formes d'onde déjà capturées (voir
  `CAHIER_DES_CHARGES.md`, section 4). C'est le rôle de la fonction
  `capture_waveform()` dans `send_waveform.py`, clairement marquée, à
  compléter avec votre propre lecture matérielle.

## Configuration

Au premier lancement, `instance/config.json` est créé :

```json
{
  "host": "192.168.1.42",
  "port": 8765,
  "api_key": "",
  "sensor_id": "rpi-01",
  "interval_s": 2.0,
  "simulate": false
}
```

- `host` : adresse IP de la **tablette** sur le wifi commun (pas celle du
  routeur — sur un réseau `192.168.0.0/24`, `192.168.0.1` est presque
  toujours le routeur, pas la tablette). Voir
  [`field_app/README.md`](../field_app/README.md#mise-en-réseau-avec-le-raspberry-pi)
  pour la procédure complète (trouver l'IP de la tablette, ouvrir le
  pare-feu Windows, tester la connectivité avant de lancer ce script).
- `api_key` : copier exactement la clé affichée au démarrage de
  `field_app/server.py` (ou lue dans `field_app/instance/config.json`).
- `sensor_id` : identifiant libre si plusieurs capteurs/RPi sont déployés.

## Tester sans matériel

```bash
python send_waveform.py --host 192.168.1.42 --api-key <clé> --simulate
```

Envoie une forme d'onde simulée toutes les `interval_s` secondes ; environ
30 % simulent un impact marqué pour vérifier que l'alerte "tir détecté"
s'affiche bien côté tablette.

## Usage réel

1. Compléter `capture_waveform()` dans `send_waveform.py` avec la lecture
   matérielle réelle (512 échantillons, ADC 8 bits, voir le format exact
   dans `CAHIER_DES_CHARGES.md` section 4).
2. Lancer :
   ```bash
   python send_waveform.py --host 192.168.1.42 --api-key <clé>
   ```
3. Pour un fonctionnement autonome au démarrage du RPi, ajouter ce script à
   un service systemd ou à `@reboot` dans crontab.
