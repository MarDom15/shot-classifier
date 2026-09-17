from src.agent import ml_agent
from src.utils.config import DATA_RAW


def test_discover_source_zips_includes_main_archive():
    zips = ml_agent.discover_source_zips()
    assert DATA_RAW in zips


def test_discover_source_zips_picks_up_incoming(tmp_path, monkeypatch):
    fake_incoming = tmp_path / "incoming"
    fake_incoming.mkdir()
    (fake_incoming / "nouvelle_session.zip").write_bytes(b"fake")
    monkeypatch.setattr(ml_agent, "INCOMING_DIR", fake_incoming)
    zips = ml_agent.discover_source_zips()
    assert any(z.name == "nouvelle_session.zip" for z in zips)


def test_snapshot_and_rollback_roundtrip(tmp_path, monkeypatch):
    fake_models = tmp_path / "models_store"
    fake_models.mkdir()
    (fake_models / "dummy.txt").write_text("v1")
    fake_history = tmp_path / "history"

    monkeypatch.setattr(ml_agent, "MODELS_DIR", fake_models)
    monkeypatch.setattr(ml_agent, "HISTORY_DIR", fake_history)

    snap = ml_agent.snapshot_models("test_tag")
    assert snap is not None and snap.exists()
    assert (snap / "dummy.txt").read_text() == "v1"

    # simuler un entrainement qui degrade le modele
    (fake_models / "dummy.txt").write_text("v2 (pire)")
    ml_agent.rollback_models(snap)
    assert (fake_models / "dummy.txt").read_text() == "v1"


def test_snapshot_returns_none_when_no_existing_models(tmp_path, monkeypatch):
    empty_models = tmp_path / "empty_models_store"
    empty_models.mkdir()
    monkeypatch.setattr(ml_agent, "MODELS_DIR", empty_models)
    monkeypatch.setattr(ml_agent, "HISTORY_DIR", tmp_path / "history")
    assert ml_agent.snapshot_models("tag") is None


def test_run_once_end_to_end_smoke():
    """Verifie qu'un cycle complet s'execute sans erreur et journalise un resultat.
    Recharge et ecrase les modeles courants : acceptable dans ce depot de taille
    modeste (~10s), mais a isoler dans un job dedie si le jeu de donnees grossit."""
    entry = ml_agent.run_once()
    assert entry["status"] == "success"
    assert entry["dataset"]["n_events"] >= 397
    assert "stage1_is_shot" in entry["training"]["new_best_f1"]
    assert ml_agent.AGENT_LOG_PATH.exists()
