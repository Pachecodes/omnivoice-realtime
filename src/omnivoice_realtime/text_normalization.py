from __future__ import annotations

import re

from omnivoice_realtime.schemas import PronunciationProfile

_PROFILES: dict[str, tuple[tuple[str, str], ...]] = {
    "es-latam-tech": (
        (r"\bChatGPT\b", "Chat, ge pe te"),
        (r"\bElevenLabs\b", "Eleven Labs"),
        (r"\bYOO\s+Media\b", "Yú Media"),
        (r"\bHeyGen\b", "Hey Gen"),
        (r"\bIA\b", "inteligencia artificial"),
    )
}


def prepare_text(
    text: str,
    profile: PronunciationProfile = "none",
    custom_pronunciations: dict[str, str] | None = None,
) -> tuple[str, int]:
    """Apply deterministic built-in and custom spoken-form replacements."""
    prepared = text
    replacements = 0

    for pattern, spoken_form in _PROFILES.get(profile, ()):
        prepared, count = re.subn(pattern, spoken_form, prepared, flags=re.IGNORECASE)
        replacements += count

    entries = sorted((custom_pronunciations or {}).items(), key=lambda item: len(item[0]), reverse=True)
    for written_form, spoken_form in entries:
        written_form = written_form.strip()
        spoken_form = spoken_form.strip()
        if not written_form or not spoken_form:
            continue
        prefix = r"(?<!\w)" if written_form[0].isalnum() else ""
        suffix = r"(?!\w)" if written_form[-1].isalnum() else ""
        pattern = f"{prefix}{re.escape(written_form)}{suffix}"
        prepared, count = re.subn(pattern, spoken_form, prepared, flags=re.IGNORECASE)
        replacements += count

    return prepared, replacements
