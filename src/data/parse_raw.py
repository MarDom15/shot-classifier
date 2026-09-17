"""Parse les fichiers texte bruts (formes d'onde ADC 8 bits, 512 échantillons)
de l'archive "Brocksettel" en un DataFrame tabulaire.

Peut être exécuté directement :
    python -m src.data.parse_raw --zip data/raw/200924_Brocksettel.zip \
        --out data/processed/brocksettel_waveforms_raw.csv

Gère deux anomalies connues du format d'origine :
  * certains fichiers contiennent plusieurs événements "Triggered:" concaténés
    sans saut de ligne (double-déclenchement du capteur) -> chaque événement
    devient une ligne distincte ;
  * la longueur nominale d'un événement est 512 échantillons ; tout écart est
    signalé et corrigé (tronqué / complété) plutôt que de faire échouer le
    chargement.
"""
from __future__ import annotations

import argparse
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

N_SAMPLES = 512
FOLDER_RE = re.compile(r"^(?P<idx>\d{2})(?P<weapon>G36|P8|MP7|Steine)(?P<mode>H|K)?(?P<dist>\d+)?m?(?P<variant>D)?$")


@dataclass
class ParseResult:
    df: pd.DataFrame
    anomalies: list[str] = field(default_factory=list)


def _iter_zip_text_members(zf: zipfile.ZipFile):
    for info in zf.infolist():
        if info.is_dir():
            continue
        if "__MACOSX" in info.filename:
            continue
        if not info.filename.endswith(".txt"):
            continue
        yield info


def parse_zips(zip_paths: list[str | Path]) -> ParseResult:
    """Parse plusieurs archives (session initiale + nouvelles sessions deposees
    dans data/raw/incoming/, voir src/agent/ml_agent.py) et concatene le resultat.
    """
    all_df = []
    all_anomalies: list[str] = []
    for zp in zip_paths:
        result = parse_zip(zp)
        if len(result.df):
            all_df.append(result.df)
        all_anomalies.extend(f"[{Path(zp).name}] {a}" for a in result.anomalies)

    combined = pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()
    if len(combined):
        before = len(combined)
        combined = combined.drop_duplicates(subset=["session", "folder", "file", "event_index_in_file"])
        if len(combined) != before:
            all_anomalies.append(f"{before - len(combined)} doublon(s) retire(s) entre archives")
    return ParseResult(df=combined, anomalies=all_anomalies)


def parse_zip(zip_path: str | Path) -> ParseResult:
    zip_path = Path(zip_path)
    rows: list[dict] = []
    anomalies: list[str] = []

    with zipfile.ZipFile(zip_path) as zf:
        members = list(_iter_zip_text_members(zf))
        for info in members:
            parts = Path(info.filename).parts
            # .../<root>/<session>/<folder>/<file>.txt
            if len(parts) < 3:
                anomalies.append(f"Chemin inattendu: {info.filename}")
                continue
            fname = parts[-1]
            folder = parts[-2]
            session = parts[-3]

            m = FOLDER_RE.match(folder)
            if not m:
                anomalies.append(f"Dossier non reconnu: {session}/{folder}")
                continue
            weapon = m.group("weapon")
            mode = m.group("mode") or ""
            dist = m.group("dist")
            variant = bool(m.group("variant"))

            content = zf.read(info).decode("utf-8", errors="replace")
            if "Triggered:" not in content:
                anomalies.append(f"En-tete inattendu: {info.filename}")
                continue

            prefix_m = re.match(r"^([A-Za-z]+)", fname)
            prefix = prefix_m.group(1) if prefix_m else "?"

            segments = [seg.strip() for seg in content.split("Triggered:") if seg.strip()]
            n_events = len(segments)
            for evt_idx, seg in enumerate(segments):
                tokens = seg.split()
                try:
                    values = [int(t, 16) for t in tokens]
                except ValueError as e:
                    anomalies.append(f"Valeur hex invalide dans {info.filename} (evt {evt_idx}): {e}")
                    continue
                n = len(values)
                extra_flag = n != N_SAMPLES
                if n > N_SAMPLES:
                    values = values[:N_SAMPLES]
                elif n < N_SAMPLES:
                    anomalies.append(f"Longueur insuffisante ({n}) dans {info.filename} (evt {evt_idx})")
                    values = values + [None] * (N_SAMPLES - n)

                row = {
                    "session": session,
                    "folder": folder,
                    "weapon": weapon,
                    "mode": mode,
                    "distance_m": int(dist) if dist else None,
                    "variant_D": variant,
                    "file": fname,
                    "label_prefix": prefix,
                    "event_index_in_file": evt_idx,
                    "n_events_in_file": n_events,
                    "n_samples_raw": n,
                    "extra_sample_flag": extra_flag,
                    "filepath": info.filename,
                }
                for i, v in enumerate(values):
                    row[f"s{i:03d}"] = v
                rows.append(row)

    df = pd.DataFrame(rows)
    return ParseResult(df=df, anomalies=anomalies)


def sample_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if len(c) == 4 and c[0] == "s" and c[1:].isdigit()]


def meta_columns(df: pd.DataFrame) -> list[str]:
    sc = set(sample_columns(df))
    return [c for c in df.columns if c not in sc]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", action="append", default=None,
                     help="Archive a parser (repetable). Par defaut : data/raw/200924_Brocksettel.zip "
                          "+ toute archive presente dans data/raw/incoming/.")
    ap.add_argument("--out", default="data/processed/brocksettel_waveforms_raw.csv")
    args = ap.parse_args()

    if args.zip:
        zip_paths = args.zip
    else:
        zip_paths = ["data/raw/200924_Brocksettel.zip"]
        incoming = Path("data/raw/incoming")
        if incoming.exists():
            zip_paths += sorted(str(p) for p in incoming.glob("*.zip"))

    result = parse_zips(zip_paths)
    print(f"{len(result.df)} evenements parses depuis {len(zip_paths)} archive(s): {', '.join(zip_paths)}")
    if result.anomalies:
        print(f"{len(result.anomalies)} anomalie(s):")
        for a in result.anomalies:
            print(" -", a)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.df.to_csv(args.out, index=False)
    print(f"Ecrit: {args.out}")


if __name__ == "__main__":
    main()
