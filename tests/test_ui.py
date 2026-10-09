from fastapi.testclient import TestClient

from omnivoice_realtime.app import create_app
from omnivoice_realtime.engine import MockOmniVoiceEngine


def test_root_redirects_to_studio():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/ui"


def test_studio_ui_is_served_with_core_voice_workflow():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.get("/ui")

    assert response.status_code == 200
    html = response.text
    assert "OmniVoice Studio" in html
    assert "Generar audio" in html
    assert "Clonar una voz" in html
    assert "Pronunciación" in html
    assert "Promo rápida" in html
    assert "prefers-reduced-motion" in html


def test_studio_javascript_is_served():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.get("/ui/app.js")

    assert response.status_code == 200
    assert "fetch('/v1/tts'" in response.text
    assert "audio_base64" in response.text
    assert "await $('#audio').play()" not in response.text
