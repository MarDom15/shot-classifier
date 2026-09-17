"""Construction des cibles (labels) a partir des metadonnees.

Architecture retenue (voir CAHIER_DES_CHARGES.md, section 4) : deux etages
plutot qu'un classifieur unique a 4 classes, pour ne pas noyer la classe
temoin (14 exemples sur 397) dans un probleme multiclasse desequilibre.

    Etage 1 - is_shot   : "Steine" (0) vs arme (1)
    Etage 2 - weapon    : G36 / MP7 / P8 (uniquement sur les tirs)
    Etage 2b - mode     : H / K (uniquement sur les tirs, information auxiliaire)
"""
from __future__ import annotations

import pandas as pd

STAGE1_COL = "is_shot"
STAGE2_COL = "weapon"
STAGE2B_COL = "mode"


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[STAGE1_COL] = (df["weapon"] != "Steine").astype(int)
    return df


def shots_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["weapon"] != "Steine"].copy()
