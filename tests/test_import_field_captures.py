import json

from src.data.import_field_captures import build_field_archive
from src.data.parse_raw import parse_zip, sample_columns


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in records)


def test_only_confirmed_captures_are_exported(tmp_path):
    field_dir = tmp_path / "field_app_data"
    _write_jsonl(field_dir / "captures.jsonl", [
        {"id": "aaa111aaa111aaa1", "values": [130] * 512},
        {"id": "bbb222bbb222bbb2", "values": [10] * 512},
        {"id": "ccc333ccc333ccc3", "values": [50] * 512},  # jamais confirmee
    ])
    _write_jsonl(field_dir / "confirmations.jsonl", [
        {"id": "aaa111aaa111aaa1", "confirmed": {"is_shot": True, "weapon": "G36"}},
        {"id": "bbb222bbb222bbb2", "confirmed": {"is_shot": False, "weapon": None}},
    ])

    out_zip = tmp_path / "incoming" / "field_export.zip"
    stats = build_field_archive(field_dir, out_zip)

    assert stats["included"] == 2
    assert stats["skipped_unconfirmed"] == 1
    assert out_zip.exists()

    result = parse_zip(out_zip)
    assert len(result.df) == 2
    assert set(result.df["weapon"]) == {"G36", "Steine"}
    assert set(result.df["session"]) == {"field"}
    assert (result.df["s000"].isin([130, 10])).all()


def test_ambiguous_weapon_is_skipped(tmp_path):
    field_dir = tmp_path / "field_app_data"
    _write_jsonl(field_dir / "captures.jsonl", [{"id": "x1x1x1x1x1x1x1x1", "values": [100] * 512}])
    _write_jsonl(field_dir / "confirmations.jsonl", [
        {"id": "x1x1x1x1x1x1x1x1", "confirmed": {"is_shot": True, "weapon": "?"}},
    ])

    out_zip = tmp_path / "incoming" / "field_export.zip"
    stats = build_field_archive(field_dir, out_zip)

    assert stats["included"] == 0
    assert stats["skipped_ambiguous"] == 1
    assert not out_zip.exists()


def test_correction_overrides_confirmation(tmp_path):
    """La derniere confirmation d'une capture l'emporte (correction ulterieure)."""
    field_dir = tmp_path / "field_app_data"
    _write_jsonl(field_dir / "captures.jsonl", [{"id": "y1y1y1y1y1y1y1y1", "values": [90] * 512}])
    _write_jsonl(field_dir / "confirmations.jsonl", [
        {"id": "y1y1y1y1y1y1y1y1", "confirmed": {"is_shot": True, "weapon": "MP7"}},
        {"id": "y1y1y1y1y1y1y1y1", "confirmed": {"is_shot": True, "weapon": "P8"}},
    ])

    out_zip = tmp_path / "incoming" / "field_export.zip"
    stats = build_field_archive(field_dir, out_zip)

    result = parse_zip(out_zip)
    assert stats["included"] == 1
    assert result.df.iloc[0]["weapon"] == "P8"


def test_missing_field_data_dir_is_a_noop(tmp_path):
    out_zip = tmp_path / "incoming" / "field_export.zip"
    stats = build_field_archive(tmp_path / "does_not_exist", out_zip)
    assert stats["included"] == 0
    assert not out_zip.exists()


def test_malformed_length_is_skipped_not_padded_with_nan(tmp_path):
    """Regression : une capture corrompue (longueur != 512) ne doit jamais
    atteindre l'archive exportee — parse_zip la completerait avec des NaN,
    rejetes par scikit-learn a l'entrainement (Input X contains NaN)."""
    field_dir = tmp_path / "field_app_data"
    _write_jsonl(field_dir / "captures.jsonl", [
        {"id": "short0000000001", "values": [128] * 460},  # trop court
        {"id": "good0000000001a", "values": [128] * 512},
    ])
    _write_jsonl(field_dir / "confirmations.jsonl", [
        {"id": "short0000000001", "confirmed": {"is_shot": False, "weapon": None}},
        {"id": "good0000000001a", "confirmed": {"is_shot": False, "weapon": None}},
    ])

    out_zip = tmp_path / "incoming" / "field_export.zip"
    stats = build_field_archive(field_dir, out_zip)

    assert stats["included"] == 1
    assert stats["skipped_malformed"] == 1

    result = parse_zip(out_zip)
    assert len(result.df) == 1
    scols = sample_columns(result.df)
    assert not result.df[scols].isna().any().any()
