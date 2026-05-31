from __future__ import annotations

import re
import unicodedata


_REPLACEMENTS = {
    "Coca-Cola": "可口可乐",
    "Coca Cola": "可口可乐",
    "Qwen": "千问",
    "RKLLM": "",
    "RKNN": "",
}

_PUNCT_TRANSLATION = str.maketrans(
    {
        ":": "，",
        "：": "，",
        ";": "，",
        "；": "，",
        "/": "，",
        "\\": "，",
        "*": "",
        "#": "",
        "_": "",
        "~": "",
        "|": "",
        "`": "",
        '"': "",
        "'": "",
        "“": "",
        "”": "",
        "‘": "",
        "’": "",
        "(": "",
        ")": "",
        "（": "",
        "）": "",
        "[": "",
        "]": "",
        "【": "",
        "】": "",
        "{": "",
        "}": "",
        "<": "",
        ">": "",
    }
)


def sanitize_tts_text(text: str, max_chars: int = 260, fallback: str | None = "我没有生成可播报的回答。") -> str:
    """Make model output easier and stabler for Chinese TTS playback."""
    text = unicodedata.normalize("NFKC", text)
    cleaned_lines: list[str] = []
    in_code_block = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if line.startswith("I rkllm:"):
            continue
        if set(line) <= {"-"}:
            continue
        line = re.sub(r"^\s*[-*+]\s*", "", line)
        line = re.sub(r"^\s*\d+[.)、]\s*", "", line)
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"https?://\S+", "", line)
        for src, dst in _REPLACEMENTS.items():
            line = line.replace(src, dst)
        line = line.translate(_PUNCT_TRANSLATION)
        line = re.sub(r"\s+", " ", line).strip(" ，,、")
        if line:
            cleaned_lines.append(line)

    text = "。".join(cleaned_lines)
    text = re.sub(r"。+", "。", text)
    text = text.translate(_PUNCT_TRANSLATION)
    text = re.sub(r"[，,、]+。", "。", text)
    text = re.sub(r"，+", "，", text)
    text = re.sub(r"\s+", "", text)
    text = text.strip("。 \n\t")
    if len(text) > max_chars:
        text = text[:max_chars].rstrip("，,、；;：: ")
        last_stop = max(text.rfind("。"), text.rfind("！"), text.rfind("？"))
        if last_stop >= 40:
            text = text[: last_stop + 1]
    if text and text[-1] not in "。！？":
        text += "。"
    if text:
        return text
    return fallback or ""
