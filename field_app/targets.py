"""Configuration statique des 18 postes de tir surveilles.

Chaque poste (boite de controle) a une adresse IP fixe sur le reseau local,
192.168.0.41 a 192.168.0.58. L'identification d'un envoi se fait par l'IP
source de la requete HTTP recue (voir server.py), pas par une auto-
declaration du Raspberry Pi : une IP mal configuree cote RPi ne peut donc
pas usurper l'identite d'un autre poste.
"""
from __future__ import annotations

FIRST_OCTET = 41  # 192.168.0.41 ... 192.168.0.58
N_TARGETS = 18

TARGETS = [
    {"id": i, "ip": f"192.168.0.{FIRST_OCTET + i - 1}", "label": f"Cible {i}"}
    for i in range(1, N_TARGETS + 1)
]

TARGETS_BY_IP = {t["ip"]: t for t in TARGETS}
TARGETS_BY_ID = {t["id"]: t for t in TARGETS}


def identify_target(ip: str | None) -> dict | None:
    if not ip:
        return None
    return TARGETS_BY_IP.get(ip)
