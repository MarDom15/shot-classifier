"""Convertit les captures de l'app terrain (field_app/) verifiees par un
operateur en une archive .zip compatible avec le format attendu par
src/data/parse_raw.py, deposee dans data/raw/incoming/ pour etre reprise
automatiquement par l'agent (src/agent/ml_agent.py) au prochain cycle —
aucune modification de parse_raw.py necessaire.

Seules les captures avec une confirmation operateur
(field_app/data/confirmations.jsonl) sont exportees : une prediction seule
n'est pas une verite terrain (voir field_app/README.md). Les captures dont
l'arme reelle a ete indiquee comme "inconnue/autre" sont egalement ignorees
(aucune des trois classes G36/MP7/P8 ne peut leur etre attribuee).

L'archive est regeneree entierement a chaque appel (noms de fichiers
deterministes, derives de l'id de chaque capture) : relancer ce script
plusieurs fois sur les memes confirmations produit le meme resultat, sans
duplication au fil des cycles de l'agent.

Usage :
    python -m src.data.import_field_captures
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

SESSION_NAME = "field"
VALID_WEAPONS = {"G36", "MP7", "P8"}
DEFAULT_FIELD_DATA_DIR = Path("field_app") / "data"
DEFAULT_OUT_ZIP = Path("data") / "raw" / "incoming" / "field_export.zip"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _latest_confirmations(path: Path) -> dict[str, dict]:
    """Une capture peut etre corrigee plusieurs fois ; la derniere l'emporte."""
    latest: dict[str, dict] = {}
    for rec in _load_jsonl(path):
        latest[rec["id"]] = rec["confirmed"]
    return latest


def build_field_archive(field_data_dir: Path, out_zip: Path) -> dict:
    captures = {c["id"]: c for c in _load_jsonl(field_data_dir / "captures.jsonl")}
    confirmations = _latest_confirmations(field_data_dir / "confirmations.jsonl")

    by_weapon: dict[str, list[tuple[str, list[int]]]] = {}
    skipped_unconfirmed = 0
    skipped_ambiguous = 0
    skipped_malformed = 0

    for cap_id, capture in captures.items():
        values = capture.get("values") or []
        if len(values) != 512 or any(not isinstance(v, int) or v < 0 or v > 255 for v in values):
            # Le serveur (field_app/server.py) rejette deja tout envoi non
            # conforme avant qu'il n'atteigne captures.jsonl ; ce garde-fou ne
            # sert qu'a proteger contre un fichier corrompu ou modifie a la
            # main - une capture invalide ne doit jamais atteindre l'entrainement
            # (elle y serait completee par des NaN, rejetes par scikit-learn).
            skipped_malformed += 1
            continue

        confirmed = confirmations.get(cap_id)
        if confirmed is None:
            skipped_unconfirmed += 1
            continue

        if confirmed["is_shot"]:
            weapon = confirmed.get("weapon")
            if weapon not in VALID_WEAPONS:
                skipped_ambiguous += 1
                continue
        else:
            weapon = "Steine"

        by_weapon.setdefault(weapon, []).append((cap_id, values))

    included = sum(len(items) for items in by_weapon.values())

    if included == 0:
        out_zip.unlink(missing_ok=True)
    else:
        out_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, (weapon, items) in enumerate(sorted(by_weapon.items()), start=1):
                folder = f"{idx:02d}{weapon}"
                for cap_id, values in items:
                    hex_line = " ".join(f"{v:02X}" for v in values)
                    zf.writestr(f"{SESSION_NAME}/{folder}/Field_{cap_id[:16]}.txt", f"Triggered:{hex_line}\n")

    return {
        "out_zip": str(out_zip),
        "included": included,
        "skipped_unconfirmed": skipped_unconfirmed,
        "skipped_ambiguous": skipped_ambiguous,
        "skipped_malformed": skipped_malformed,
        "weapons": {w: len(items) for w, items in by_weapon.items()},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field-data", default=str(DEFAULT_FIELD_DATA_DIR),
                     help="Dossier contenant captures.jsonl / confirmations.jsonl")
    ap.add_argument("--out", default=str(DEFAULT_OUT_ZIP))
    args = ap.parse_args()

    stats = build_field_archive(Path(args.field_data), Path(args.out))
    if stats["included"] == 0:
        print("Aucune capture confirmee a exporter (rien a faire).")
    else:
        print(f"Archive ecrite : {stats['out_zip']}")
        print(f"  {stats['included']} capture(s) confirmee(s) exportee(s) {stats['weapons']}")
    print(f"  {stats['skipped_unconfirmed']} capture(s) non confirmee(s) ignoree(s)")
    print(f"  {stats['skipped_ambiguous']} capture(s) confirmee(s) mais arme ambigue ignoree(s)")
    if stats["skipped_malformed"]:
        print(f"  {stats['skipped_malformed']} capture(s) malformee(s) ignoree(s) (longueur/valeurs invalides)")


if __name__ == "__main__":
    main()
