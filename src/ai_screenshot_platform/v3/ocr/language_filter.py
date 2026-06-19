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
    allowed_scripts = _allowed_scripts(target_language)
    content_scripts = {script for script in scripts if script != "number"}
    if not content_scripts.intersection(allowed_scripts):
        return LanguageFilterResult(False, "wrong_language", scripts)
    if content_scripts - allowed_scripts:
        return LanguageFilterResult(False, "mixed_language", scripts)
    if _target_script_char_count(text, target_language) < min_chars:
        return LanguageFilterResult(False, "too_few_chars", scripts)
    return LanguageFilterResult(True, "accepted", scripts)


def _allowed_scripts(target_language: str) -> set[str]:
    if target_language.startswith("en"):
        return {"latin"}
    if target_language.startswith("ja"):
        return {"japanese", "han"}
    if target_language.startswith("ko"):
        return {"korean"}
    if target_language.startswith("zh"):
        return {"han"}
    return {"latin", "han", "japanese", "korean"}


def _target_script_char_count(text: str, target_language: str) -> int:
    count = 0
    for char in text:
        code = ord(char)
        if target_language.startswith("en") and "a" <= char.lower() <= "z":
            count += 1
        elif target_language.startswith("ja") and ("\u4e00" <= char <= "\u9fff" or 0x3040 <= code <= 0x30FF):
            count += 1
        elif target_language.startswith("ko") and 0xAC00 <= code <= 0xD7AF:
            count += 1
        elif target_language.startswith("zh") and "\u4e00" <= char <= "\u9fff":
            count += 1
    return count
