from fastapi.testclient import TestClient

from omnivoice_realtime.app import create_app
from omnivoice_realtime.engine import MockOmniVoiceEngine


def test_clone_cache_rejects_path_traversal_voice_id():
    app = create_app(engine=MockOmniVoiceEngine())
    client = TestClient(app)

    response = client.post(
        "/v1/voices/clone-cache",
        data={"voice_id": "../../evil", "ref_text": "Hola"},
        files={"ref_audio": ("ref.wav", b"fake wav", "audio/wav")},
    )

    assert response.status_code == 400
    assert "voice_id" in response.json()["detail"]


def test_clone_cache_rejects_oversized_upload():
    app = create_app(engine=MockOmniVoiceEngine())
    app.state.max_upload_bytes = 4
    client = TestClient(app)

    response = client.post(
        "/v1/voices/clone-cache",
        data={"voice_id": "sample", "ref_text": "Hola"},
        files={"ref_audio": ("ref.wav", b"too large", "audio/wav")},
    )

    assert response.status_code == 413


def test_websocket_reports_bad_clone_voice_without_disconnect():
    app = create_app(engine=MockOmniVoiceEngine())
    client = TestClient(app)

    with client.websocket_connect("/v1/tts/stream") as ws:
        ws.send_json({"type": "start", "voice_mode": "clone", "voice_id": "missing"})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "text", "text": "Hola."})
        error = ws.receive_json()
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()

    assert error["type"] == "error"
    assert error["detail"] == "Request could not be completed"
    assert pong["type"] == "pong"
