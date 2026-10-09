from __future__ import annotations

from enum import StrEnum
from typing import Literal

PronunciationProfile = Literal["none", "es-latam-tech"]

from pydantic import BaseModel, Field


class VoiceMode(StrEnum):
    AUTO = "auto"
    DESIGN = "design"
    CLONE = "clone"


class AudioFormat(StrEnum):
    PCM16 = "pcm16"
    WAV = "wav"


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: str | None = "Spanish"
    voice_mode: VoiceMode = VoiceMode.AUTO
    voice_id: str | None = None
    instruct: str | None = None
    ref_text: str | None = None
    ref_audio_path: str | None = None
    pronunciation_profile: PronunciationProfile = "none"
    custom_pronunciations: dict[str, str] = Field(default_factory=dict, max_length=100)
    normalize_text: bool = False
    num_step: int = Field(32, ge=4, le=64)
    speed: float = Field(1.0, gt=0.2, le=3.0)
    duration: float | None = Field(default=None, gt=0.0, le=120.0)
    guidance_scale: float = Field(2.0, ge=0.0, le=4.0)
    t_shift: float = Field(0.1, ge=0.0, le=1.0)
    position_temperature: float = Field(5.0, ge=0.0, le=20.0)
    class_temperature: float = Field(0.0, ge=0.0, le=5.0)
    layer_penalty_factor: float = Field(5.0, ge=0.0, le=20.0)
    denoise: bool = True
    preprocess_prompt: bool = True
    postprocess_output: bool = True
    pad_duration: float = Field(0.1, ge=0.0, le=2.0)
    fade_duration: float = Field(0.1, ge=0.0, le=2.0)
    audio_chunk_duration: float = Field(15.0, gt=0.0, le=120.0)
    audio_chunk_threshold: float = Field(30.0, gt=0.0, le=600.0)
    format: AudioFormat = AudioFormat.PCM16


class BatchTTSRequest(BaseModel):
    items: list[TTSRequest] = Field(..., min_length=1, max_length=20)


class TTSStreamConfig(BaseModel):
    type: Literal["start"] = "start"
    language: str | None = "Spanish"
    voice_mode: VoiceMode = VoiceMode.AUTO
    voice_id: str | None = None
    instruct: str | None = None
    pronunciation_profile: PronunciationProfile = "none"
    custom_pronunciations: dict[str, str] = Field(default_factory=dict, max_length=100)
    normalize_text: bool = False
    num_step: int = Field(16, ge=4, le=64)
    speed: float = Field(1.0, gt=0.2, le=3.0)
    guidance_scale: float = Field(2.0, ge=0.0, le=4.0)
    t_shift: float = Field(0.1, ge=0.0, le=1.0)
    position_temperature: float = Field(5.0, ge=0.0, le=20.0)
    class_temperature: float = Field(0.0, ge=0.0, le=5.0)
    layer_penalty_factor: float = Field(5.0, ge=0.0, le=20.0)
    denoise: bool = True
    preprocess_prompt: bool = True
    postprocess_output: bool = True
    pad_duration: float = Field(0.1, ge=0.0, le=2.0)
    fade_duration: float = Field(0.1, ge=0.0, le=2.0)
    audio_chunk_duration: float = Field(15.0, gt=0.0, le=120.0)
    audio_chunk_threshold: float = Field(30.0, gt=0.0, le=600.0)
    format: AudioFormat = AudioFormat.PCM16
    chunk_max_chars: int = Field(220, ge=20, le=1000)

    def to_request(self, text: str) -> TTSRequest:
        return TTSRequest(
            text=text,
            language=self.language,
            voice_mode=self.voice_mode,
            voice_id=self.voice_id,
            instruct=self.instruct,
            pronunciation_profile=self.pronunciation_profile,
            custom_pronunciations=self.custom_pronunciations,
            normalize_text=self.normalize_text,
            num_step=self.num_step,
            speed=self.speed,
            guidance_scale=self.guidance_scale,
            t_shift=self.t_shift,
            position_temperature=self.position_temperature,
            class_temperature=self.class_temperature,
            layer_penalty_factor=self.layer_penalty_factor,
            denoise=self.denoise,
            preprocess_prompt=self.preprocess_prompt,
            postprocess_output=self.postprocess_output,
            pad_duration=self.pad_duration,
            fade_duration=self.fade_duration,
            audio_chunk_duration=self.audio_chunk_duration,
            audio_chunk_threshold=self.audio_chunk_threshold,
            format=self.format,
        )


class TextPrepareRequest(BaseModel):
    text: str = Field(..., min_length=1)
    pronunciation_profile: PronunciationProfile = "none"
    custom_pronunciations: dict[str, str] = Field(default_factory=dict, max_length=100)


class TextPrepareResponse(BaseModel):
    original_text: str
    prepared_text: str
    pronunciation_profile: PronunciationProfile
    replacements: int


class AudioPacket(BaseModel):
    type: Literal["audio"] = "audio"
    seq: int = 1
    sample_rate: int
    encoding: str
    duration_seconds: float
    audio_base64: str


class GenerationMetrics(BaseModel):
    generation_seconds: float
    audio_seconds: float
    rtf: float


class TTSAudioResponse(AudioPacket):
    metrics: GenerationMetrics
    voice_id: str | None = None


class BatchTTSAudioResponse(BaseModel):
    items: list[TTSAudioResponse]
    count: int


class HealthResponse(BaseModel):
    ready: bool
    engine: str
    sample_rate: int


class VoiceCacheResponse(BaseModel):
    voice_id: str
    cache_hit: bool
    ref_text: str | None = None
    registered: bool = False


class VoiceRecord(BaseModel):
    voice_id: str
    ref_audio_filename: str | None = None
    ref_text: str | None = None
    label: str | None = None
    language: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    cached: bool = False
    ref_audio_exists: bool = False


class VoiceListResponse(BaseModel):
    voices: list[VoiceRecord]
    count: int


class GenerateResult(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    audio: object
    sample_rate: int
    duration_seconds: float
    metrics: GenerationMetrics
    voice_id: str | None = None
