from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import uuid4

import anyio
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse

from omnivoice_realtime.audio_formats import encode_audio
from omnivoice_realtime.engine import MockOmniVoiceEngine, OmniVoiceEngine, TTSEngine
from omnivoice_realtime.schemas import (
    BatchTTSAudioResponse,
    BatchTTSRequest,
    HealthResponse,
    TTSAudioResponse,
    TTSRequest,
    TTSStreamConfig,
    TextPrepareRequest,
    TextPrepareResponse,
    VoiceCacheResponse,
    VoiceListResponse,
    VoiceRecord,
    VoiceMode,
)
from omnivoice_realtime.text_chunker import TextChunker
from omnivoice_realtime.text_normalization import prepare_text
from omnivoice_realtime.voice_registry import VoiceRegistry


_VOICE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac"}


def _validate_voice_id(voice_id: str) -> str:
    if not _VOICE_ID_RE.fullmatch(voice_id):
        raise HTTPException(
            status_code=400,
            detail="voice_id must be 1-80 chars using only letters, numbers, dot, underscore, or dash",
        )
    return voice_id


def _safe_audio_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".wav"
    if suffix not in _ALLOWED_AUDIO_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported audio file extension: {suffix}")
    return suffix


def _safe_upload_target(upload_dir: Path, voice_id: str, suffix: str) -> Path:
    base = upload_dir.resolve()
    target = (upload_dir / f"{voice_id}{suffix}").resolve()
    if base not in target.parents and target != base:
        raise HTTPException(status_code=400, detail="voice_id escapes upload directory")
    return target


async def _write_upload_limited(upload: UploadFile, target: Path, max_bytes: int) -> None:
    total = 0
    with target.open("xb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Reference audio upload too large")
            out.write(chunk)


def _cached_voice_ids(engine: TTSEngine) -> set[str]:
    voices = getattr(engine, "_voices", {})
    if isinstance(voices, dict):
        return set(voices.keys())
    return set()


def _registered_audio_path(registry: VoiceRegistry, record: dict) -> Path:
    path = Path(record.get("ref_audio_path") or "").resolve()
    root = registry.audio_root.resolve()
    if root not in path.parents or path.suffix.lower() not in _ALLOWED_AUDIO_SUFFIXES or not path.is_file():
        raise HTTPException(status_code=409, detail="Registered reference audio unavailable")
    return path


def _record_to_response(record: dict, engine: TTSEngine, registry: VoiceRegistry) -> VoiceRecord:
    try:
        _registered_audio_path(registry, record)
        exists = True
    except (HTTPException, OSError, ValueError):
        exists = False
    public = {key: value for key, value in record.items() if key in VoiceRecord.model_fields}
    return VoiceRecord(
        **public,
        cached=record.get("voice_id") in _cached_voice_ids(engine),
        ref_audio_exists=exists,
    )


