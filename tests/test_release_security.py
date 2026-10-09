import pytest
from fastapi.testclient import TestClient
from omnivoice_realtime.app import create_app
from omnivoice_realtime.engine import MockOmniVoiceEngine


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_UPLOAD_DIR", str(tmp_path / "uploads"))
    return create_app(engine=MockOmniVoiceEngine())


@pytest.mark.parametrize("path", ["/etc/passwd", "../../private.wav", "https://example.com/ref.wav"])
def test_rest_rejects_caller_local_paths(app, path):
    response = TestClient(app).post("/v1/tts", json={"text": "hello", "ref_audio_path": path})
    assert response.status_code == 400
    assert path not in response.text


def test_batch_rejects_caller_local_paths(app):
    response = TestClient(app).post("/v1/tts/batch", json={"items": [{"text": "hello", "ref_audio_path": "/etc/passwd"}]})
    assert response.status_code == 400


def test_registry_does_not_expose_local_paths(app):
    client = TestClient(app)
    assert client.post("/v1/voices/clone-cache", data={"voice_id": "sample"}, files={"ref_audio": ("ref.wav", b"test", "audio/wav")}).status_code == 200
    for url in ["/v1/voices", "/v1/voices/sample"]:
        response = client.get(url)
        assert "ref_audio_path" not in response.text
        assert str(app.state.upload_dir) not in response.text


def test_registry_rejects_symlink_escape(app, tmp_path):
    outside = tmp_path / "private.wav"
    outside.write_bytes(b"private")
    link = app.state.upload_dir / "escape.wav"
    link.symlink_to(outside)
    app.state.voice_registry.upsert(voice_id="escape", ref_audio_path=link, ref_text="hello")
    client = TestClient(app)
    assert client.post("/v1/voices/escape/warm-cache").status_code == 409
    assert client.post("/v1/tts", json={"text": "hello", "voice_mode": "clone", "voice_id": "escape"}).status_code == 400
    assert not app.state.engine._voices
    assert client.get("/v1/voices/escape").json()["ref_audio_exists"] is False


def test_error_details_are_not_sent_to_rest_or_websocket(app):
    def fail(_):
        raise RuntimeError("PRIVATE_CANARY /home/private/key token-secret")
    app.state.engine.generate = fail
    client = TestClient(app)
    assert "PRIVATE_CANARY" not in client.post("/v1/tts", json={"text": "hello"}).text
    with client.websocket_connect("/v1/tts/stream") as ws:
        ws.send_json({"type": "text", "text": "hello."})
        assert "PRIVATE_CANARY" not in str(ws.receive_json())
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_duplicate_voice_does_not_overwrite_reference(app):
    client = TestClient(app)
    args = {"data": {"voice_id": "sample"}, "files": {"ref_audio": ("ref.wav", b"first", "audio/wav")}}
    assert client.post("/v1/voices/clone-cache", **args).status_code == 200
    record = app.state.voice_registry.get("sample")
    from pathlib import Path
    audio = Path(record["ref_audio_path"])
    args["files"] = {"ref_audio": ("ref.wav", b"second", "audio/wav")}
    assert client.post("/v1/voices/clone-cache", **args).status_code == 409
    assert audio.read_bytes() == b"first"


def test_cross_origin_http_rejected(app):
    response = TestClient(app).post("/v1/tts", headers={"Origin": "https://evil.example"}, json={"text": "hello"})
    assert response.status_code == 403


def test_cross_origin_websocket_rejected(app):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with TestClient(app).websocket_connect("/v1/tts/stream", headers={"Origin": "https://evil.example"}):
            pass


def test_unknown_host_rejected(app):
    assert TestClient(app).get("/health", headers={"Host": "evil.example"}).status_code == 400


def test_empty_registry_env_uses_private_default(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("OMNIVOICE_VOICE_REGISTRY", "")
    app = create_app(engine=MockOmniVoiceEngine())
    assert app.state.voice_registry.path == app.state.upload_dir / "voices.json"


def test_same_origin_browser_allowed(app):
    assert TestClient(app).post("/v1/tts", headers={"Origin": "http://testserver"}, json={"text": "hello"}).status_code == 200
