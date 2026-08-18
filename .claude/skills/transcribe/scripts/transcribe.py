# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#     "openai-whisper==20250625",
#     "yt-dlp",
# ]
#
# # whisper's setup.py imports pkg_resources, which setuptools dropped in 81.
# [tool.uv.extra-build-dependencies]
# openai-whisper = ["setuptools<81"]
# ///
"""Transcribe a YouTube video (or a local audio/video file) with OpenAI Whisper.

Pipeline: yt-dlp downloads the best audio track → Whisper (running locally,
no API key) transcribes it → the transcript is written to disk in the chosen
format and printed to stdout.

`yt-dlp` is intentionally left unpinned: YouTube extraction breaks often and
the fix is almost always a newer yt-dlp. Whisper is pinned for reproducibility.

Whisper shells out to `ffmpeg` to decode audio, so ffmpeg must be on PATH.
Models are downloaded once to ~/.cache/whisper on first use.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

VALID_FORMATS = ("txt", "srt", "vtt", "tsv", "json")
VALID_MODELS = ("tiny", "base", "small", "medium", "large", "turbo")

# .../xharness/.claude/skills/transcribe/scripts/transcribe.py -> .../xharness
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT_DIR = REPO_ROOT / "output" / "transcripts"


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr, flush=True)


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def sanitize(name: str) -> str:
    """Turn a video title into a safe, tidy filename stem."""
    name = re.sub(r"[^\w\s.-]", "", name).strip()
    name = re.sub(r"[\s_]+", "_", name)
    return name[:120] or "transcript"


def fetch_audio(url: str, workdir: Path) -> tuple[Path, str]:
    """Download the best audio-only track for `url`. Returns (path, title)."""
    import yt_dlp

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(workdir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_path = Path(ydl.prepare_filename(info))
        title = info.get("title") or info.get("id") or "transcript"
    if not audio_path.exists():
        raise SystemExit(f"error: yt-dlp did not produce the expected file: {audio_path}")
    return audio_path, title


def main() -> int:
    p = argparse.ArgumentParser(
        description="Transcribe a YouTube video or local media file with local Whisper.",
    )
    p.add_argument("source", help="YouTube URL (or any yt-dlp URL), or a path to a local audio/video file")
    p.add_argument(
        "--model",
        default="small",
        choices=VALID_MODELS,
        help="Whisper model size (default: small). Bigger = more accurate + slower.",
    )
    p.add_argument(
        "--format",
        default="txt",
        choices=VALID_FORMATS,
        help="Output format (default: txt). srt/vtt carry timestamps.",
    )
    p.add_argument(
        "--output",
        help=(
            "Explicit output file path, overriding the default. Default: "
            "<repo>/output/transcripts/<title>_<YYYYMMDD-HHMMSS>.<format>"
        ),
    )
    p.add_argument(
        "--language",
        help="Force a language (ISO code, e.g. en, es). Default: Whisper auto-detects.",
    )
    p.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep the downloaded audio file next to the transcript instead of discarding it.",
    )
    args = p.parse_args()

    # Resolve where the transcript goes. An explicit --output wins; otherwise
    # everything lands in the git-ignored output/transcripts/ tree, stamped with
    # the run time so repeat runs of the same video never clobber each other.
    if args.output:
        out_path = Path(args.output).expanduser()
        out_dir = out_path.parent
        stem = out_path.stem or "transcript"
    else:
        out_dir = DEFAULT_OUT_DIR
        stem = None  # filled in after we know the title
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    with tempfile.TemporaryDirectory(prefix="transcribe-") as tmp:
        workdir = Path(tmp)

        # 1. Get an audio file.
        if is_url(args.source):
            eprint(f"[transcribe] downloading audio from {args.source} ...")
            audio_path, title = fetch_audio(args.source, workdir)
        else:
            audio_path = Path(args.source).expanduser()
            if not audio_path.exists():
                raise SystemExit(f"error: local file not found: {audio_path}")
            title = audio_path.stem

        if stem is None:
            stem = f"{sanitize(title)}_{stamp}"

        # 2. Transcribe locally with Whisper.
        import whisper
        from whisper.utils import get_writer

        eprint(f"[transcribe] loading Whisper model '{args.model}' (first run downloads it) ...")
        model = whisper.load_model(args.model)

        eprint(f"[transcribe] transcribing '{title}' ...")
        result = model.transcribe(
            str(audio_path),
            language=args.language,
            verbose=False,
        )

        # 3. Write the transcript. Whisper's writers key off the input filename's
        #    stem, so hand them a temp file named exactly how we want the output.
        writer = get_writer(args.format, str(out_dir))
        writer_input = workdir / f"{stem}.{audio_path.suffix.lstrip('.') or 'audio'}"
        writer(
            result,
            str(writer_input),
            {"max_line_width": None, "max_line_count": None, "highlight_words": False},
        )
        final_path = out_dir / f"{stem}.{args.format}"

        # 4. Optionally keep the audio.
        if args.keep_audio and is_url(args.source):
            kept = out_dir / audio_path.name
            kept.write_bytes(audio_path.read_bytes())
            eprint(f"[transcribe] kept audio: {kept}")

    detected = result.get("language")
    eprint(f"[transcribe] done. language={detected}  ->  {final_path}")

    # Print the plain-text transcript to stdout so the caller can show it.
    print(result["text"].strip())
    eprint(f"[transcribe] saved: {final_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
