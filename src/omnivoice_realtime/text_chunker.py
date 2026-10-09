from __future__ import annotations

import re

_SENTENCE_RE = re.compile(r"(.+?[.!?。！？]\s*)", re.DOTALL)
class TextChunker:
    """Incremental sentence/phrase chunker for low-latency TTS streaming."""

    def __init__(self, max_chars: int = 220):
        self.max_chars = max_chars
        self._buffer = ""

    def push(self, text: str) -> list[str]:
        self._buffer += text
        chunks: list[str] = []

        while True:
            match = _SENTENCE_RE.match(self._buffer)
            if not match:
                break
            chunk = match.group(1).strip()
            self._buffer = self._buffer[match.end() :].lstrip()
            if chunk:
                chunks.append(chunk)

        chunks.extend(self._drain_long_prefixes())
        return chunks

    def flush(self) -> list[str]:
        chunks = self._drain_long_prefixes(force=True)
        rest = self._buffer.strip()
        self._buffer = ""
        if rest:
            chunks.append(rest)
        return chunks

    def reset(self) -> None:
        self._buffer = ""

    def _drain_long_prefixes(self, force: bool = False) -> list[str]:
        chunks: list[str] = []
        while len(self._buffer.strip()) > self.max_chars or (
            force and len(self._buffer.strip()) > self.max_chars
        ):
            split_at = self._find_split_index(self._buffer, self.max_chars)
            if split_at <= 0:
                break
            chunk = self._buffer[:split_at].strip()
            self._buffer = self._buffer[split_at:].lstrip()
            if chunk:
                chunks.append(chunk)
        return chunks

    @staticmethod
    def _find_split_index(text: str, max_chars: int) -> int:
        window = text[: max_chars + 1]
        for boundary in (",", ";", ":", "—", "-"):
            idx = window.rfind(boundary)
            if idx > 0:
                return idx + 1
        idx = window.rfind(" ")
        if idx > 0:
            return idx
        return max_chars
