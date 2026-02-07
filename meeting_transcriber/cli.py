import argparse
from pathlib import Path

from meeting_transcriber.recorder import (
    RecordingConfig,
    list_devices_human,
    record_audio,
)
from meeting_transcriber.transcriber import (
    TranscribeConfig,
    transcribe_recording_outputs_to_markdown,
    transcribe_to_markdown,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="meeting_transcriber",
        description="Windows PCのWeb会議を録音し、文字起こし(Markdown)を生成します。",
    )
    sub = p.add_subparsers(dest="cmd", required=False)

    p.add_argument(
        "--list-devices",
        action="store_true",
        help="録音デバイス一覧を表示して終了します。",
    )

    rec = sub.add_parser("record", help="録音のみ実行します。")
    rec.add_argument("--out", type=Path, default=Path("output"), help="出力ディレクトリ")
    rec.add_argument(
        "--system-device",
        type=int,
        default=None,
        help="システム音(ループバック)に使うデバイスindex(未指定なら既定の出力デバイス)",
    )
    rec.add_argument(
        "--mic-device",
        type=int,
        default=None,
        help="マイクに使うデバイスindex(未指定なら既定の入力デバイス)",
    )
    rec.add_argument(
        "--no-system",
        action="store_true",
        help="システム音(ループバック)の録音を無効化します。",
    )
    rec.add_argument(
        "--no-mic",
        action="store_true",
        help="マイク録音を無効化します。",
    )
    rec.add_argument(
        "--samplerate",
        type=int,
        default=None,
        help="録音サンプルレート(Hz)。未指定ならデバイス既定値。",
    )
    rec.add_argument(
        "--channels",
        type=int,
        default=1,
        help="録音チャンネル数(基本は1を推奨)。",
    )
    rec.add_argument(
        "--duration",
        type=float,
        default=None,
        help="録音秒数。未指定の場合はEnter入力で停止。",
    )

    tr = sub.add_parser("transcribe", help="文字起こしのみ実行します。")
    tr.add_argument("--audio", type=Path, required=True, help="入力音声ファイル(wavなど)")
    tr.add_argument("--out", type=Path, required=True, help="出力Markdownファイル")
    tr.add_argument(
        "--model",
        type=str,
        default="small",
        help="Whisperモデル名(base/small/medium/large-v3など)",
    )
    tr.add_argument(
        "--language",
        type=str,
        default="ja",
        help="言語コード(例: ja, en)。autoにすると自動判定。",
    )

    rt = sub.add_parser("run", help="録音→文字起こしまで一括実行します。")
    rt.add_argument("--out", type=Path, default=Path("output"), help="出力ディレクトリ")
    rt.add_argument("--system-device", type=int, default=None)
    rt.add_argument("--mic-device", type=int, default=None)
    rt.add_argument("--no-system", action="store_true")
    rt.add_argument("--no-mic", action="store_true")
    rt.add_argument("--samplerate", type=int, default=None)
    rt.add_argument("--channels", type=int, default=1)
    rt.add_argument("--duration", type=float, default=None)
    rt.add_argument("--model", type=str, default="small")
    rt.add_argument("--language", type=str, default="ja")

    return p


def main(argv: list[str] | None = None) -> int:
    p = _build_parser()
    args = p.parse_args(argv)

    if args.list_devices:
        print(list_devices_human())
        return 0

    cmd = args.cmd or "run"

    if cmd == "record":
        cfg = RecordingConfig(
            out_dir=args.out,
            system_device=args.system_device,
            mic_device=args.mic_device,
            enable_system=not args.no_system,
            enable_mic=not args.no_mic,
            samplerate=args.samplerate,
            channels=args.channels,
            duration=args.duration,
        )
        record_audio(cfg)
        return 0

    if cmd == "transcribe":
        tcfg = TranscribeConfig(model=args.model, language=args.language)
        transcribe_to_markdown(audio_path=args.audio, md_path=args.out, cfg=tcfg)
        return 0

    if cmd == "run":
        cfg = RecordingConfig(
            out_dir=args.out,
            system_device=args.system_device,
            mic_device=args.mic_device,
            enable_system=not args.no_system,
            enable_mic=not args.no_mic,
            samplerate=args.samplerate,
            channels=args.channels,
            duration=args.duration,
        )
        outputs = record_audio(cfg)

        tcfg = TranscribeConfig(model=args.model, language=args.language)
        md = outputs.out_dir / "transcript.md"
        transcribe_recording_outputs_to_markdown(outputs=outputs, md_path=md, cfg=tcfg)
        print(f"Wrote {md}")
        return 0

    p.print_help()
    return 2

