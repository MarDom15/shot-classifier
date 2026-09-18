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

### IP fixe de ce Raspberry Pi : `192.168.0.255`

C'est l'adresse que les boîtiers de contrôle (technicien) doivent viser
pour se connecter à ce pont. À fixer **sur le système du RPi lui-même**
(pas dans la config Python) :

```bash
sudo nano /etc/dhcpcd.conf
```

Ajouter à la fin (adapter `eth0` en `wlan0` si le RPi est en wifi, et
`192.168.0.1` si la passerelle/routeur a une autre adresse) :

```
interface eth0
static ip_address=192.168.0.255/24
static routers=192.168.0.1
```

Puis `sudo reboot`. Vérifier ensuite avec `ip addr show eth0`.

> **Note technique, pour mémoire** : sur un réseau `192.168.0.0/24`
> standard (masque `/24`, le plus courant), `.255` est réservée comme
> adresse de diffusion (broadcast) et n'est normalement pas assignable à
> un appareil — si le pont ne reçoit rien malgré une configuration
> correcte des boîtiers, c'est le premier point à vérifier avec la
> personne qui gère le réseau (masque de sous-réseau réellement utilisé).

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
  "listen_port": 9090,
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

Confirmé avec le technicien : TCP, port **9090**, une connexion transporte
**plusieurs messages** à la suite (pas une reconnexion par forme d'onde).
Comme les messages sont de taille variable (512 octets bruts, ou une image
de taille quelconque), chacun est précédé d'un **en-tête de 4 octets**
(entier non signé, big-endian) indiquant sa longueur — convention la plus
simple pour ce cas, à ajuster dans `_read_frame()` si le système réel utilise
un autre découpage (délimiteur, taille fixe...).

Reste une hypothèse par défaut : **identification du capteur par IP source**
de la connexion entrante (table `ip_to_target`) — cohérent avec le fait que
chaque capteur a sa propre IP fixe (boîtier de contrôle dédié). Si le
système distingue plutôt les capteurs autrement (port, identifiant dans le
message...), adapter `identify_sensor()`.

### Tester sans matériel

```bash
python tcp_bridge.py --simulate-sensor 127.0.0.1 --interval 2
```

Dans un autre terminal, lancer `python tcp_bridge.py` (sans arguments) pour
qu'il écoute — le capteur simulé ouvre **une seule connexion** et y envoie
des formes d'onde encadrées en continu, comme prévu pour le système réel.
Ajouter l'IP utilisée (`127.0.0.1` pour un test local) à `ip_to_target` dans
la configuration pour voir la bonne cible s'allumer côté tablette.

**⚠️ Si vous testez tout sur une seule machine** (avec la stack Docker
principale qui tourne aussi, voir README racine) : le port 9090 par défaut
entre en conflit avec Prometheus, qui l'utilise déjà sur cette même machine
— ce n'est pas un problème sur le vrai déploiement (le RPi et la machine qui
fait tourner Prometheus sont deux appareils différents), mais changez
temporairement `listen_port` pour un test local complet sur un seul PC.

Validé de bout en bout pendant le développement : plusieurs formes d'onde
envoyées sur la **même connexion** → pont TCP → tablette (toutes reçues,
correctement décodées, bonne cible identifiée), avec un mélange de
messages bruts et d'une image PNG de test (pic retrouvé au bon endroit
après digitalisation).
