from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceRegistry:
    """Tiny JSON-backed registry for durable cloned voice references.

    The actual OmniVoice clone prompt lives in process memory, so this registry keeps
    the uploaded reference-audio path and transcript needed to rebuild that prompt
    after a service restart.
    """

    def __init__(self, path: Path, audio_root: Path | None = None):
        self.path = path
        self.audio_root = audio_root or path.parent
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "voices": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Preserve a corrupt file for manual inspection instead of overwriting it silently.
            backup = self.path.with_suffix(self.path.suffix + f".corrupt-{int(datetime.now().timestamp())}")
            self.path.replace(backup)
            return {"version": 1, "voices": {}}
        if not isinstance(data, dict):
            return {"version": 1, "voices": {}}
        voices = data.get("voices")
        if not isinstance(voices, dict):
            data["voices"] = {}
        data.setdefault("version", 1)
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False) as tmp:
            tmp.write(rendered)
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.path)

    def upsert(
        self,
        *,
        voice_id: str,
        ref_audio_path: Path,
        ref_text: str | None,
        ref_audio_filename: str | None = None,
        label: str | None = None,
        language: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        data = self.load()
        voices: dict[str, Any] = data.setdefault("voices", {})
        now = utc_now_iso()
        existing = voices.get(voice_id) if isinstance(voices.get(voice_id), dict) else {}
        record = {
            **existing,
            "voice_id": voice_id,
            "ref_audio_path": str(ref_audio_path),
            "ref_audio_filename": ref_audio_filename,
            "ref_text": ref_text,
            "label": label if label is not None else existing.get("label"),
            "language": language if language is not None else existing.get("language"),
            "notes": notes if notes is not None else existing.get("notes"),
            "created_at": existing.get("created_at") or now,
            "updated_at": now,
        }
        voices[voice_id] = record
        self.save(data)
        return record

    def list(self) -> list[dict[str, Any]]:
        data = self.load()
        voices = data.get("voices", {})
        return [v for _, v in sorted(voices.items()) if isinstance(v, dict)]

    def get(self, voice_id: str) -> dict[str, Any] | None:
        data = self.load()
        record = data.get("voices", {}).get(voice_id)
        return record if isinstance(record, dict) else None
