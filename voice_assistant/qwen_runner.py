from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable

import pexpect
from pexpect.exceptions import EOF, TIMEOUT, ExceptionPexpect


class QwenRunner:
    def __init__(self, config: dict):
        self.config = config
        self.project_dir = Path(config["paths"]["project_dir"])
        self.qwen = config["qwen"]

    def ask(self, image_path: str | Path, text: str) -> str:
        child = self._spawn(image_path)
        try:
            self._expect(child, "user:", int(self.qwen.get("load_timeout", 300)), "initial user prompt")
            child.sendline(text)
            self._expect(child, "robot:", 60, "robot answer prefix")
            self._expect(child, "user:", int(self.qwen.get("reply_timeout", 300)), "next user prompt")
            answer = child.before.strip()
            child.sendline("exit")
            return self._clean_answer(answer)
        finally:
            self._close_child(child)

    def ask_stream(self, image_path: str | Path, text: str, on_sentence: Callable[[str], None]) -> str:
        child = self._spawn(image_path)
        sentence_buffer = _SentenceBuffer(
            on_sentence=on_sentence,
            soft_limit=int(self.qwen.get("stream_sentence_chars", 80)),
            hard_limit=int(self.qwen.get("stream_sentence_hard_chars", 140)),
        )
        answer_parts: list[str] = []
        pending = ""
        try:
            self._expect(child, "user:", int(self.qwen.get("load_timeout", 300)), "initial user prompt")
            child.sendline(text)
            self._expect(child, "robot:", 60, "robot answer prefix")

            timeout = int(self.qwen.get("reply_timeout", 300))
            deadline = time.monotonic() + timeout
            while True:
                if time.monotonic() > deadline:
                    tail = pending[-2000:]
                    raise RuntimeError(f"Qwen demo did not reach next user prompt; last output:\n{tail}")
                try:
                    chunk = child.read_nonblocking(size=256, timeout=1)
                except TIMEOUT:
                    continue
                except EOF:
                    break
                if not chunk:
                    continue
                deadline = time.monotonic() + timeout
                pending += chunk
                prompt_idx = pending.find("user:")
                if prompt_idx >= 0:
                    before_prompt = pending[:prompt_idx]
                    if before_prompt:
                        answer_parts.append(before_prompt)
                        sentence_buffer.feed(before_prompt)
                    pending = ""
                    break
                if len(pending) > 8:
                    safe_text = pending[:-8]
                    answer_parts.append(safe_text)
                    sentence_buffer.feed(safe_text)
                    pending = pending[-8:]

            if pending:
                answer_parts.append(pending)
                sentence_buffer.feed(pending)
            sentence_buffer.finish()
            child.sendline("exit")
            return self._clean_answer("".join(answer_parts))
        finally:
            self._close_child(child)

    def _spawn(self, image_path: str | Path) -> pexpect.spawn:
        env = os.environ.copy()
        current_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{self.project_dir}:{current_ld}" if current_ld else str(self.project_dir)
        env.setdefault("RKLLM_LOG_LEVEL", "1")

        args = [
            str(self.qwen["demo"]),
            str(image_path),
            str(self.qwen["vision_model"]),
            str(self.qwen["llm_model"]),
            str(self.qwen["max_new_tokens"]),
            str(self.qwen["max_context_len"]),
            str(self.qwen["rknn_core_num"]),
            str(self.qwen["img_start"]),
            str(self.qwen["img_end"]),
            str(self.qwen["img_content"]),
        ]
        return pexpect.spawn(
            args[0],
            args[1:],
            cwd=str(self.project_dir),
            env=env,
            encoding="utf-8",
            codec_errors="ignore",
            timeout=int(self.qwen.get("load_timeout", 300)),
        )

    @staticmethod
    def _close_child(child: pexpect.spawn) -> None:
        try:
            child.close(force=True)
        except ExceptionPexpect:
            pass

    @staticmethod
    def _expect(child: pexpect.spawn, pattern: str, timeout: int, label: str) -> None:
        try:
            child.expect(pattern, timeout=timeout)
        except (TIMEOUT, EOF) as exc:
            tail = child.before[-2000:] if isinstance(child.before, str) else repr(child.before)
            raise RuntimeError(f"Qwen demo did not reach {label}; last output:\n{tail}") from exc

    @staticmethod
    def _clean_answer(answer: str) -> str:
        lines = []
        for line in answer.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == "robot:" or stripped == "user:":
                continue
            if stripped.startswith("I rkllm:"):
                continue
            if set(stripped) <= {"-"}:
                continue
            lines.append(stripped)
        return "\n".join(lines).strip()


class _SentenceBuffer:
    _END = set("。！？!?；;\n")
    _SOFT_END = set("，,、 ")

    def __init__(self, on_sentence: Callable[[str], None], soft_limit: int, hard_limit: int):
        self.on_sentence = on_sentence
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit
        self.buffer = ""

    def feed(self, text: str) -> None:
        text = _strip_ansi(text.replace("\r", ""))
        for char in text:
            self.buffer += char
            if char in self._END:
                self._emit()
            elif len(self.buffer) >= self.soft_limit and char in self._SOFT_END:
                self._emit()
            elif len(self.buffer) >= self.hard_limit:
                self._emit()

    def finish(self) -> None:
        self._emit()

    def _emit(self) -> None:
        text = self.buffer.strip()
        self.buffer = ""
        if not text:
            return
        if text in {"robot:", "user:"}:
            return
        if text.startswith("I rkllm:"):
            return
        if _is_runtime_log_fragment(text):
            return
        self.on_sentence(text)


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def _is_runtime_log_fragment(text: str) -> bool:
    lower = text.lower()
    if "per second" in lower or "tokens" in lower:
        return True
    if "rkllm" in lower or "rknn" in lower:
        return True
    return bool(re.search(r"[A-Za-z]", text) and not re.search(r"[\u4e00-\u9fff]", text))
