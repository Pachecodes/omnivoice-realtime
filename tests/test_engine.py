import threading
from types import SimpleNamespace

import numpy as np

from omnivoice_realtime.engine import MockOmniVoiceEngine, OmniVoiceEngine
from omnivoice_realtime.schemas import TTSRequest, VoiceMode


def test_mock_engine_generates_deterministic_audio_and_metrics():
    engine = MockOmniVoiceEngine(sample_rate=24000)
    request = TTSRequest(text="Hola", language="Spanish", num_step=16)

    result = engine.generate(request)

    assert result.sample_rate == 24000
    assert isinstance(result.audio, np.ndarray)
    assert result.audio.dtype == np.float32
    assert 0.3 <= result.duration_seconds <= 10
    assert result.metrics.audio_seconds == result.duration_seconds
    assert result.metrics.rtf >= 0


def test_voice_clone_prompt_cache_is_reused_for_same_voice_id(tmp_path):
    engine = MockOmniVoiceEngine(sample_rate=24000)
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"fake audio")

    first = engine.cache_voice_clone("voice-sample", str(ref), "Hola mundo")
    second = engine.cache_voice_clone("voice-sample", str(ref), "Hola mundo")

    assert first.voice_id == "voice-sample"
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.voice_id == first.voice_id


def test_real_engine_exposes_automatic_asr_transcript_from_clone_prompt(tmp_path):
    class FakeModel:
        def create_voice_clone_prompt(self, ref_audio, ref_text):
            assert ref_text is None
            return SimpleNamespace(ref_text="Hola, esta transcripción vino del ASR.")

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"fake audio")
    engine = OmniVoiceEngine.__new__(OmniVoiceEngine)
    engine._model = FakeModel()
    engine.sample_rate = 24000
    engine._lock = threading.Lock()
    engine._voices = {}

    result = engine.cache_voice_clone("auto-asr", str(ref))

    assert result.ref_text == "Hola, esta transcripción vino del ASR."
    assert engine._voices["auto-asr"].ref_text == result.ref_text



def test_generate_accepts_clone_voice_mode_with_cached_voice(tmp_path):
    engine = MockOmniVoiceEngine(sample_rate=24000)
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"fake audio")
    engine.cache_voice_clone("voice-sample", str(ref), "Hola mundo")

    result = engine.generate(
        TTSRequest(text="Buenos días", voice_mode=VoiceMode.CLONE, voice_id="voice-sample")
    )

    assert result.voice_id == "voice-sample"
