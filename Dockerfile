# Image legere pour l'app Streamlit de demo + les scripts d'entrainement.
# Construite pour tourner en local (gratuit) : aucune dependance a un
# service cloud payant.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependances systeme minimales (lightgbm/xgboost ont besoin de libgomp)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Torch CPU-only : evite de telecharger les paquets CUDA (plusieurs Go inutiles
# sur une machine sans GPU dedie a l'entrainement).
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2" \
    && pip install -r requirements.txt

COPY src/ src/
COPY app/ app/
COPY data/raw/ data/raw/
COPY data/processed/ data/processed/
COPY models_store/ models_store/
COPY docs/reports/ docs/reports/

RUN mkdir -p monitoring data/raw/incoming models_store_history

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
