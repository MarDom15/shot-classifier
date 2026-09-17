"""Configuration partagee du projet."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw" / "200924_Brocksettel.zip"
DATA_WAVEFORMS = ROOT / "data" / "processed" / "brocksettel_waveforms_raw.csv"
DATA_FEATURES = ROOT / "data" / "processed" / "brocksettel_features_enriched.csv"
MODELS_DIR = ROOT / "models_store"
REPORTS_DIR = ROOT / "docs" / "reports"

RANDOM_SEED = 42

# Le split train/test se fait par session d'enregistrement, jamais au hasard :
# les deux sessions ont pu avoir des conditions (gain, montage) legerement
# differentes, et un split aleatoire donnerait un score de validation
# artificiellement optimiste (fuite d'information entre train et test).
GROUP_COL = "session"
TEST_SESSION = "19090822"  # session utilisee comme jeu de test (la plus recente)
