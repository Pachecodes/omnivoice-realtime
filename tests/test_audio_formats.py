import base64
import numpy as np

from omnivoice_realtime.audio_formats import encode_audio


def test_encode_audio_pcm16_base64_has_expected_length_and_metadata():
    samples = np.array([-1.0, 0.0, 1.0], dtype=np.float32)

    packet = encode_audio(samples, sample_rate=24000, fmt="pcm16")

    raw = base64.b64decode(packet.audio_base64)
    assert packet.encoding == "pcm16"
    assert packet.sample_rate == 24000
    assert packet.duration_seconds == 3 / 24000
    assert len(raw) == 6


def test_encode_audio_wav_base64_starts_with_riff_header():
    samples = np.zeros(240, dtype=np.float32)

    packet = encode_audio(samples, sample_rate=24000, fmt="wav")

    raw = base64.b64decode(packet.audio_base64)
    assert packet.encoding == "wav"
    assert raw[:4] == b"RIFF"
    assert raw[8:12] == b"WAVE"
