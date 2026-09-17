from src.data.parse_raw import parse_zip, sample_columns
from src.utils.config import DATA_RAW


def test_parse_zip_produces_expected_row_count():
    result = parse_zip(DATA_RAW)
    # 397 evenements attendus (voir CAHIER_DES_CHARGES.md, section donnees) :
    # 366 fichiers, dont 31 contiennent deux evenements concatenes, moins un
    # fichier orphelin hors arborescence exclu comme anomalie.
    assert len(result.df) == 397


def test_parse_zip_flags_known_anomaly():
    result = parse_zip(DATA_RAW)
    assert any("19080404" in a for a in result.anomalies)


def test_all_events_have_512_samples():
    result = parse_zip(DATA_RAW)
    scols = sample_columns(result.df)
    assert len(scols) == 512
    assert result.df[scols].isna().sum().sum() == 0


def test_weapon_categories():
    result = parse_zip(DATA_RAW)
    assert set(result.df["weapon"].unique()) == {"G36", "MP7", "P8", "Steine"}
