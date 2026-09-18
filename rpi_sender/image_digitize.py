"""Digitalisation approximative d'une image de signal en 512 valeurs 0-255.

Portage Python de la meme methode que field_app/static/app.js
(digitizeImageData), pour le cas ou le systeme du technicien envoie parfois
une image plutot que des echantillons bruts (voir tcp_bridge.py). Detecte
la couleur de fond a partir des coins de l'image, puis pour chaque colonne
moyenne la position verticale des pixels qui en different (la trace).

Calibration sur la HAUTEUR TOTALE de l'image (bas=0, haut=255 par defaut),
PAS sur l'etendue verticale observee de la trace : normaliser sur la trace
ecraserait une ligne de base plate avec un pic isole vers 0 (verifie
empiriquement lors du developpement de la fonctionnalite equivalente cote
UI — erreur moyenne ~120/255 avec l'etendue de la trace, ~0 avec la
hauteur totale de l'image, sur un signal de test connu).

C'est une estimation, pas une lecture exacte — fiable sur une image nette
a fond uni, pas garanti sur une photo (angle, eclairage).
"""
from __future__ import annotations

import io

N_SAMPLES = 512
THRESHOLD = 45

# Signatures binaires usuelles pour detecter qu'un paquet est une image
# plutot que des echantillons bruts (voir tcp_bridge.py: looks_like_image).
_IMAGE_SIGNATURES = (
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"\xff\xd8\xff",        # JPEG
    b"BM",                  # BMP
    b"GIF87a",
    b"GIF89a",
)


def looks_like_image(data: bytes) -> bool:
    return any(data.startswith(sig) for sig in _IMAGE_SIGNATURES)


def digitize_image(image_bytes: bytes, bottom_value: int = 0, top_value: int = 255) -> list[int] | None:
    """Renvoie 512 valeurs 0-255, ou None si aucune trace n'a pu etre detectee."""
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(
            "Pillow est requis pour digitaliser une image (pip install -r "
            "rpi_sender/requirements-tcp-bridge.txt)."
        ) from e

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = img.size
    pixels = img.load()

    corners = [pixels[0, 0], pixels[width - 1, 0], pixels[0, height - 1], pixels[width - 1, height - 1]]
    bg = tuple(sum(c[i] for c in corners) / 4 for i in range(3))

    def dist(p) -> float:
        return sum((p[i] - bg[i]) ** 2 for i in range(3)) ** 0.5

    rows: list[float | None] = [None] * width
    for x in range(width):
        total, count = 0.0, 0
        for y in range(height):
            if dist(pixels[x, y]) > THRESHOLD:
                total += y
                count += 1
        if count:
            rows[x] = total / count

    last = next((r for r in rows if r is not None), None)
    if last is None:
        return None
    for x in range(width):
        if rows[x] is None:
            rows[x] = last
        else:
            last = rows[x]

    resampled = []
    for i in range(N_SAMPLES):
        src_x = min(width - 1, int((i / (N_SAMPLES - 1)) * (width - 1)))
        resampled.append(rows[src_x])

    values = []
    for r in resampled:
        frac = 1 - r / max(1, height - 1)
        v = bottom_value + frac * (top_value - bottom_value)
        values.append(max(0, min(255, round(v))))
    return values
