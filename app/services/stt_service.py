from __future__ import annotations

import os
import time
from pathlib import Path

import speech_recognition as sr


def _resolve_ffmpeg_bin() -> Path | None:
    # __file__ is in app/services/, so we jump back out to root gest emp fastAPI
    root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        root / "ffmpeg" / "bin",
        root / "ffmpeg-2026-03-18-git-106616f13d-essentials_build" / "bin",
    ]
    for candidate in candidates:
        ffmpeg_bin = candidate / "ffmpeg.exe"
        ffprobe_bin = candidate / "ffprobe.exe"
        if ffmpeg_bin.exists() and ffprobe_bin.exists():
            return candidate
    return None


_ffmpeg_bin = _resolve_ffmpeg_bin()
if _ffmpeg_bin:
    os.environ["PATH"] = f"{_ffmpeg_bin}{os.pathsep}{os.environ.get('PATH', '')}"

from pydub import AudioSegment


class STTError(Exception):
    """Raised when speech-to-text processing fails."""


SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}


if _ffmpeg_bin:
    AudioSegment.converter = str(_ffmpeg_bin / "ffmpeg.exe")
    AudioSegment.ffprobe = str(_ffmpeg_bin / "ffprobe.exe")


def _convert_to_wav_if_needed(file_path: Path) -> Path:
    suffix = file_path.suffix.lower()
    if suffix == ".wav":
        return file_path

    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        raise STTError(f"Unsupported audio format: {suffix or 'unknown'}")

    wav_path = file_path.with_suffix(".wav")
    try:
        audio = AudioSegment.from_file(str(file_path))
        audio.export(str(wav_path), format="wav")
    except Exception as exc:
        raise STTError(
            "Unable to convert audio to WAV. Ensure FFmpeg is installed and available in PATH."
        ) from exc
    return wav_path


def speech_to_text(file_path: str) -> str:
    input_path = Path(file_path)
    if not input_path.exists() or not input_path.is_file():
        raise STTError("Audio file not found.")

    recognizer = sr.Recognizer()
    wav_path = _convert_to_wav_if_needed(input_path)

    try:
        with sr.AudioFile(str(wav_path)) as source:
            audio_data = recognizer.record(source)

        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                print(f"[stt] Recognize attempt {attempt}/3")
                transcript = recognizer.recognize_google(audio_data)
                cleaned = transcript.strip()
                if not cleaned:
                    raise STTError("Transcription produced empty text.")
                print(f"[stt] Success on attempt {attempt}. transcript_length={len(cleaned)}")
                return cleaned
            except sr.UnknownValueError as exc:
                print(f"[stt] Audio not understood on attempt {attempt}: {exc}")
                raise STTError("Speech recognition could not understand the audio.") from exc
            except sr.RequestError as exc:
                last_error = exc
                err_text = str(exc)
                print(f"[stt] Request error on attempt {attempt}: {err_text}")
                if "WinError 10053" in err_text and attempt < 3:
                    time.sleep(1.2)
                    continue
                if attempt < 3:
                    time.sleep(1.0)
                    continue
            except Exception as exc:
                last_error = exc
                err_text = str(exc)
                print(f"[stt] Unexpected error on attempt {attempt}: {err_text}")
                if "WinError 10053" in err_text and attempt < 3:
                    time.sleep(1.2)
                    continue
                if attempt < 3:
                    time.sleep(1.0)
                    continue

        if last_error and "WinError 10053" in str(last_error):
            raise STTError(
                "Speech-to-text failed after 3 attempts due to connection abort (WinError 10053). Please retry."
            ) from last_error
        raise STTError(f"Speech-to-text failed after 3 attempts: {last_error}")
    except STTError:
        raise
    except Exception as exc:
        raise STTError(f"Speech-to-text failed: {exc}") from exc
    finally:
        if wav_path != input_path and wav_path.exists():
            try:
                os.remove(wav_path)
            except OSError:
                pass