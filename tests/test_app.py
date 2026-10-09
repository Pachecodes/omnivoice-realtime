from fastapi.testclient import TestClient

from omnivoice_realtime.app import create_app
from omnivoice_realtime.engine import MockOmniVoiceEngine


def test_health_reports_ready_with_mock_engine():
    app = create_app(engine=MockOmniVoiceEngine())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["engine"] == "mock"


def test_rest_tts_returns_audio_packet():
    app = create_app(engine=MockOmniVoiceEngine())
    client = TestClient(app)

    response = client.post("/v1/tts", json={"text": "Hola mundo.", "format": "pcm16"})

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "audio"
    assert body["encoding"] == "pcm16"
    assert body["audio_base64"]
    assert body["metrics"]["audio_seconds"] > 0


def test_voice_clone_upload_creates_cache_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_UPLOAD_DIR", str(tmp_path))
    app = create_app(engine=MockOmniVoiceEngine())
    client = TestClient(app)

    response = client.post(
        "/v1/voices/clone-cache",
        data={
            "voice_id": "sample",
            "ref_text": "Hola mundo",
            "label": "Sample test voice",
            "language": "Spanish",
            "notes": "unit test",
        },
        files={"ref_audio": ("ref.wav", b"fake wav", "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json()["voice_id"] == "sample"
    assert response.json()["cache_hit"] is False
    assert response.json()["registered"] is True

    list_response = client.get("/v1/voices")
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["count"] == 1
    assert body["voices"][0]["voice_id"] == "sample"
    assert body["voices"][0]["cached"] is True
    assert body["voices"][0]["ref_audio_exists"] is True
    assert body["voices"][0]["label"] == "Sample test voice"



def test_voice_clone_upload_auto_transcribes_when_text_is_omitted(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.post(
        "/v1/voices/clone-cache",
        data={"voice_id": "auto_transcribed", "language": "Spanish"},
        files={"ref_audio": ("ref.wav", b"fake wav", "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json()["ref_text"] == "Transcripción automática de prueba."
    voice = client.get("/v1/voices/auto_transcribed").json()
    assert voice["ref_text"] == "Transcripción automática de prueba."



def test_registered_voice_can_warm_new_engine_after_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_UPLOAD_DIR", str(tmp_path))
    first_app = create_app(engine=MockOmniVoiceEngine())
    first_client = TestClient(first_app)
    response = first_client.post(
        "/v1/voices/clone-cache",
        data={"voice_id": "restart_voice", "ref_text": "Restart test"},
        files={"ref_audio": ("ref.wav", b"fake wav", "audio/wav")},
    )
    assert response.status_code == 200

    second_app = create_app(engine=MockOmniVoiceEngine())
    second_client = TestClient(second_app)
    detail_before = second_client.get("/v1/voices/restart_voice")
    assert detail_before.status_code == 200
    assert detail_before.json()["cached"] is False
    assert detail_before.json()["ref_audio_exists"] is True

    warm_response = second_client.post("/v1/voices/restart_voice/warm-cache")
    assert warm_response.status_code == 200
    assert warm_response.json()["registered"] is True

    tts_response = second_client.post(
        "/v1/tts",
        json={"text": "Hello", "voice_mode": "clone", "voice_id": "restart_voice", "format": "pcm16"},
    )
    assert tts_response.status_code == 200
    assert tts_response.json()["voice_id"] == "restart_voice"



def test_tts_auto_warms_registered_voice(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_UPLOAD_DIR", str(tmp_path))
    first_client = TestClient(create_app(engine=MockOmniVoiceEngine()))
    response = first_client.post(
        "/v1/voices/clone-cache",
        data={"voice_id": "auto_warm_voice", "ref_text": "Auto warm test"},
        files={"ref_audio": ("ref.wav", b"fake wav", "audio/wav")},
    )
    assert response.status_code == 200

    second_client = TestClient(create_app(engine=MockOmniVoiceEngine()))
    tts_response = second_client.post(
        "/v1/tts",
        json={"text": "Hello", "voice_mode": "clone", "voice_id": "auto_warm_voice", "format": "pcm16"},
    )
    assert tts_response.status_code == 200
    assert tts_response.json()["voice_id"] == "auto_warm_voice"



def test_websocket_streams_audio_after_flush():
    app = create_app(engine=MockOmniVoiceEngine())
    client = TestClient(app)

    with client.websocket_connect("/v1/tts/stream") as ws:
        ws.send_json({"type": "start", "format": "pcm16", "num_step": 16})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "text", "text": "Hola mundo"})
        ws.send_json({"type": "flush"})
        audio = ws.receive_json()
        done = ws.receive_json()

    assert audio["type"] == "audio"
    assert audio["seq"] == 1
    assert audio["audio_base64"]
    assert done["type"] == "done"
