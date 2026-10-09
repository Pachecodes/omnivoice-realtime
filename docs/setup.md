# Setup guide

[← Project overview](../README.md) · [Documentation index](README.md)

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

See [`.env.example`](../.env.example); it contains no credentials. Uvicorn accepts
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

