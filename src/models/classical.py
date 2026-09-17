"""Registre des modeles classiques compares dans ce projet.

Chaque entree renvoie un pipeline scikit-learn complet (standardisation +
estimateur) afin que tous les modeles soient utilisables de facon uniforme,
y compris ceux sensibles a l'echelle des variables (SVM, kNN, regression
logistique).
"""
from __future__ import annotations

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from src.utils.config import RANDOM_SEED

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


def build_registry(n_classes: int) -> dict[str, Pipeline]:
    """n_classes sert uniquement a configurer XGBoost (objectif binaire/multiclasse)."""
    registry: dict[str, Pipeline] = {
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, random_state=RANDOM_SEED)),
        ]),
        "knn": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", KNeighborsClassifier(n_neighbors=5)),
        ]),
        "svm_rbf": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="rbf", probability=True, random_state=RANDOM_SEED)),
        ]),
        "decision_tree": Pipeline([
            ("clf", DecisionTreeClassifier(max_depth=6, random_state=RANDOM_SEED)),
        ]),
        "random_forest": Pipeline([
            ("clf", RandomForestClassifier(
                n_estimators=300, max_depth=None, random_state=RANDOM_SEED, class_weight="balanced"
            )),
        ]),
        "gradient_boosting": Pipeline([
            ("clf", GradientBoostingClassifier(random_state=RANDOM_SEED)),
        ]),
    }

    if HAS_XGBOOST:
        objective = "binary:logistic" if n_classes == 2 else "multi:softprob"
        registry["xgboost"] = Pipeline([
            ("clf", XGBClassifier(
                n_estimators=300,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                objective=objective,
                eval_metric="logloss",
                random_state=RANDOM_SEED,
            )),
        ])

    if HAS_LIGHTGBM:
        registry["lightgbm"] = Pipeline([
            ("clf", LGBMClassifier(
                n_estimators=300, max_depth=-1, learning_rate=0.05,
                random_state=RANDOM_SEED, verbose=-1,
            )),
        ])

    return registry
