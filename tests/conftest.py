import pytest


@pytest.fixture(autouse=True)
def isolated_voice_storage(tmp_path, monkeypatch):
    """Tests must never read or mutate an operator's private voice registry."""
    monkeypatch.setenv("OMNIVOICE_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.delenv("OMNIVOICE_VOICE_REGISTRY", raising=False)
    monkeypatch.setenv("OMNIVOICE_ALLOWED_HOSTS", "testserver,127.0.0.1,localhost")
