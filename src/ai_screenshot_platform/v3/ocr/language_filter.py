from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageFilterResult:
    accepted: bool
    reason: str
    detected_scripts: list[str]


def detect_scripts(text: str) -> list[str]:
    scripts: set[str] = set()
    for char in text:
        code = ord(char)
        if "\u4e00" <= char <= "\u9fff":
            scripts.add("han")
        elif "a" <= char.lower() <= "z":
            scripts.add("latin")
        elif 0x3040 <= code <= 0x30FF:
            scripts.add("japanese")
        elif 0xAC00 <= code <= 0xD7AF:
            scripts.add("korean")
        elif char.isdigit():
            scripts.add("number")
    return sorted(scripts)


def filter_language(text: str, target_language: str, min_chars: int = 2) -> LanguageFilterResult:
    compact = "".join(char for char in text if not char.isspace())
    if len(compact) < min_chars:
        return LanguageFilterResult(False, "too_few_chars", detect_scripts(text))
    scripts = detect_scripts(text)
    if target_language.startswith("zh") and "han" not in scripts:
        return LanguageFilterResult(False, "wrong_language", scripts)
    if target_language.startswith("en") and "latin" not in scripts:
        return LanguageFilterResult(False, "wrong_language", scripts)
    risk_scripts = [script for script in scripts if script not in {"number", "latin" if target_language.startswith("en") else "han"}]
    if risk_scripts:
        return LanguageFilterResult(False, "mixed_language", scripts)
    return LanguageFilterResult(True, "accepted", scripts)
