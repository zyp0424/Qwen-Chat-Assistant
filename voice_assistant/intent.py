from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    need_photo: bool
    qwen_text: str


class IntentRouter:
    def __init__(self, photo_keywords: list[str], image_prefix_trigger: str, image_prefix: str):
        self.photo_keywords = tuple(photo_keywords)
        self.image_prefix_trigger = image_prefix_trigger
        self.image_prefix = image_prefix

    @classmethod
    def from_config(cls, config: dict) -> "IntentRouter":
        intent = config["intent"]
        return cls(
            photo_keywords=intent["photo_keywords"],
            image_prefix_trigger=intent["image_prefix_trigger"],
            image_prefix=intent["image_prefix"],
        )

    def analyze(self, text: str) -> Intent:
        normalized = text.strip()
        need_photo = any(keyword in normalized for keyword in self.photo_keywords)
        if self.image_prefix_trigger in normalized and not normalized.startswith(self.image_prefix):
            normalized = f"{self.image_prefix}{normalized}"
        return Intent(need_photo=need_photo, qwen_text=normalized)
