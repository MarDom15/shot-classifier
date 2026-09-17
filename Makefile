.PHONY: install parse features import-field-data train train-classical train-cnn compare app field-app docker-build docker-up test lint drift

install:
	pip install -r requirements-dev.txt

parse:
	python -m src.data.parse_raw

import-field-data:
	python -m src.data.import_field_captures

features:
	python -m src.data.features

train-classical:
	python -m src.training.train_classical

train-cnn:
	python -m src.training.train_cnn

train: train-classical train-cnn compare

compare:
	python -m src.training.compare_models

drift:
	python -m src.monitoring.drift

app:
	streamlit run app/streamlit_app.py

docker-build:
	docker compose build

docker-up:
	docker compose up

test:
	pytest -q

lint:
	ruff check src app tests field_app rpi_sender

field-app:
	python field_app/server.py
