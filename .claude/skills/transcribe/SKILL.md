---
name: transcribe
description: Transcribe a YouTube video (or local audio/video file) to text using OpenAI Whisper running locally — no API key required. Downloads the audio track with yt-dlp, transcribes with Whisper, and writes a txt/srt/vtt/json transcript to disk. Use whenever the user wants a transcript, subtitles, captions, or the text of a video or podcast.
argument-hint: "<youtube-url|file> [--model tiny|base|small|medium|large|turbo] [--format txt|srt|vtt|tsv|json] [--output path] [--language en]"
allowed-tools:
  - Bash
---

Transcribe the video or audio source given in $ARGUMENTS.

Runs OpenAI Whisper **locally** — no API key and no per-minute cost. Requires
`ffmpeg` on PATH (Whisper uses it to decode audio); `brew install ffmpeg` if missing.

Run from the repo root:

```bash
uv run .claude/skills/transcribe/scripts/transcribe.py <youtube-url|file> [--model <size>] [--format <fmt>] [--output <path>] [--language <code>] [--keep-audio]
```

Arguments:
- `<source>` — required, a YouTube URL (any yt-dlp-supported URL works) or a path to a local audio/video file
- `--model` — Whisper model size: `tiny`, `base`, `small` (default), `medium`, `large`, `turbo`. Bigger is more accurate and slower.
- `--format` — output format: `txt` (default), `srt`, `vtt`, `tsv`, `json`. Use `srt`/`vtt` when the user wants subtitles or timestamps.
- `--output` — explicit output file path, overriding the default location below
- `--language` — force an ISO language code (e.g. `en`, `es`); omit to let Whisper auto-detect
- `--keep-audio` — also keep the downloaded audio file alongside the transcript

Output location:
- By default transcripts are written to `output/transcripts/` at the repo root,
  named `<video-title>_<YYYYMMDD-HHMMSS>.<format>`. That path is resolved relative
  to the repo, not the current working directory, so it lands in the same place
  wherever the command is run from. `/output/` is git-ignored.
- The timestamp means re-transcribing the same video never overwrites an earlier run.
- Pass `--output <path>` to write somewhere else; an explicit path is used verbatim
  (no timestamp is appended).

Behavior notes:
- The plain-text transcript is printed to stdout; progress goes to stderr.
- The first run with a given model downloads it to `~/.cache/whisper` (~150MB for
  `small`, ~3GB for `large`). Later runs reuse the cached model.
- Transcription is CPU-bound and roughly real-time-ish on `small`; a long video can
  take several minutes. Prefer `small` unless the user asks for higher accuracy.

Report the output file path on success. For a short video, also show the transcript
in the conversation; for a long one, summarize it and point to the file rather than
dumping the whole thing. If `ffmpeg` is missing, tell the user to run `brew install ffmpeg`.
If `uv` is not installed, tell the user to run `brew install uv`.
