# -*- mode: python ; coding: utf-8 -*-
# Empaquetage de l'app terrain en executable Windows autonome (dossier +
# .exe, pas de Python/Docker requis sur la tablette).
#
# Construction :
#   cd field_app\build
#   pyinstaller field_app.spec --noconfirm
#
# Resultat : field_app/build/dist/ShotClassifierTerrain/ShotClassifierTerrain.exe
# -> copier tout le dossier ShotClassifierTerrain/ sur la tablette.

from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None
ROOT = Path(SPECPATH).resolve().parent.parent  # racine du depot shot-classifier
FIELD_APP = ROOT / "field_app"

datas = [
    (str(FIELD_APP / "static"), "static"),
    (str(ROOT / "models_store"), "models_store"),
]
binaries = []
hiddenimports = []

# torch, sklearn, xgboost, lightgbm embarquent des binaires natifs et des
# imports dynamiques que l'analyse statique de PyInstaller rate souvent :
# on les laisse collecter tout ce dont ils ont besoin explicitement.
for pkg in ("torch", "sklearn", "xgboost", "lightgbm", "uvicorn"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [str(FIELD_APP / "server.py")],
    pathex=[str(FIELD_APP), str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["evidently", "streamlit", "matplotlib.tests"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ShotClassifierTerrain",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="ShotClassifierTerrain",
)
