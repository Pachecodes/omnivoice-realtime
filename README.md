# OmniVoice Realtime + Studio

Local FastAPI integration by **Jesús Pacheco / Akitá** for the independent
[OmniVoice upstream project](https://github.com/k2-fsa/OmniVoice). The upstream
model and research are by Han Zhu and collaborators, not by the integration
maintainer. This repository supplies REST/WebSocket transport, a persistent
reference registry, pronunciation preparation, and two Spanish-language Studio
interfaces. It does not train a model, ship weights, or include anyone's voice.

**License boundary:** original integration code/tests/Studio assets are MIT.
Upstream OmniVoice code is Apache-2.0 (copyright 2026 Xiaomi Corp.). The
[official model card](https://huggingface.co/k2-fsa/OmniVoice) states that the
pretrained model is **CC-BY-NC**, because of training-data restrictions. Do not
infer commercial model rights from this integration's MIT license. The card
does not specify a CC license version; clarify exact terms with upstream before
any redistribution or commercial use. No weights or model-data assets are
redistributed here. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

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

## Install and CPU-only mock demo

Requires Python **3.11+**, a virtual environment, and pip. The base package needs
no PyTorch, GPU, model download, or account. Mock mode produces deterministic
**test tones, not speech**, and cannot validate voice quality or cloning.

From this source checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install '.[dev]'
OMNIVOICE_MOCK=1 python -m uvicorn omnivoice_realtime.main:app --host 127.0.0.1 --port 8010 --workers 1
```

On PowerShell, set `$env:OMNIVOICE_MOCK="1"` before the Uvicorn command.
Open `http://127.0.0.1:8010/ui` or `/ui/pro`. Do not mistake mock health readiness
for genuine model readiness. `create_app()` loads a real model synchronously at
startup unless mock mode is explicitly selected.

## Genuine synthesis (separate, optional installation)

Read and accept upstream's noncommercial model terms first. Use a separate
model environment. Install matching `torch` and `torchaudio` wheels for your
hardware **before** installing this project's `omnivoice` extra:

```bash
# NVIDIA example from upstream; choose the proper CUDA build for your driver.
python -m pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
python -m pip install '.[omnivoice]'
python -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
OMNIVOICE_MOCK=0 OMNIVOICE_DEVICE=cuda:0 OMNIVOICE_DTYPE=float16 python -m uvicorn omnivoice_realtime.main:app --host 127.0.0.1 --port 8010 --workers 1
```

The optional adapter targets `omnivoice>=0.2.1,<0.3`. Dependency resolution can
change PyTorch builds: inspect the resolved environment before inference.
NVIDIA needs a compatible GPU/driver/CUDA PyTorch stack. GPU RAM, system RAM,
cache disk space and speed depend on model, ASR, and request size; this release
has **no measured minimum VRAM/RAM or latency guarantee**. Leave room for both
OmniVoice and optional Whisper. The base mock is suitable for CPU-only CI.
Real CPU inference can be selected with `OMNIVOICE_DEVICE=cpu` and
`OMNIVOICE_DTYPE=float32`, but its speed and compatibility are **not validated
in this release**. Upstream documents Apple Silicon `mps`; that adapter path is
also untested here. Do not treat macOS mock tests as GPU/MPS support proof.

Real startup downloads model dependencies/weights from upstream hosting unless
already cached; optional ASR may download `openai/whisper-small`. Set a local
`HF_HOME` if desired. No downloads occur in mock mode. Offline operation requires
all needed upstream artifacts already cached; use upstream offline settings.
Some upstream number normalization requires `omnivoice[tn]` and additional
platform-dependent libraries; it is not included by this integration's extra.

**Release verification:** model-free unit/security/Studio tests and mock health,
REST and WebSocket protocols are tested. **Real model synthesis, GPU/MPS/CPU
model execution, ASR accuracy and audio quality are untested in this preparation.**

## Configuration

See `.env.example`; it contains no credentials. Uvicorn accepts
`--env-file .env` if you deliberately copy and edit the example; environment
files are not automatically loaded by the app. Empty storage settings use defaults.

| Variable | Default / meaning |
| --- | --- |
| `OMNIVOICE_MOCK` | `0`; set exactly `1` for tones/no model |
| `OMNIVOICE_MODEL` | `k2-fsa/OmniVoice` (or an operator-approved local model) |
| `OMNIVOICE_DEVICE`, `OMNIVOICE_DTYPE` | `cuda:0`, `float16` |
| `OMNIVOICE_ASR_MODEL` | `openai/whisper-small` |
| `OMNIVOICE_ASR_DEVICE` | model device when empty |
| `OMNIVOICE_UPLOAD_DIR` | parent of `omnivoice-realtime/`; default `~/.local/share` |
| `OMNIVOICE_VOICE_REGISTRY` | default `<upload directory>/voices.json` |
| `OMNIVOICE_MAX_UPLOAD_BYTES` | `15728640` reference bytes; proxy must cap full multipart bodies |
| `OMNIVOICE_ALLOWED_HOSTS` | `127.0.0.1,localhost,[::1]`; explicit hosts, no wildcard |
| `HF_HOME` | optional cache location managed by upstream |

Host and port are Uvicorn command-line settings, not app environment variables.
Keep the upload directory private and outside the checkout. On existing storage,
verify operator-only permissions; do not rely on creation permissions to repair
an insecure directory. Never share a registry between untrusted users.

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
For practical deletion/revocation and deployment boundaries, see SECURITY.md.

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

## Privacy, consent and deployment

Never clone someone without informed permission, impersonate a third party,
commit reference audio/transcripts, or use the model for fraud. Clearly disclose
synthetic speech where appropriate. MIT applies to software, not identity rights
or upstream model commercial rights. References and transcripts persist locally;
the browser retains only the chosen voice ID in local storage. Delete that browser
storage on shared machines. No consent enforcement is implemented in software.

Bind to loopback. Remote access requires an authenticated TLS proxy protecting
**all routes including WebSockets**, firewalling, upload/request/concurrency
limits and explicit allowed hosts. This project supplies none of those identity
or rate-limit controls. Browser same-origin and Host validation are only defense
in depth. Do not directly bind to an untrusted network. See [SECURITY.md](SECURITY.md).

## Development

```bash
python -m pytest -q
python -m pip install build
python -m build
```

CI runs model-free tests, packaging, and an isolated mock wheel smoke. No weights,
voices, generated audio, private deployment scripts, secrets or Git history are
included in the release. Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
