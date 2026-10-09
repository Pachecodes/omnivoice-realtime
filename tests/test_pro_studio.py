from fastapi.testclient import TestClient

from omnivoice_realtime.app import create_app
from omnivoice_realtime.engine import MockOmniVoiceEngine


def test_existing_studio_links_to_separate_pro_mode_without_being_replaced():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.get("/ui")

    assert response.status_code == 200
    assert "Dirige la voz" in response.text
    assert 'href="/ui/pro"' in response.text


def test_pro_studio_exposes_complete_inference_workbench():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.get("/ui/pro")

    assert response.status_code == 200
    html = response.text
    assert "OmniVoice Pro" in html
    assert "Laboratorio de voz" in html
    assert "Transcripción automática" in html
    assert 'name="ref_text"' in html
    assert 'name="ref_text" rows="4" required' not in html
    assert "Generación individual" in html
    assert "Generación por lote" in html
    assert "Diccionario de pronunciación" in html
    for control in (
        "Duración objetivo",
        "Velocidad",
        "Pasos de inferencia",
        "Guidance scale",
        "T shift",
        "Temperatura de posición",
        "Temperatura de clase",
        "Penalidad por capa",
        "Padding",
        "Fade",
        "Duración de chunk",
        "Umbral de chunk",
        "Preprocesar prompt",
        "Posprocesar audio",
        "Denoise",
        "Normalizar texto",
    ):
        assert control in html


def test_pro_assets_cover_batch_clone_and_full_generation_payload():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.get("/ui/pro/app.js")

    assert response.status_code == 200
    js = response.text
    assert "'/v1/tts/batch'" in js
    assert "fetch('/v1/voices/clone-cache'" in js
    for field in (
        "duration",
        "speed",
        "num_step",
        "guidance_scale",
        "t_shift",
        "position_temperature",
        "class_temperature",
        "layer_penalty_factor",
        "pad_duration",
        "fade_duration",
        "audio_chunk_duration",
        "audio_chunk_threshold",
        "preprocess_prompt",
        "postprocess_output",
        "denoise",
        "normalize_text",
        "custom_pronunciations",
    ):
        assert field in js


def test_custom_pronunciation_dictionary_is_applied_after_profile():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.post(
        "/v1/text/prepare",
        json={
            "text": "ChatGPT trabaja con Akita AI y Demo.",
            "pronunciation_profile": "es-latam-tech",
            "custom_pronunciations": {
                "Akita AI": "Akitá ei ai",
                "Demo": "Démo",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["prepared_text"] == "Chat, ge pe te trabaja con Akitá ei ai y Démo."
    assert response.json()["replacements"] == 3


def test_batch_tts_generates_every_item_without_changing_single_endpoint():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.post(
        "/v1/tts/batch",
        json={
            "items": [
                {"text": "Primera línea.", "format": "wav"},
                {"text": "Segunda línea.", "speed": 1.14, "format": "wav"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert [item["encoding"] for item in data["items"]] == ["wav", "wav"]
    assert all(item["audio_base64"] for item in data["items"])
