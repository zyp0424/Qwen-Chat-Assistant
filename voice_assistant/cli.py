from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .orchestrator import VoiceAssistant
from .streaming_tts import StreamingTtsPlayer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Chinese voice-photo Qwen assistant")
    parser.add_argument("--config", default=None, help="Path to YAML config")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("record", help="Record one temporary command WAV")
    p.add_argument("--seconds", type=int, default=None)
    p.add_argument("--out", default=None)

    p = sub.add_parser("stt", help="Transcribe a WAV file")
    p.add_argument("wav")

    p = sub.add_parser("tts-stream", help="Synthesize text and stream raw PCM to speaker")
    p.add_argument("text")

    sub.add_parser("camera", help="Capture one photo")

    p = sub.add_parser("wake", help="Wait for wake keyword")
    p.add_argument("--mode", choices=("kws", "stt"), default="kws")
    p.add_argument("--timeout", type=int, default=None)

    p = sub.add_parser("kws-file", help="Detect configured wake keyword in a WAV file")
    p.add_argument("wav")

    p = sub.add_parser("ask", help="Ask Qwen from text")
    p.add_argument("text")
    p.add_argument("--image", default=None)
    p.add_argument("--force-photo", action="store_true")
    p.add_argument("--no-speak", action="store_true")
    p.add_argument("--no-play", action="store_true")

    p = sub.add_parser("once", help="Record, transcribe, ask Qwen, synthesize and play")
    p.add_argument("--seconds", type=int, default=None)
    p.add_argument("--no-speak", action="store_true")
    p.add_argument("--no-play", action="store_true")

    p = sub.add_parser("listen", help="Wait for wake keyword, then run one command")
    p.add_argument("--wake-mode", choices=("kws", "stt"), default="kws")
    p.add_argument("--wake-timeout", type=int, default=None)
    p.add_argument("--seconds", type=int, default=None)
    p.add_argument("--no-speak", action="store_true")
    p.add_argument("--no-play", action="store_true")

    p = sub.add_parser("listen-forever", help="Keep waiting for wake keyword and run commands")
    p.add_argument("--wake-mode", choices=("kws", "stt"), default="kws")
    p.add_argument("--wake-timeout", type=int, default=None)
    p.add_argument("--seconds", type=int, default=None)
    p.add_argument("--no-speak", action="store_true")
    p.add_argument("--no-play", action="store_true")

    sub.add_parser("cleanup", help="Clean temporary files")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    assistant = VoiceAssistant(load_config(args.config))

    try:
        _run_command(args, assistant)
    except KeyboardInterrupt:
        print("\n已收到 Ctrl+C，中断当前流程并退出。", file=sys.stderr)
        raise SystemExit(130) from None


def _run_command(args: argparse.Namespace, assistant: VoiceAssistant) -> None:
    if args.cmd == "record":
        out = Path(args.out) if args.out else assistant.temp_dir / "command.wav"
        wav = assistant.record_command(args.seconds)
        if out != wav:
            out.parent.mkdir(parents=True, exist_ok=True)
            wav.replace(out)
            wav = out
        print(wav)
    elif args.cmd == "stt":
        print(assistant.transcribe_wav(args.wav))
    elif args.cmd == "tts-stream":
        player = StreamingTtsPlayer(assistant.config)
        try:
            player.enqueue(args.text)
        finally:
            player.close()
    elif args.cmd == "camera":
        print(assistant.capture_photo())
    elif args.cmd == "wake":
        print(assistant.wait_for_wake(mode=args.mode, timeout=args.timeout))
    elif args.cmd == "kws-file":
        print(assistant.detect_wake_wav(args.wav))
    elif args.cmd == "ask":
        answer = assistant.run_once_from_text(
            args.text,
            image_path=args.image,
            force_photo=args.force_photo,
            speak=not args.no_speak,
            play=not args.no_play,
        )
        print(answer)
    elif args.cmd == "once":
        answer = assistant.run_once_from_microphone(
            seconds=args.seconds,
            speak=not args.no_speak,
            play=not args.no_play,
        )
        print(answer)
    elif args.cmd == "listen":
        answer = assistant.listen_once(
            wake_mode=args.wake_mode,
            wake_timeout=args.wake_timeout,
            seconds=args.seconds,
            speak=not args.no_speak,
            play=not args.no_play,
        )
        print(answer)
    elif args.cmd == "listen-forever":
        assistant.listen_forever(
            wake_mode=args.wake_mode,
            wake_timeout=args.wake_timeout,
            seconds=args.seconds,
            speak=not args.no_speak,
            play=not args.no_play,
        )
    elif args.cmd == "cleanup":
        assistant.cleanup_temp()


if __name__ == "__main__":
    main()
