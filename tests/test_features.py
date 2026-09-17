import pandas as pd

from src.data.features import BASELINE, compute_features


def _make_row(values):
    row = {f"s{i:03d}": v for i, v in enumerate(values)}
    row.update({"session": "s", "folder": "f", "weapon": "G36", "mode": "H",
                "distance_m": 10, "variant_D": False, "file": "x.txt",
                "label_prefix": "T", "event_index_in_file": 0, "n_events_in_file": 1,
                "n_samples_raw": len(values), "extra_sample_flag": False, "filepath": "x"})
    return pd.DataFrame([row])


def test_flat_signal_has_zero_energy_and_no_peak():
    flat = [int(BASELINE)] * 512
    df = _make_row(flat)
    feat = compute_features(df)
    assert feat.loc[0, "energy"] == 0
    assert feat.loc[0, "peak_amplitude"] == 0


def test_single_spike_detected_at_correct_index():
    values = [int(BASELINE)] * 512
    values[100] = 255
    df = _make_row(values)
    feat = compute_features(df)
    assert feat.loc[0, "peak_idx"] == 100
    assert feat.loc[0, "clip_frac"] > 0


def test_feature_columns_present():
    df = _make_row([int(BASELINE)] * 512)
    feat = compute_features(df)
    expected = {"energy", "peak_idx", "spectral_centroid", "dominant_freq_bin",
                "zero_crossing_rate", "skewness", "kurtosis", "clip_frac"}
    assert expected.issubset(set(feat.columns))