def _warm_voice_from_registry(registry: VoiceRegistry, engine: TTSEngine, voice_id: str) -> VoiceCacheResponse:
    record = registry.get(voice_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown registered voice_id: {voice_id}")
    ref_audio_path = str(_registered_audio_path(registry, record))
    try:
        result = engine.cache_voice_clone(voice_id, ref_audio_path, record.get("ref_text"))
        return VoiceCacheResponse(
            voice_id=result.voice_id,
            cache_hit=result.cache_hit,
            ref_text=result.ref_text,
            registered=True,
        )
    except Exception as exc:  # noqa: BLE001 - API boundary converts to HTTP error
        raise HTTPException(status_code=400, detail="Request could not be completed") from exc


def _auto_warm_registered_voice(registry: VoiceRegistry, engine: TTSEngine, request: TTSRequest) -> None:
    if request.voice_mode != VoiceMode.CLONE or not request.voice_id:
        return
    if request.voice_id in _cached_voice_ids(engine):
        return
    record = registry.get(request.voice_id)
    if record is None:
        return
    ref_audio_path = str(_registered_audio_path(registry, record))
    engine.cache_voice_clone(request.voice_id, ref_audio_path, record.get("ref_text"))


def _generate_audio_response(registry: VoiceRegistry, engine: TTSEngine, request: TTSRequest) -> TTSAudioResponse:
    if request.ref_audio_path is not None:
        raise HTTPException(status_code=400, detail="Upload reference audio and use voice_id instead")
    _auto_warm_registered_voice(registry, engine, request)
    result = engine.generate(request)
    packet = encode_audio(result.audio, result.sample_rate, request.format.value)
    return TTSAudioResponse(
        **packet.model_dump(),
        metrics=result.metrics,
        voice_id=result.voice_id,
    )


def build_engine_from_env() -> TTSEngine:
    if os.getenv("OMNIVOICE_MOCK", "0") == "1":
        return MockOmniVoiceEngine()
    return OmniVoiceEngine(
        model_id=os.getenv("OMNIVOICE_MODEL", "k2-fsa/OmniVoice"),
        device_map=os.getenv("OMNIVOICE_DEVICE", "cuda:0"),
        dtype=os.getenv("OMNIVOICE_DTYPE", "float16"),
        asr_model_name=os.getenv("OMNIVOICE_ASR_MODEL", "openai/whisper-small"),
        asr_device=os.getenv("OMNIVOICE_ASR_DEVICE") or None,
    )


def create_app(engine: TTSEngine | None = None) -> FastAPI:
    app = FastAPI(title="OmniVoice Realtime API", version="0.3.0")
    allowed_hosts = [h.strip() for h in os.getenv("OMNIVOICE_ALLOWED_HOSTS", "127.0.0.1,localhost,[::1]").split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    app.state.engine = engine or build_engine_from_env()
    app.state.ui_dir = Path(__file__).parent / "ui"
    upload_dir = Path(os.getenv("OMNIVOICE_UPLOAD_DIR") or Path.home() / ".local" / "share") / "omnivoice-realtime"
    upload_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    app.state.upload_dir = upload_dir
    registry_path = Path(os.getenv("OMNIVOICE_VOICE_REGISTRY") or upload_dir / "voices.json")
    app.state.voice_registry = VoiceRegistry(registry_path, audio_root=upload_dir)
    app.state.max_upload_bytes = int(os.getenv("OMNIVOICE_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))

    @app.middleware("http")
    async def reject_cross_origin(request, call_next):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse(status_code=403, content={"detail": "Cross-origin request denied"})
        return await call_next(request)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/ui")

    @app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
    def studio_ui() -> HTMLResponse:
        return HTMLResponse((app.state.ui_dir / "index.html").read_text(encoding="utf-8"))

    @app.get("/ui/app.js", include_in_schema=False)
    def studio_javascript() -> Response:
        return Response(
            (app.state.ui_dir / "app.js").read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

    @app.get("/ui/styles.css", include_in_schema=False)
    def studio_styles() -> Response:
        return Response(
            (app.state.ui_dir / "styles.css").read_text(encoding="utf-8"),
            media_type="text/css",
        )

    @app.get("/ui/pro", response_class=HTMLResponse, include_in_schema=False)
    def pro_studio_ui() -> HTMLResponse:
        return HTMLResponse((app.state.ui_dir / "pro" / "index.html").read_text(encoding="utf-8"))

    @app.get("/ui/pro/app.js", include_in_schema=False)
    def pro_studio_javascript() -> Response:
        return Response(
            (app.state.ui_dir / "pro" / "app.js").read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

    @app.get("/ui/pro/styles.css", include_in_schema=False)
    def pro_studio_styles() -> Response:
        return Response(
            (app.state.ui_dir / "pro" / "styles.css").read_text(encoding="utf-8"),
            media_type="text/css",
        )

    @app.post("/v1/text/prepare", response_model=TextPrepareResponse)
    def prepare_spoken_text(request: TextPrepareRequest) -> TextPrepareResponse:
        prepared, replacements = prepare_text(
            request.text,
            request.pronunciation_profile,
            request.custom_pronunciations,
        )
        return TextPrepareResponse(
            original_text=request.text,
            prepared_text=prepared,
            pronunciation_profile=request.pronunciation_profile,
            replacements=replacements,
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        tts: TTSEngine = app.state.engine
        return HealthResponse(ready=tts.is_ready(), engine=tts.name, sample_rate=tts.sample_rate)

    @app.post("/v1/tts", response_model=TTSAudioResponse)
    def tts(request: TTSRequest) -> TTSAudioResponse:
        try:
            return _generate_audio_response(app.state.voice_registry, app.state.engine, request)
        except Exception as exc:  # noqa: BLE001 - API boundary converts to HTTP error
            raise HTTPException(status_code=400, detail="Request could not be completed") from exc

    @app.post("/v1/tts/batch", response_model=BatchTTSAudioResponse)
    def tts_batch(request: BatchTTSRequest) -> BatchTTSAudioResponse:
        try:
            items = [
                _generate_audio_response(app.state.voice_registry, app.state.engine, item)
                for item in request.items
            ]
            return BatchTTSAudioResponse(items=items, count=len(items))
        except Exception as exc:  # noqa: BLE001 - API boundary converts to HTTP error
            raise HTTPException(status_code=400, detail="Request could not be completed") from exc

    @app.post("/v1/voices/clone-cache", response_model=VoiceCacheResponse)
    async def clone_cache(
        voice_id: str = Form(default_factory=lambda: str(uuid4())),
        ref_text: str | None = Form(default=None),
        label: str | None = Form(default=None),
        language: str | None = Form(default=None),
        notes: str | None = Form(default=None),
        ref_audio: UploadFile = File(...),
    ) -> VoiceCacheResponse:
        safe_voice_id = _validate_voice_id(voice_id)
        suffix = _safe_audio_suffix(ref_audio.filename or "ref.wav")
        if app.state.voice_registry.get(safe_voice_id) is not None:
            raise HTTPException(status_code=409, detail="Voice already registered; use a new voice_id")
        target = _safe_upload_target(app.state.upload_dir, str(uuid4()), suffix)
        try:
            await _write_upload_limited(ref_audio, target, app.state.max_upload_bytes)
            result = app.state.engine.cache_voice_clone(safe_voice_id, str(target), ref_text)
            app.state.voice_registry.upsert(
                voice_id=safe_voice_id,
                ref_audio_path=target,
                ref_audio_filename="reference" + suffix,
                ref_text=result.ref_text,
                label=label,
                language=language,
                notes=notes,
            )
            return VoiceCacheResponse(
                voice_id=result.voice_id,
                cache_hit=result.cache_hit,
                ref_text=result.ref_text,
                registered=True,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Request could not be completed") from exc

    @app.get("/v1/voices", response_model=VoiceListResponse)
    def list_voices() -> VoiceListResponse:
        voices = [_record_to_response(record, app.state.engine, app.state.voice_registry) for record in app.state.voice_registry.list()]
        return VoiceListResponse(voices=voices, count=len(voices))

    @app.get("/v1/voices/{voice_id}", response_model=VoiceRecord)
    def get_voice(voice_id: str) -> VoiceRecord:
        safe_voice_id = _validate_voice_id(voice_id)
        record = app.state.voice_registry.get(safe_voice_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Unknown registered voice_id: {safe_voice_id}")
        return _record_to_response(record, app.state.engine, app.state.voice_registry)

    @app.post("/v1/voices/{voice_id}/warm-cache", response_model=VoiceCacheResponse)
    def warm_registered_voice(voice_id: str) -> VoiceCacheResponse:
        safe_voice_id = _validate_voice_id(voice_id)
        return _warm_voice_from_registry(app.state.voice_registry, app.state.engine, safe_voice_id)

    @app.websocket("/v1/tts/stream")
    async def tts_stream(ws: WebSocket) -> None:
        origin = ws.headers.get("origin")
        expected = ("https" if ws.url.scheme == "wss" else "http") + "://" + ws.url.netloc
        if origin and origin != expected:
            await ws.close(code=1008)
            return
        await ws.accept()
        config = TTSStreamConfig()
        chunker = TextChunker(max_chars=config.chunk_max_chars)
        seq = 0
        try:
            while True:
                try:
                    message = await ws.receive_json()
                    msg_type = message.get("type")
                    if msg_type == "start":
                        config = TTSStreamConfig(**message)
                        chunker = TextChunker(max_chars=config.chunk_max_chars)
                        seq = 0
                        await ws.send_json(
                            {
                                "type": "ready",
                                "engine": app.state.engine.name,
                                "sample_rate": app.state.engine.sample_rate,
                            }
                        )
                    elif msg_type == "text":
                        for chunk in chunker.push(str(message.get("text", ""))):
                            seq = await _send_audio_for_chunk(ws, app.state.engine, app.state.voice_registry, config, chunk, seq)
                    elif msg_type == "flush":
                        emitted = False
                        for chunk in chunker.flush():
                            emitted = True
                            seq = await _send_audio_for_chunk(ws, app.state.engine, app.state.voice_registry, config, chunk, seq)
                        await ws.send_json({"type": "done", "seq": seq, "emitted": emitted})
                    elif msg_type == "cancel":
                        chunker.reset()
                        await ws.send_json({"type": "cancelled"})
                    elif msg_type == "ping":
                        await ws.send_json({"type": "pong"})
                    else:
                        await ws.send_json({"type": "error", "detail": f"Unknown message type: {msg_type}"})
                except WebSocketDisconnect:
                    return
                except Exception as exc:  # noqa: BLE001 - keep websocket alive on bad request
                    await ws.send_json({"type": "error", "detail": "Request could not be completed"})
        except WebSocketDisconnect:
            return

    return app


async def _send_audio_for_chunk(
    ws: WebSocket, engine: TTSEngine, registry: VoiceRegistry, config: TTSStreamConfig, chunk: str, seq: int
) -> int:
    """Generate and send one chunk without blocking the websocket event loop."""
    next_seq = seq + 1
    request = config.to_request(chunk)
    await anyio.to_thread.run_sync(_auto_warm_registered_voice, registry, engine, request)
    result = await anyio.to_thread.run_sync(engine.generate, request)
    packet = encode_audio(result.audio, result.sample_rate, request.format.value, seq=next_seq)
    await ws.send_json(
        {
            **packet.model_dump(),
            "text": chunk,
            "metrics": result.metrics.model_dump(),
            "voice_id": result.voice_id,
        }
    )
    return next_seq
