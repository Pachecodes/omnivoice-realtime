# API reference and transport boundaries

[← Project overview](../README.md) · [Documentation index](README.md)

## Scope and limitations

- `POST /v1/tts`: one JSON audio packet, base64 WAV or mono PCM16.
- `POST /v1/tts/batch`: up to 20 requests, sequential generation, not parallel inference.
- `WS /v1/tts/stream`: incremental input split into text chunks; **whole audio
  for each chunk is generated before sending**. This is realtime-ish transport,
  not token-level streaming, full duplex speech, WebRTC, or a phone agent.
- `POST /v1/voices/clone-cache`: upload a consented reference and optional
  transcript. The real engine may use Whisper when the transcript is omitted.
- `GET /v1/voices`, `GET /v1/voices/{voice_id}`, and
  `POST /v1/voices/{voice_id}/warm-cache`: local registry and restart warming.
- `POST /v1/text/prepare`: deterministic pronunciation replacements; built-in
  `es-latam-tech` and a custom dictionary.
- `/ui` and `/ui/pro`: basic Studio and inference/batch workbench, sharing the
  same engine. `/docs` exposes the API schema; `/health` reports engine readiness.

This is a **single-operator local research tool**, not an authenticated hosted
service. No tenant isolation, quotas, automatic deletion, or guaranteed latency.
Cancel resets buffered text but does not interrupt active inference. Use one
worker; the JSON registry is not a concurrent database. Existing voice IDs
cannot be overwritten: choose a new ID. API callers cannot supply arbitrary
local reference paths; upload first and use `voice_id`. References persist on
disk and clone prompts live in memory; audio must remain available for restart.
Voice design attributes are an upstream capability, not guaranteed emotion
control. Auto mode does not lock speaker identity. Verify every real result.

## REST and voice usage

```bash
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/v1/tts -H 'Content-Type: application/json' \
  -d '{"text":"Hola mundo.","language":"Spanish","voice_mode":"auto","format":"wav"}'
```

Response is **JSON**, not a raw WAV response. Decode `audio_base64` before writing
audio. PCM16 is signed little-endian mono at the returned sample rate; WAV adds
a container. Metrics describe the current engine, including mock timings.

Use a clean, consented 3–10 second reference in the target language, without
music or unnecessary personal information. Obtain rights to both the recording
and voice identity; the ability to upload audio does not establish consent.

```bash
curl http://127.0.0.1:8010/v1/voices/clone-cache \
  -F voice_id=demo_voice -F ref_text='Exact words in the reference.' \
  -F ref_audio=@reference.wav
curl http://127.0.0.1:8010/v1/tts -H 'Content-Type: application/json' \
  -d '{"text":"Una prueba con permiso.","voice_mode":"clone","voice_id":"demo_voice","format":"wav"}'
```

Allowed reference extensions: WAV, MP3, M4A, OGG, FLAC, AAC; actual codec support
comes from upstream/audio libraries. HTTP errors do not expose engine exceptions.
For practical deletion/revocation and deployment boundaries, see [SECURITY.md](../SECURITY.md).

## WebSocket protocol

Connect to `ws://127.0.0.1:8010/v1/tts/stream`, then send JSON messages:

```json
{"type":"start","language":"Spanish","num_step":16,"format":"pcm16"}
{"type":"text","text":"Hola mundo."}
{"type":"flush"}
```

Receive `ready`, zero or more `audio` packets with `seq` and `audio_base64`, and
`done` after flush. `ping` returns `pong`; `cancel` returns `cancelled`; malformed
or failing requests return `error`. A text chunk ending in punctuation may emit
before flush. The included `python scripts/ws_smoke.py` targets loopback port
8010; its output is test-engine audio when the server runs in mock mode.

