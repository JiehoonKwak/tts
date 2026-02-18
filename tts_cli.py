#!/usr/bin/env python3
"""
tts-speak: Local TTS CLI powered by Qwen3-TTS + MLX.

Usage:
    tts-speak "Hello world"
    tts-speak "안녕하세요" --lang ko
    echo "Build complete" | tts-speak --play
    cat article.txt | tts-speak --lang ko --play
    echo '{"text":"Done"}' | tts-speak --play
    tts-speak -f notes.md --lang ko
    tts-speak "Done!" --play --no-save
"""

import argparse
import json
import sys
import subprocess
import tempfile
from pathlib import Path


DEFAULT_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
DEFAULT_VOICE = "A clear, natural female voice with a moderate pace."
DEFAULT_OUTPUT = Path.home() / "Music" / "tts" / "qwen3"

LANG_ALIASES = {
    "ko": "ko",
    "korean": "ko",
    "kr": "ko",
    "en": "en",
    "english": "en",
    "ja": "ja",
    "japanese": "ja",
    "jp": "ja",
    "zh": "zh",
    "chinese": "zh",
    "cn": "zh",
}


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="tts-speak",
        description="Generate speech from text using Qwen3-TTS on Apple Silicon.",
    )
    p.add_argument("text", nargs="?", default=None, help="Text to speak")
    p.add_argument(
        "-f", "--file", type=Path, help="Read text from file (.txt, .md, .json)"
    )
    p.add_argument(
        "--lang", default="en", help="Language: en, ko, ja, zh (default: en)"
    )
    p.add_argument(
        "--voice", default=DEFAULT_VOICE, help="Voice description for VoiceDesign"
    )
    p.add_argument("--model", default=DEFAULT_MODEL, help="HuggingFace model ID")
    p.add_argument(
        "--speed", type=float, default=1.0, help="Playback speed (default: 1.0)"
    )
    p.add_argument(
        "--play", action="store_true", help="Play audio immediately via afplay"
    )
    p.add_argument(
        "--no-save", action="store_true", help="Don't save file (use with --play)"
    )
    p.add_argument("--output", type=Path, default=None, help="Output directory")
    p.add_argument("--prefix", default="tts", help="Output filename prefix")
    p.add_argument(
        "--json-key",
        default=None,
        help="JSON key to extract text from (default: tries 'message', 'text', 'content')",
    )
    p.add_argument("--max-tokens", type=int, default=2048, help="Max generation tokens")
    p.add_argument("--verbose", action="store_true", help="Show generation details")
    return p.parse_args(argv)


def _stdin_is_pipe():
    """Check if stdin has piped data (not a terminal)."""
    return not sys.stdin.isatty()


def _extract_json_text(raw, key=None):
    """Try to extract text from JSON. Returns None if not JSON."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    if key:
        return data.get(key, "")

    # Try common keys in priority order
    for k in ("message", "text", "content", "body", "description"):
        if k in data and isinstance(data[k], str):
            return data[k]

    return None


def resolve_text(args):
    """Get text from argument, file, or stdin. Auto-detects JSON in all modes."""

    raw = None

    # Priority 1: explicit file
    if args.file:
        p = args.file.expanduser()
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)
        raw = p.read_text(encoding="utf-8").strip()

    # Priority 2: positional argument
    elif args.text:
        raw = args.text

    # Priority 3: stdin (auto-detect pipe, no flag needed)
    elif _stdin_is_pipe():
        raw = sys.stdin.read().strip()

    else:
        print(
            "Error: provide text as argument, -f <file>, or pipe via stdin",
            file=sys.stderr,
        )
        sys.exit(1)

    if not raw:
        print("Error: empty input", file=sys.stderr)
        sys.exit(1)

    # Auto-detect JSON in any input mode
    json_text = _extract_json_text(raw, key=args.json_key)
    if json_text is not None:
        if args.verbose:
            print("Parsed JSON, extracted text", file=sys.stderr)
        return json_text

    return raw


def generate(args, text):
    """Run mlx_audio TTS generation."""
    lang = LANG_ALIASES.get(args.lang.lower(), args.lang)

    if args.no_save and args.play:
        output_dir = Path(tempfile.mkdtemp())
    else:
        output_dir = args.output or DEFAULT_OUTPUT
        output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "mlx_audio.tts.generate",
        "--model",
        args.model,
        "--text",
        text,
        "--lang_code",
        lang,
        "--instruct",
        args.voice,
        "--speed",
        str(args.speed),
        "--output_path",
        str(output_dir),
        "--file_prefix",
        args.prefix,
        "--max_tokens",
        str(args.max_tokens),
    ]

    if args.verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Find generated file
    wav_files = sorted(
        output_dir.glob(f"{args.prefix}_*.wav"), key=lambda p: p.stat().st_mtime
    )
    if not wav_files:
        print("Error: no audio file generated", file=sys.stderr)
        sys.exit(1)

    output_file = wav_files[-1]

    if args.play:
        subprocess.run(["afplay", str(output_file)])

    if args.no_save and args.play:
        output_file.unlink(missing_ok=True)
        output_dir.rmdir()
    else:
        print(str(output_file))

    return output_file


def main():
    args = parse_args()
    text = resolve_text(args)

    if not text:
        print("Error: empty text", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Text: {text}", file=sys.stderr)
        print(f"Lang: {args.lang}", file=sys.stderr)
        print(f"Voice: {args.voice}", file=sys.stderr)

    generate(args, text)


if __name__ == "__main__":
    main()
