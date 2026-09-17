import pandas as pd

from src.utils.labels import STAGE1_COL, add_labels, shots_only


def test_add_labels_binary_encoding():
    df = pd.DataFrame({"weapon": ["G36", "P8", "Steine", "MP7"]})
    out = add_labels(df)
    assert out[STAGE1_COL].tolist() == [1, 1, 0, 1]


def test_shots_only_excludes_steine():
    df = pd.DataFrame({"weapon": ["G36", "Steine", "P8"]})
    out = shots_only(df)
    assert "Steine" not in out["weapon"].values
    assert len(out) == 2
