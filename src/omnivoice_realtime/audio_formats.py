from __future__ import annotations

import base64
import io

import numpy as np
import soundfile as sf

from omnivoice_realtime.schemas import AudioPacket


def _float_to_pcm16(audio: np.ndarray) -> bytes:
    clipped = np.clip(audio.astype(np.float32), -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def encode_audio(audio: np.ndarray, sample_rate: int, fmt: str, seq: int = 1) -> AudioPacket:
    """Encode mono float32 audio to a JSON-friendly base64 audio packet."""
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    duration_seconds = float(len(audio) / sample_rate) if sample_rate else 0.0

    if fmt == "pcm16":
        raw = _float_to_pcm16(audio)
        encoding = "pcm16"
    elif fmt == "wav":
        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
        raw = buffer.getvalue()
        encoding = "wav"
    else:
        raise ValueError(f"Unsupported audio format: {fmt}")

    return AudioPacket(
        seq=seq,
        sample_rate=sample_rate,
        encoding=encoding,
        duration_seconds=duration_seconds,
        audio_base64=base64.b64encode(raw).decode("ascii"),
    )
