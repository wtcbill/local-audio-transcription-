#!/usr/bin/env python
"""Reliable local transcription helper for Chinese monologues and Japanese dialogue."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from datetime import datetime
from pathlib import Path


KNOWN_FFMPEG = Path(r"C:\Program Files (x86)\bililive\ugc_assistant\2.3.0.1097\ffmpeg.exe")
KNOWN_FFPROBE = Path(r"C:\Program Files (x86)\bililive\ugc_assistant\2.3.0.1097\ffprobe.exe")


def fmt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:05.2f}"
    return f"{minutes:02d}:{sec:05.2f}"


def find_tool(explicit: str | None, name: str, known_path: Path) -> str:
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return str(path.resolve())
        discovered = shutil.which(explicit)
        if discovered:
            return discovered
        raise FileNotFoundError(f"Cannot find {name}: {explicit}")
    discovered = shutil.which(name)
    if discovered:
        return discovered
    if known_path.is_file():
        return str(known_path)
    raise FileNotFoundError(
        f"Cannot find {name}. Install ffmpeg or pass --{name} with its full path."
    )


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "unknown error").strip()
        raise RuntimeError(f"Command failed: {command[0]}\n{detail}") from exc


def inspect_audio(ffprobe: str, audio: Path) -> dict:
    result = run([
        ffprobe,
        "-v", "error",
        "-show_entries",
        "format=duration,size,bit_rate,format_name:stream=index,codec_type,codec_name,sample_rate,channels",
        "-of", "json",
        str(audio),
    ])
    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    try:
        duration = float(fmt.get("duration", 0.0))
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        raise ValueError("The audio duration is missing or zero; the file may be invalid.")
    data["resolved_duration_seconds"] = duration
    return data


def normalize_audio(ffmpeg: str, source: Path, target: Path) -> None:
    run([
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        "-map", "0:a:0",
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        "-vn", str(target),
    ])


def split_pcm_wav(source: Path, target_dir: Path, chunk_seconds: int) -> list[tuple[Path, float, float]]:
    """Split normalized PCM WAV exactly, returning path, offset, and duration."""
    with wave.open(str(source), "rb") as wav_in:
        params = wav_in.getparams()
        rate = wav_in.getframerate()
        if params.nchannels != 1 or params.sampwidth != 2 or rate != 16000:
            raise ValueError("Internal error: normalized WAV is not 16 kHz mono PCM16.")
        frames_per_chunk = chunk_seconds * rate
        chunks = []
        frame_offset = 0
        index = 0
        while frame_offset < params.nframes:
            frame_count = min(frames_per_chunk, params.nframes - frame_offset)
            frames = wav_in.readframes(frame_count)
            chunk_path = target_dir / f"chunk_{index:04d}.wav"
            with wave.open(str(chunk_path), "wb") as wav_out:
                wav_out.setparams(params)
                wav_out.writeframes(frames)
            chunks.append((chunk_path, frame_offset / rate, frame_count / rate))
            frame_offset += frame_count
            index += 1
    return chunks


def resolve_runtime(device_arg: str, compute_arg: str) -> tuple[str, str]:
    device = device_arg
    if device == "auto":
        try:
            import ctranslate2
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    compute = compute_arg
    if compute == "auto":
        compute = "float16" if device == "cuda" else "int8"
    return device, compute


def safe_stem(path: Path) -> str:
    stem = re.sub(r"[^\w.-]+", "_", path.stem, flags=re.UNICODE).strip("_.")
    return stem[:80] or "audio"


def unique_base(out_dir: Path, audio: Path, mode: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = out_dir / f"{safe_stem(audio)}_{mode}_{timestamp}"
    candidate = base
    counter = 2
    while candidate.with_suffix(".json").exists() or candidate.with_suffix(".txt").exists():
        candidate = out_dir / f"{base.name}_{counter}"
        counter += 1
    return candidate


def optional_float(value) -> float | None:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def transcribe_chunks(model, chunks, args, language: str) -> tuple[list[dict], list[dict]]:
    """Transcribe every chunk and return complete results only after a successful pass."""
    rows: list[dict] = []
    chunk_results: list[dict] = []
    for index, (chunk_path, offset, duration) in enumerate(chunks):
        kwargs = {
            "beam_size": 5,
            "condition_on_previous_text": args.condition_on_previous_text,
            "temperature": 0.0,
            "vad_filter": args.vad,
            "word_timestamps": args.word_timestamps,
        }
        if language != "auto":
            kwargs["language"] = language
        if args.initial_prompt:
            kwargs["initial_prompt"] = args.initial_prompt
        segments, info = model.transcribe(str(chunk_path), **kwargs)
        chunk_rows = 0
        # Iterating segments can be the first operation that loads CUDA DLLs.
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            row = {
                "start": round(offset + seg.start, 3),
                "end": round(offset + seg.end, 3),
                "text": text,
                "avg_logprob": optional_float(getattr(seg, "avg_logprob", None)),
                "no_speech_prob": optional_float(getattr(seg, "no_speech_prob", None)),
            }
            if args.word_timestamps and getattr(seg, "words", None):
                row["words"] = [
                    {
                        "start": round(offset + word.start, 3),
                        "end": round(offset + word.end, 3),
                        "word": word.word,
                        "probability": optional_float(getattr(word, "probability", None)),
                    }
                    for word in seg.words
                ]
            rows.append(row)
            chunk_rows += 1
        chunk_results.append({
            "index": index,
            "offset_seconds": round(offset, 3),
            "duration_seconds": round(duration, 3),
            "detected_language": getattr(info, "language", None),
            "language_probability": optional_float(getattr(info, "language_probability", None)),
            "segments": chunk_rows,
        })
    return rows, chunk_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe audio locally with faster-whisper.")
    parser.add_argument("--audio", required=True, help="Input audio path.")
    parser.add_argument("--out-dir", help="Output directory; defaults to the audio file's directory.")
    parser.add_argument(
        "--mode", choices=("auto", "zh-monologue", "ja-dialogue"), default="auto",
        help="Preset language and output intent."
    )
    parser.add_argument("--model", default="medium", help="Whisper model name or local model path.")
    parser.add_argument("--language", default=None, help="Override language, for example zh, ja, en, or auto.")
    parser.add_argument("--chunk-seconds", type=int, default=300, help="Exact PCM chunk length; 0 disables splitting.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--compute-type", default="auto", help="auto, int8, float16, or another CTranslate2 type.")
    parser.add_argument("--ffmpeg", help="ffmpeg executable name or full path.")
    parser.add_argument("--ffprobe", help="ffprobe executable name or full path.")
    parser.add_argument("--vad", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--condition-on-previous-text", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--word-timestamps", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--initial-prompt", help="Optional names or specialist terms expected in the audio.")
    parser.add_argument("--inspect-only", action="store_true", help="Inspect audio without loading Whisper.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audio = Path(args.audio).expanduser().resolve()
    if not audio.is_file():
        raise FileNotFoundError(f"Audio file does not exist: {audio}")
    if args.chunk_seconds < 0:
        raise ValueError("--chunk-seconds must be zero or greater.")

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else audio.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_tool(args.ffmpeg, "ffmpeg", KNOWN_FFMPEG)
    ffprobe = find_tool(args.ffprobe, "ffprobe", KNOWN_FFPROBE)
    source_info = inspect_audio(ffprobe, audio)

    language = args.language
    if language is None:
        language = {"zh-monologue": "zh", "ja-dialogue": "ja"}.get(args.mode, "auto")
    if args.inspect_only:
        print(json.dumps({"audio": str(audio), "ffmpeg": ffmpeg, "ffprobe": ffprobe, "inspection": source_info}, ensure_ascii=False, indent=2))
        return 0

    from faster_whisper import WhisperModel

    device, compute_type = resolve_runtime(args.device, args.compute_type)
    runtime_fallback = None
    try:
        model = WhisperModel(args.model, device=device, compute_type=compute_type)
    except Exception as exc:
        if args.device != "auto" or device == "cpu":
            raise
        print("GPU initialization failed; retrying with CPU int8.", file=sys.stderr)
        runtime_fallback = {
            "stage": "model_initialization",
            "from_device": device,
            "to_device": "cpu",
            "reason": str(exc),
        }
        device, compute_type = "cpu", "int8"
        model = WhisperModel(args.model, device=device, compute_type=compute_type)

    with tempfile.TemporaryDirectory(prefix="local_audio_transcription_") as temp_name:
        temp_dir = Path(temp_name)
        normalized = temp_dir / "normalized.wav"
        normalize_audio(ffmpeg, audio, normalized)
        if args.chunk_seconds:
            chunks = split_pcm_wav(normalized, temp_dir, args.chunk_seconds)
        else:
            chunks = [(normalized, 0.0, source_info["resolved_duration_seconds"])]
        try:
            rows, chunk_results = transcribe_chunks(model, chunks, args, language)
        except Exception as exc:
            if args.device != "auto" or device == "cpu":
                raise
            print("GPU transcription failed; restarting from the beginning with CPU int8.", file=sys.stderr)
            runtime_fallback = {
                "stage": "transcription",
                "from_device": device,
                "to_device": "cpu",
                "reason": str(exc),
            }
            del model
            device, compute_type = "cpu", "int8"
            model = WhisperModel(args.model, device=device, compute_type=compute_type)
            rows, chunk_results = transcribe_chunks(model, chunks, args, language)

    base = unique_base(out_dir, audio, args.mode)
    txt_path = base.with_suffix(".txt")
    json_path = base.with_suffix(".json")
    lines = [f"[{fmt_time(row['start'])} - {fmt_time(row['end'])}] {row['text']}" for row in rows]
    txt_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    payload = {
        "schema_version": 2,
        "audio": str(audio),
        "mode": args.mode,
        "requested_language": language,
        "model": args.model,
        "device": device,
        "compute_type": compute_type,
        "runtime_fallback": runtime_fallback,
        "chunk_seconds": args.chunk_seconds,
        "vad": args.vad,
        "condition_on_previous_text": args.condition_on_previous_text,
        "source_inspection": source_info,
        "chunks": chunk_results,
        "segments": rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "segments": len(rows),
        "duration_seconds": source_info["resolved_duration_seconds"],
        "mode": args.mode,
        "language": language,
        "device": device,
        "raw_transcript": str(txt_path),
        "metadata": str(json_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
