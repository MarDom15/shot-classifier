"""Extraction de caracteristiques (features) a partir des formes d'onde brutes.

Caracteristiques temporelles (deja utilisees dans l'analyse exploratoire) :
    mean, std, min, max, peak_to_peak, peak_idx, energy, abs_mean_dev, clip_frac

Caracteristiques enrichies ajoutees ici :
    - spectrales (FFT sur la fenetre de 512 points, en cycles/fenetre puisque
      la frequence d'echantillonnage reelle du capteur n'est pas connue) :
      dominant_freq_bin, spectral_centroid, spectral_energy_low/mid/high,
      spectral_flatness, spectral_energy_total
    - forme du signal : zero_crossing_rate, rise_time_idx (delai entre le
      premier depassement de seuil et le pic), skewness, kurtosis

Usage :
    python -m src.data.features --in data/processed/brocksettel_waveforms_raw.csv \
        --out data/processed/brocksettel_features_enriched.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.data.parse_raw import meta_columns, sample_columns

BASELINE = 128.0


def _fft_features(row: np.ndarray) -> dict:
    x = row - BASELINE
    spectrum = np.abs(np.fft.rfft(x))
    spectrum[0] = 0.0  # retire la composante continue
    total_energy = float(np.sum(spectrum ** 2))
    freqs = np.arange(len(spectrum))  # en cycles / fenetre (pas de temps physique connu)

    if total_energy <= 0 or len(spectrum) < 3:
        return {
            "dominant_freq_bin": 0.0,
            "spectral_centroid": 0.0,
            "spectral_energy_low": 0.0,
            "spectral_energy_mid": 0.0,
            "spectral_energy_high": 0.0,
            "spectral_flatness": 0.0,
            "spectral_energy_total": total_energy,
        }

    dominant_bin = float(freqs[np.argmax(spectrum)])
    centroid = float(np.sum(freqs * spectrum) / np.sum(spectrum))

    third = len(spectrum) // 3
    e_low = float(np.sum(spectrum[:third] ** 2))
    e_mid = float(np.sum(spectrum[third:2 * third] ** 2))
    e_high = float(np.sum(spectrum[2 * third:] ** 2))

    # planéité spectrale = moyenne géométrique / moyenne arithmétique (0=tonal, 1=bruit blanc)
    power = spectrum ** 2
    power_nonzero = power[power > 0]
    if len(power_nonzero) > 0:
        geo_mean = np.exp(np.mean(np.log(power_nonzero)))
        arith_mean = np.mean(power_nonzero)
        flatness = float(geo_mean / arith_mean) if arith_mean > 0 else 0.0
    else:
        flatness = 0.0

    return {
        "dominant_freq_bin": dominant_bin,
        "spectral_centroid": centroid,
        "spectral_energy_low": e_low,
        "spectral_energy_mid": e_mid,
        "spectral_energy_high": e_high,
        "spectral_flatness": flatness,
        "spectral_energy_total": total_energy,
    }


def _rise_time(row: np.ndarray, peak_idx: int, threshold_frac: float = 0.5) -> int:
    dev = np.abs(row - BASELINE)
    peak_amp = dev[peak_idx]
    if peak_amp <= 0:
        return 0
    threshold = threshold_frac * peak_amp
    crossed = np.where(dev[: peak_idx + 1] >= threshold)[0]
    first_cross = crossed[0] if len(crossed) else peak_idx
    return int(peak_idx - first_cross)


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    scols = sample_columns(df)
    mcols = [c for c in meta_columns(df) if c not in scols]
    arr = df[scols].to_numpy(dtype=float)

    dev = np.abs(arr - BASELINE)
    peak_idx = np.nanargmax(dev, axis=1)

    records = []
    for i in range(len(df)):
        row = arr[i]
        pidx = int(peak_idx[i])
        std = float(np.nanstd(row))
        # Signal plat (std=0, ex. capteur deconnecte) : asymetrie/aplatissement
        # non definis mathematiquement (0/0) -> scipy renvoie NaN, invalide pour
        # l'entrainement (LogisticRegression etc. rejettent les NaN). 0.0 est la
        # convention pour "pas de forme distinctive" plutot qu'une valeur manquante.
        feat = {
            "mean": float(np.nanmean(row)),
            "std": std,
            "min": float(np.nanmin(row)),
            "max": float(np.nanmax(row)),
            "peak_to_peak": float(np.nanmax(row) - np.nanmin(row)),
            "peak_idx": pidx,
            "peak_amplitude": float(dev[i, pidx]),
            "energy": float(np.nansum((row - BASELINE) ** 2)),
            "abs_mean_dev": float(np.nanmean(np.abs(row - BASELINE))),
            "clip_frac": float(np.mean((row <= 1) | (row >= 254))),
            "zero_crossing_rate": float(np.mean(np.diff(np.sign(row - BASELINE)) != 0)),
            "rise_time_idx": _rise_time(row, pidx),
            "skewness": float(stats.skew(row)) if std > 0 else 0.0,
            "kurtosis": float(stats.kurtosis(row)) if std > 0 else 0.0,
        }
        feat.update(_fft_features(row))
        records.append(feat)

    feat_df = pd.DataFrame(records)
    out = pd.concat([df[mcols].reset_index(drop=True), feat_df.reset_index(drop=True)], axis=1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", default="data/processed/brocksettel_waveforms_raw.csv")
    ap.add_argument("--out", default="data/processed/brocksettel_features_enriched.csv")
    args = ap.parse_args()

    df = pd.read_csv(args.inp)
    out = compute_features(df)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"{len(out)} lignes, {len(out.columns)} colonnes -> {args.out}")


if __name__ == "__main__":
    main()
