# Envoi Raspberry Pi — Shot Classifier

Deux scripts à exécuter sur le Raspberry Pi, selon comment les capteurs
livrent leurs données, pour relayer chaque forme d'onde vers l'app terrain
(`field_app/`) sur la tablette Windows :

| Script | Cas d'usage |
|---|---|
| `send_waveform.py` | **Un capteur lu directement par ce RPi** (ADC/GPIO/série branché dessus). Ne dépend d'aucun paquet externe. |
| `tcp_bridge.py` | **Plusieurs capteurs**, chacun relié à son propre boîtier de contrôle (IP fixe), qui envoient leurs données au RPi **par le réseau (TCP)** — le RPi agrège et relaie vers la tablette avec la bonne cible. Nécessite Pillow (voir plus bas). |

## `send_waveform.py` — un capteur lu directement sur ce RPi

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

## `tcp_bridge.py` — plusieurs capteurs relayés par le réseau

Pour le cas où chaque capteur est relié à son propre boîtier de contrôle
(ex. un automate Siemens LOGO! 8) avec une **IP fixe**, qui envoie ses
données par **TCP** vers ce Raspberry Pi — celui-ci agrège tout et relaie
vers la tablette avec la bonne cible.

```bash
pip install -r requirements-tcp-bridge.txt   # Pillow, pour decoder les images
python tcp_bridge.py
```

Au premier lancement, `instance/tcp_bridge_config.json` est créé :

```json
{
  "tablet_host": "192.168.1.42",
  "tablet_port": 8765,
  "api_key": "",
  "listen_host": "0.0.0.0",
  "listen_port": 9000,
  "ip_to_target": {
    "192.168.1.101": 1,
    "192.168.1.102": 2
  }
}
```

- `ip_to_target` : associe l'IP fixe de chaque boîtier de contrôle à sa
  cible (1-18, voir `field_app/targets.py`) — c'est cette table qui permet
  à un seul RPi de relayer plusieurs cibles distinctement (le RPi précise
  alors `target_id` dans chaque envoi vers la tablette, voir
  [`field_app/README.md`](../field_app/README.md#les-18-cibles)).
- `listen_port` : port TCP sur lequel les boîtiers se connectent (à ajuster
  selon ce que le technicien configure de son côté).

**Contenu accepté par paquet, détecté automatiquement** : soit 512 octets
bruts (échantillons ADC 0-255), soit une **image** (PNG/JPEG/BMP/GIF) de la
forme d'onde — auquel cas elle est digitalisée automatiquement (même
méthode approximative que le panneau *Test manuel* de l'app terrain, voir
`image_digitize.py` ; fiable sur une image nette à fond uni).

### ⚠️ Hypothèses par défaut à confirmer avec le technicien

Ce script a été écrit avant d'avoir toutes les précisions sur le protocole
exact — deux hypothèses raisonnables sont prises par défaut, clairement
marquées dans le code (`tcp_bridge.py`, en tête de fichier) :

1. **Identification du capteur par IP source** de la connexion entrante
   (table `ip_to_target`). Si le système du technicien distingue plutôt les
   capteurs autrement (port, identifiant dans le message...), adapter
   `identify_sensor()`.
2. **Un message = le contenu complet d'une connexion TCP** (le boîtier se
   connecte, envoie une forme d'onde, ferme la connexion). Si le système
   réel garde une connexion ouverte pour plusieurs messages à la suite, il
   faudra ajouter un découpage explicite (longueur préfixée ou délimiteur)
   dans `handle_connection()`.

### Tester sans matériel

```bash
python tcp_bridge.py --simulate-sensor 127.0.0.1 --interval 2
```

Dans un autre terminal, lancer `python tcp_bridge.py` (sans arguments) pour
qu'il écoute — le capteur simulé s'y connecte et envoie des formes d'onde en
continu. Ajouter l'IP utilisée (`127.0.0.1` pour un test local) à
`ip_to_target` dans la configuration pour voir la bonne cible s'allumer côté
tablette.

Validé de bout en bout pendant le développement : capteur simulé → pont TCP
→ tablette (cible correctement identifiée), et une image PNG de test → pont
TCP → digitalisation → tablette (pic retrouvé au bon endroit).
