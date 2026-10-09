from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from omnivoice_realtime.schemas import GenerateResult, GenerationMetrics, TTSRequest, VoiceCacheResponse, VoiceMode
from omnivoice_realtime.text_normalization import prepare_text


class TTSEngine(Protocol):
    name: str
    sample_rate: int

    def is_ready(self) -> bool: ...

    def generate(self, request: TTSRequest) -> GenerateResult: ...

    def cache_voice_clone(
        self, voice_id: str, ref_audio_path: str, ref_text: str | None = None
    ) -> VoiceCacheResponse: ...


@dataclass
class _CachedVoice:
    voice_id: str
    ref_audio_path: str
    ref_text: str | None
    prompt: Any


class MockOmniVoiceEngine:
    """Deterministic fast test engine; no GPU/model required."""

    name = "mock"

    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self._voices: dict[str, _CachedVoice] = {}

    def is_ready(self) -> bool:
        return True

    def cache_voice_clone(
        self, voice_id: str, ref_audio_path: str, ref_text: str | None = None
    ) -> VoiceCacheResponse:
        if voice_id in self._voices:
            cached = self._voices[voice_id]
            return VoiceCacheResponse(voice_id=voice_id, cache_hit=True, ref_text=cached.ref_text)
        transcript = ref_text or "Transcripción automática de prueba."
        self._voices[voice_id] = _CachedVoice(
            voice_id=voice_id,
            ref_audio_path=ref_audio_path,
            ref_text=transcript,
            prompt={"mock": True, "path": ref_audio_path},
        )
        return VoiceCacheResponse(voice_id=voice_id, cache_hit=False, ref_text=transcript)

    def generate(self, request: TTSRequest) -> GenerateResult:
        start = time.perf_counter()
        if request.voice_mode == VoiceMode.CLONE and request.voice_id not in self._voices:
            raise ValueError(f"Unknown cached voice_id: {request.voice_id}")
        duration = min(10.0, max(0.35, len(request.text) * 0.055 / max(request.speed, 0.1)))
        n = int(duration * self.sample_rate)
        digest = hashlib.sha1(request.text.encode("utf-8")).digest()
        freq = 180 + digest[0]
        t = np.arange(n, dtype=np.float32) / self.sample_rate
        envelope = np.minimum(1.0, np.linspace(0, 10, n, dtype=np.float32))
        audio = 0.08 * envelope * np.sin(2 * math.pi * freq * t)
        generation_seconds = time.perf_counter() - start
        return GenerateResult(
            audio=audio.astype(np.float32),
            sample_rate=self.sample_rate,
            duration_seconds=duration,
            metrics=GenerationMetrics(
                generation_seconds=generation_seconds,
                audio_seconds=duration,
                rtf=generation_seconds / duration if duration else 0.0,
            ),
            voice_id=request.voice_id,
        )


class OmniVoiceEngine:
    """Production OmniVoice engine with persistent model and clone prompt cache."""

    name = "omnivoice"

    def __init__(
        self,
        model_id: str = "k2-fsa/OmniVoice",
        device_map: str = "cuda:0",
        dtype: str = "float16",
        asr_model_name: str = "openai/whisper-small",
        asr_device: str | None = None,
    ):
        import torch
        from omnivoice import OmniVoice

        dtype_obj = getattr(torch, dtype)
        self._model = OmniVoice.from_pretrained(
            model_id,
            device_map=device_map,
            dtype=dtype_obj,
            asr_model_name=asr_model_name,
            asr_device=asr_device or device_map,
        )
        self.sample_rate = int(getattr(self._model, "sampling_rate", 24000))
        self._voices: dict[str, _CachedVoice] = {}
        self._lock = threading.Lock()

    def is_ready(self) -> bool:
        return True

    def cache_voice_clone(
        self, voice_id: str, ref_audio_path: str, ref_text: str | None = None
    ) -> VoiceCacheResponse:
        if voice_id in self._voices:
            cached = self._voices[voice_id]
            return VoiceCacheResponse(voice_id=voice_id, cache_hit=True, ref_text=cached.ref_text)
        if not Path(ref_audio_path).exists():
            raise FileNotFoundError(ref_audio_path)
        with self._lock:
            if voice_id in self._voices:
                cached = self._voices[voice_id]
                return VoiceCacheResponse(voice_id=voice_id, cache_hit=True, ref_text=cached.ref_text)
            prompt = self._model.create_voice_clone_prompt(
                ref_audio=ref_audio_path,
                ref_text=ref_text or None,
            )
            transcript = str(getattr(prompt, "ref_text", None) or ref_text or "")
            self._voices[voice_id] = _CachedVoice(
                voice_id=voice_id,
                ref_audio_path=ref_audio_path,
                ref_text=transcript,
                prompt=prompt,
            )
        return VoiceCacheResponse(voice_id=voice_id, cache_hit=False, ref_text=transcript)

    def generate(self, request: TTSRequest) -> GenerateResult:
        start = time.perf_counter()
        prepared_text, _ = prepare_text(
            request.text,
            request.pronunciation_profile,
            request.custom_pronunciations,
        )
        kwargs: dict[str, Any] = {
            "text": prepared_text,
            "language": request.language,
            "num_step": request.num_step,
            "speed": request.speed,
            "guidance_scale": request.guidance_scale,
            "t_shift": request.t_shift,
            "position_temperature": request.position_temperature,
            "class_temperature": request.class_temperature,
            "layer_penalty_factor": request.layer_penalty_factor,
            "denoise": request.denoise,
            "preprocess_prompt": request.preprocess_prompt,
            "postprocess_output": request.postprocess_output,
            "pad_duration": request.pad_duration,
            "fade_duration": request.fade_duration,
            "audio_chunk_duration": request.audio_chunk_duration,
            "audio_chunk_threshold": request.audio_chunk_threshold,
            "normalize_text": request.normalize_text,
        }
        if request.duration is not None:
            kwargs["duration"] = request.duration
        if request.instruct:
            kwargs["instruct"] = request.instruct
        if request.voice_mode == VoiceMode.CLONE:
            if request.voice_id:
                cached = self._voices.get(request.voice_id)
                if cached is None:
                    raise ValueError(f"Unknown cached voice_id: {request.voice_id}")
                kwargs["voice_clone_prompt"] = cached.prompt
            elif request.ref_audio_path:
                kwargs["ref_audio"] = request.ref_audio_path
                kwargs["ref_text"] = request.ref_text
            else:
                raise ValueError("clone mode requires voice_id or ref_audio_path")

        with self._lock:
            audios = self._model.generate(**kwargs)
        audio = np.asarray(audios[0], dtype=np.float32)
        duration_seconds = len(audio) / self.sample_rate
        generation_seconds = time.perf_counter() - start
        return GenerateResult(
            audio=audio,
            sample_rate=self.sample_rate,
            duration_seconds=duration_seconds,
            metrics=GenerationMetrics(
                generation_seconds=generation_seconds,
                audio_seconds=duration_seconds,
                rtf=generation_seconds / duration_seconds if duration_seconds else 0.0,
            ),
            voice_id=request.voice_id,
        )
