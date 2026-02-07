from __future__ import annotations

import dataclasses
import datetime as dt
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

from meeting_transcriber.recorder import RecordingOutputs


@dataclasses.dataclass(frozen=True)
class TranscribeConfig:
    model: str = "small"
    language: str = "ja"  # "auto" で自動判定
    device: str = "auto"  # "cpu" or "cuda" or "auto"
    compute_type: str = "auto"  # "int8" など
    beam_size: int = 5
    vad_filter: bool = True


def _fmt_ts(seconds: float) -> str:
    # mm:ss 〜 hh:mm:ss
    s = max(0.0, float(seconds))
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def _load_model(cfg: TranscribeConfig) -> WhisperModel:
    # device/compute_typeは環境差が大きいためautoを基本にする
    return WhisperModel(cfg.model, device=cfg.device, compute_type=cfg.compute_type)


def _transcribe_one(
    model: WhisperModel,
    audio_path: Path,
    cfg: TranscribeConfig,
) -> tuple[list[str], str, float]:
    language = None if cfg.language.strip().lower() == "auto" else cfg.language
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=cfg.beam_size,
        vad_filter=cfg.vad_filter,
        word_timestamps=False,
    )

    lines: list[str] = []
    seg_count = 0
    for seg in segments:
        seg_count += 1
        st = _fmt_ts(seg.start)
        et = _fmt_ts(seg.end)
        text = (seg.text or "").strip()
        if not text:
            continue
        lines.append(f"- **{st} - {et}** {text}")

    if seg_count == 0:
        lines.append("- (セグメントが生成されませんでした。音声が無音/小音量の可能性があります。)")

    return lines, info.language, float(info.language_probability)


def transcribe_to_markdown(
    audio_path: Path,
    md_path: Path,
    cfg: TranscribeConfig,
    extra_audio: Optional[RecordingOutputs] = None,
) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)

    model = _load_model(cfg)
    seg_lines, detected_lang, detected_prob = _transcribe_one(model, audio_path, cfg)

    now = dt.datetime.now(dt.timezone.utc).astimezone()
    lines: list[str] = []
    lines.append("# Transcript")
    lines.append("")
    lines.append(f"- Generated at: {now.isoformat()}")
    lines.append(f"- Audio: `{audio_path}`")
    if extra_audio is not None:
        if extra_audio.system_wav:
            lines.append(f"- System audio: `{extra_audio.system_wav}`")
        if extra_audio.mic_wav:
            lines.append(f"- Mic audio: `{extra_audio.mic_wav}`")
        lines.append(f"- Recording info: `{extra_audio.info_txt}`")
    lines.append(f"- Detected language: `{detected_lang}` (prob={detected_prob:.2f})")
    lines.append("")
    lines.append("## セグメント")
    lines.append("")
    lines.extend(seg_lines)

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def transcribe_recording_outputs_to_markdown(
    outputs: RecordingOutputs,
    md_path: Path,
    cfg: TranscribeConfig,
) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    model = _load_model(cfg)

    now = dt.datetime.now(dt.timezone.utc).astimezone()
    lines: list[str] = []
    lines.append("# Transcript")
    lines.append("")
    lines.append(f"- Generated at: {now.isoformat()}")
    lines.append(f"- Recording info: `{outputs.info_txt}`")
    if outputs.system_wav:
        lines.append(f"- System audio: `{outputs.system_wav}`")
    if outputs.mic_wav:
        lines.append(f"- Mic audio: `{outputs.mic_wav}`")
    lines.append("")

    any_transcribed = False
    if outputs.system_wav and outputs.system_wav.exists():
        any_transcribed = True
        seg_lines, lang, prob = _transcribe_one(model, outputs.system_wav, cfg)
        lines.append("## システム音 (system)")
        lines.append("")
        lines.append(f"- Detected language: `{lang}` (prob={prob:.2f})")
        lines.append("")
        lines.extend(seg_lines)
        lines.append("")

    if outputs.mic_wav and outputs.mic_wav.exists():
        any_transcribed = True
        seg_lines, lang, prob = _transcribe_one(model, outputs.mic_wav, cfg)
        lines.append("## マイク (mic)")
        lines.append("")
        lines.append(f"- Detected language: `{lang}` (prob={prob:.2f})")
        lines.append("")
        lines.extend(seg_lines)
        lines.append("")

    if not any_transcribed:
        raise FileNotFoundError("文字起こし対象の音声ファイルが見つかりませんでした。")

    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

