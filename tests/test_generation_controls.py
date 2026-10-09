import threading

import numpy as np
from fastapi.testclient import TestClient

from omnivoice_realtime.app import create_app
from omnivoice_realtime.engine import MockOmniVoiceEngine, OmniVoiceEngine, _CachedVoice
from omnivoice_realtime.schemas import TTSRequest, VoiceMode


def test_schema_accepts_omnivoice_021_generation_controls():
    request = TTSRequest(
        text="ChatGPT cuesta $25 el 17 de julio.",
        normalize_text=True,
        pronunciation_profile="es-latam-tech",
        t_shift=0.12,
        position_temperature=4.0,
        class_temperature=0.1,
        layer_penalty_factor=4.5,
        pad_duration=0.05,
        fade_duration=0.05,
        audio_chunk_duration=12.0,
        audio_chunk_threshold=24.0,
    )

    assert request.normalize_text is True
    assert request.pronunciation_profile == "es-latam-tech"
    assert request.pad_duration == 0.05
    assert request.audio_chunk_threshold == 24.0


def test_clone_generation_forwards_instruct_and_021_controls():
    class FakeModel:
        def __init__(self):
            self.kwargs = None

        def generate(self, **kwargs):
            self.kwargs = kwargs
            return [np.zeros(240, dtype=np.float32)]

    model = FakeModel()
    engine = OmniVoiceEngine.__new__(OmniVoiceEngine)
    engine._model = model
    engine.sample_rate = 24000
    engine._lock = threading.Lock()
    engine._voices = {
        "yamill": _CachedVoice("yamill", "ref.wav", "Hola", prompt={"voice": "yamill"})
    }

    engine.generate(
        TTSRequest(
            text="Usa ChatGPT por $25.",
            voice_mode=VoiceMode.CLONE,
            voice_id="yamill",
            instruct="female, young adult, moderate pitch",
            normalize_text=True,
            pronunciation_profile="es-latam-tech",
            custom_pronunciations={"$25": "veinticinco dólares"},
            speed=1.14,
            t_shift=0.12,
            position_temperature=4.0,
            class_temperature=0.1,
            layer_penalty_factor=4.5,
            pad_duration=0.05,
            fade_duration=0.05,
            audio_chunk_duration=12.0,
            audio_chunk_threshold=24.0,
        )
    )

    assert model.kwargs["text"] == "Usa Chat, ge pe te por veinticinco dólares."
    assert model.kwargs["instruct"] == "female, young adult, moderate pitch"
    assert model.kwargs["voice_clone_prompt"] == {"voice": "yamill"}
    assert model.kwargs["normalize_text"] is True
    assert model.kwargs["speed"] == 1.14
    assert model.kwargs["t_shift"] == 0.12
    assert model.kwargs["position_temperature"] == 4.0
    assert model.kwargs["class_temperature"] == 0.1
    assert model.kwargs["layer_penalty_factor"] == 4.5
    assert model.kwargs["pad_duration"] == 0.05
    assert model.kwargs["fade_duration"] == 0.05
    assert model.kwargs["audio_chunk_duration"] == 12.0
    assert model.kwargs["audio_chunk_threshold"] == 24.0


def test_prepare_text_endpoint_applies_latam_technology_pronunciations():
    client = TestClient(create_app(engine=MockOmniVoiceEngine()))

    response = client.post(
        "/v1/text/prepare",
        json={
            "text": "Crea con ChatGPT, IA, YOO Media, ElevenLabs y HeyGen.",
            "pronunciation_profile": "es-latam-tech",
        },
    )

    assert response.status_code == 200
    assert response.json()["prepared_text"] == (
        "Crea con Chat, ge pe te, inteligencia artificial, Yú Media, Eleven Labs y Hey Gen."
    )
    assert response.json()["replacements"] == 5
