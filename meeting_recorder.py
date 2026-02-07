"""
Windows PC WEB会議 録音 & トランスクリプト作成ツール

機能:
  - システム音声（WASAPI ループバック）とマイク音声を同時録音
  - 録音終了後、OpenAI Whisper でローカル文字起こし
  - トランスクリプトを Markdown ファイルとして保存

必要環境: Windows 10/11, Python 3.9+
"""

import argparse
import datetime
import os
import signal
import sys
import threading
import time
import wave

import numpy as np

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000          # Whisper が期待するサンプルレート
CHANNELS = 1                 # モノラル
DTYPE = "float32"
BLOCK_SIZE = 1024            # 1 ブロックあたりのフレーム数
OUTPUT_DIR = "recordings"    # 録音ファイル保存先ディレクトリ

# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def ensure_dir(path: str) -> None:
    """ディレクトリが存在しなければ作成する。"""
    os.makedirs(path, exist_ok=True)


def timestamp_str() -> str:
    """ファイル名に使えるタイムスタンプ文字列を返す。"""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def format_timedelta(seconds: float) -> str:
    """秒数を HH:MM:SS 形式に変換する。"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# オーディオデバイス一覧表示
# ---------------------------------------------------------------------------

def list_audio_devices() -> None:
    """利用可能なオーディオデバイスを一覧表示する。"""
    import sounddevice as sd

    print("\n=== 利用可能なオーディオデバイス ===\n")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        direction = ""
        if dev["max_input_channels"] > 0:
            direction += "[入力]"
        if dev["max_output_channels"] > 0:
            direction += "[出力]"

        hostapi_name = sd.query_hostapis(dev["hostapi"])["name"]
        print(f"  {i:3d}: {dev['name']}  {direction}  ({hostapi_name})")

    print()
    defaults = sd.default.device
    print(f"  デフォルト入力デバイス: {defaults[0]}")
    print(f"  デフォルト出力デバイス: {defaults[1]}")
    print()


# ---------------------------------------------------------------------------
# WASAPI ループバックデバイスの自動検出
# ---------------------------------------------------------------------------

def find_wasapi_loopback_device() -> int | None:
    """
    WASAPI ホスト API のループバック（出力）デバイスを自動検出して
    そのインデックスを返す。見つからなければ None。
    """
    import sounddevice as sd

    hostapis = sd.query_hostapis()
    wasapi_index = None
    for i, api in enumerate(hostapis):
        if "WASAPI" in api["name"]:
            wasapi_index = i
            break

    if wasapi_index is None:
        return None

    # WASAPI のデフォルト出力デバイスをループバック録音に使う
    default_output = hostapis[wasapi_index].get("default_output_device")
    if default_output is not None and default_output >= 0:
        return default_output

    return None


# ---------------------------------------------------------------------------
# 録音クラス
# ---------------------------------------------------------------------------

class AudioRecorder:
    """
    マイク音声とシステム音声（ループバック）を同時に録音するクラス。
    """

    def __init__(
        self,
        mic_device: int | None = None,
        loopback_device: int | None = None,
        sample_rate: int = SAMPLE_RATE,
    ):
        import sounddevice as sd

        self.sample_rate = sample_rate
        self.mic_device = mic_device
        self.loopback_device = loopback_device

        self._mic_frames: list[np.ndarray] = []
        self._loopback_frames: list[np.ndarray] = []
        self._recording = False
        self._mic_stream = None
        self._loopback_stream = None

    # ----- コールバック -----

    def _mic_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[マイク] {status}", file=sys.stderr)
        if self._recording:
            self._mic_frames.append(indata.copy())

    def _loopback_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[ループバック] {status}", file=sys.stderr)
        if self._recording:
            self._loopback_frames.append(indata.copy())

    # ----- 録音制御 -----

    def start(self) -> None:
        """録音を開始する。"""
        import sounddevice as sd

        self._mic_frames.clear()
        self._loopback_frames.clear()
        self._recording = True

        # マイクストリーム
        try:
            self._mic_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                device=self.mic_device,
                callback=self._mic_callback,
            )
            self._mic_stream.start()
            print("[録音] マイク録音を開始しました。")
        except Exception as e:
            print(f"[警告] マイクの録音を開始できませんでした: {e}", file=sys.stderr)
            self._mic_stream = None

        # ループバックストリーム（システム音声）
        if self.loopback_device is not None:
            try:
                # WASAPI ループバックではデバイスのネイティブ設定を使用
                dev_info = sd.query_devices(self.loopback_device)
                loopback_channels = min(dev_info["max_input_channels"], 2) or CHANNELS
                loopback_sr = int(dev_info["default_samplerate"]) or self.sample_rate

                self._loopback_stream = sd.InputStream(
                    samplerate=loopback_sr,
                    channels=loopback_channels,
                    dtype=DTYPE,
                    blocksize=BLOCK_SIZE,
                    device=self.loopback_device,
                    callback=self._loopback_callback,
                )
                self._loopback_stream.start()
                print(
                    f"[録音] システム音声（ループバック）録音を開始しました。"
                    f"  デバイス={self.loopback_device}, SR={loopback_sr}, CH={loopback_channels}"
                )
            except Exception as e:
                print(
                    f"[警告] ループバック録音を開始できませんでした: {e}",
                    file=sys.stderr,
                )
                self._loopback_stream = None
        else:
            print("[情報] ループバックデバイスが指定されていません。マイクのみ録音します。")

    def stop(self) -> None:
        """録音を停止する。"""
        self._recording = False

        if self._mic_stream is not None:
            self._mic_stream.stop()
            self._mic_stream.close()
            self._mic_stream = None
            print("[録音] マイク録音を停止しました。")

        if self._loopback_stream is not None:
            self._loopback_stream.stop()
            self._loopback_stream.close()
            self._loopback_stream = None
            print("[録音] システム音声録音を停止しました。")

    def get_mixed_audio(self) -> np.ndarray:
        """
        マイクとループバックの録音データをミックスして返す。
        """
        mic_audio = (
            np.concatenate(self._mic_frames, axis=0)
            if self._mic_frames
            else np.zeros((0, 1), dtype=np.float32)
        )
        loopback_audio = (
            np.concatenate(self._loopback_frames, axis=0)
            if self._loopback_frames
            else np.zeros((0, 1), dtype=np.float32)
        )

        # モノラルに変換
        if mic_audio.ndim > 1 and mic_audio.shape[1] > 1:
            mic_audio = mic_audio.mean(axis=1, keepdims=True)
        if loopback_audio.ndim > 1 and loopback_audio.shape[1] > 1:
            loopback_audio = loopback_audio.mean(axis=1, keepdims=True)

        # 長さを揃える
        if mic_audio.shape[0] == 0:
            mixed = loopback_audio
        elif loopback_audio.shape[0] == 0:
            mixed = mic_audio
        else:
            min_len = min(mic_audio.shape[0], loopback_audio.shape[0])
            mixed = mic_audio[:min_len] + loopback_audio[:min_len]

        # 1D に整形
        mixed = mixed.flatten()

        # クリッピング防止
        peak = np.max(np.abs(mixed))
        if peak > 0:
            mixed = mixed / peak

        return mixed

    def get_mic_audio(self) -> np.ndarray:
        """マイク録音データだけを取得する。"""
        if not self._mic_frames:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(self._mic_frames, axis=0)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        return audio.flatten()

    def get_loopback_audio(self) -> np.ndarray:
        """ループバック録音データだけを取得する。"""
        if not self._loopback_frames:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(self._loopback_frames, axis=0)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        return audio.flatten()


# ---------------------------------------------------------------------------
# WAV 保存
# ---------------------------------------------------------------------------

def save_wav(filepath: str, audio: np.ndarray, sample_rate: int) -> None:
    """float32 の numpy 配列を 16bit PCM WAV として保存する。"""
    audio_16bit = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_16bit.tobytes())
    print(f"[保存] WAV ファイル: {filepath}")


# ---------------------------------------------------------------------------
# Whisper による文字起こし
# ---------------------------------------------------------------------------

def transcribe_audio(
    audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    model_name: str = "base",
    language: str = "ja",
) -> list[dict]:
    """
    Whisper モデルで文字起こしを行い、セグメントのリストを返す。
    各セグメント: {"start": float, "end": float, "text": str}
    """
    import whisper

    print(f"\n[文字起こし] Whisper モデル '{model_name}' を読み込み中...")
    model = whisper.load_model(model_name)

    print("[文字起こし] 文字起こし処理中... (音声の長さに応じて時間がかかります)")

    # Whisper は 16kHz float32 を期待
    if sample_rate != 16000:
        # リサンプリング
        import scipy.signal
        num_samples = int(len(audio) * 16000 / sample_rate)
        audio = scipy.signal.resample(audio, num_samples).astype(np.float32)

    result = model.transcribe(
        audio,
        language=language,
        verbose=False,
    )

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
        })

    print(f"[文字起こし] 完了 — {len(segments)} セグメントを検出しました。")
    return segments


# ---------------------------------------------------------------------------
# Markdown 出力
# ---------------------------------------------------------------------------

def segments_to_markdown(
    segments: list[dict],
    meeting_title: str = "",
    recording_start: str = "",
    duration_seconds: float = 0.0,
    wav_filename: str = "",
) -> str:
    """セグメント情報を Markdown 形式の文字列に変換する。"""
    lines: list[str] = []

    title = meeting_title or "WEB会議 トランスクリプト"
    lines.append(f"# {title}")
    lines.append("")

    # メタデータ
    lines.append("## 会議情報")
    lines.append("")
    lines.append(f"| 項目 | 内容 |")
    lines.append(f"|------|------|")
    if recording_start:
        lines.append(f"| 録音日時 | {recording_start} |")
    if duration_seconds > 0:
        lines.append(f"| 録音時間 | {format_timedelta(duration_seconds)} |")
    if wav_filename:
        lines.append(f"| 音声ファイル | `{wav_filename}` |")
    lines.append(f"| セグメント数 | {len(segments)} |")
    lines.append("")

    # トランスクリプト本文
    lines.append("## トランスクリプト")
    lines.append("")

    if not segments:
        lines.append("_(音声が検出されませんでした)_")
    else:
        for seg in segments:
            ts_start = format_timedelta(seg["start"])
            ts_end = format_timedelta(seg["end"])
            text = seg["text"]
            lines.append(f"**[{ts_start} - {ts_end}]**")
            lines.append(f"{text}")
            lines.append("")

    # フッター
    lines.append("---")
    lines.append("")
    lines.append(
        "_このトランスクリプトは OpenAI Whisper によって自動生成されました。"
        "内容に誤りがある場合があります。_"
    )
    lines.append("")

    return "\n".join(lines)


def save_markdown(filepath: str, content: str) -> None:
    """Markdown 文字列をファイルに保存する。"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[保存] Markdown ファイル: {filepath}")


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Windows WEB会議 録音 & トランスクリプト作成ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # デフォルト設定で録音 & 文字起こし
  python meeting_recorder.py

  # オーディオデバイス一覧を表示
  python meeting_recorder.py --list-devices

  # デバイスを指定して録音
  python meeting_recorder.py --mic-device 1 --loopback-device 4

  # Whisper モデルを指定 (tiny/base/small/medium/large)
  python meeting_recorder.py --model medium

  # 既存の WAV ファイルから文字起こしのみ実行
  python meeting_recorder.py --transcribe-only recordings/meeting_20260207.wav

  # 会議タイトルを指定
  python meeting_recorder.py --title "プロジェクト定例会議"
""",
    )

    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="利用可能なオーディオデバイスを一覧表示して終了",
    )
    parser.add_argument(
        "--mic-device",
        type=int,
        default=None,
        help="マイクデバイスのインデックス番号 (--list-devices で確認)",
    )
    parser.add_argument(
        "--loopback-device",
        type=int,
        default=None,
        help="ループバック(システム音声)デバイスのインデックス番号",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper モデルサイズ (デフォルト: base)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="ja",
        help="文字起こし言語コード (デフォルト: ja)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="",
        help="会議タイトル (Markdown のヘッダに使用)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=OUTPUT_DIR,
        help=f"出力先ディレクトリ (デフォルト: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--transcribe-only",
        type=str,
        default=None,
        metavar="WAV_FILE",
        help="既存の WAV ファイルから文字起こしのみ実行",
    )
    parser.add_argument(
        "--no-save-wav",
        action="store_true",
        help="WAV ファイルを保存しない（文字起こし後に削除）",
    )

    args = parser.parse_args()

    # --- デバイス一覧表示モード ---
    if args.list_devices:
        list_audio_devices()
        return

    ensure_dir(args.output_dir)
    ts = timestamp_str()

    # --- 文字起こしのみモード ---
    if args.transcribe_only:
        wav_path = args.transcribe_only
        if not os.path.isfile(wav_path):
            print(f"[エラー] ファイルが見つかりません: {wav_path}", file=sys.stderr)
            sys.exit(1)

        print(f"[読込] WAV ファイル: {wav_path}")
        import scipy.io.wavfile as wavfile

        sr, audio_data = wavfile.read(wav_path)
        # int16 → float32
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0
        # ステレオ → モノラル
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        duration = len(audio_data) / sr

        segments = transcribe_audio(
            audio_data,
            sample_rate=sr,
            model_name=args.model,
            language=args.language,
        )

        md_path = os.path.splitext(wav_path)[0] + "_transcript.md"
        md_content = segments_to_markdown(
            segments,
            meeting_title=args.title,
            recording_start="(既存ファイルから文字起こし)",
            duration_seconds=duration,
            wav_filename=os.path.basename(wav_path),
        )
        save_markdown(md_path, md_content)
        print(f"\n✅ 文字起こし完了: {md_path}")
        return

    # --- 録音 + 文字起こしモード ---
    loopback_dev = args.loopback_device
    if loopback_dev is None:
        print("[検出] WASAPI ループバックデバイスを自動検出中...")
        loopback_dev = find_wasapi_loopback_device()
        if loopback_dev is not None:
            import sounddevice as sd
            dev_info = sd.query_devices(loopback_dev)
            print(f"[検出] ループバックデバイス: {loopback_dev} ({dev_info['name']})")
        else:
            print("[警告] WASAPI ループバックデバイスが見つかりませんでした。マイクのみ録音します。")

    recorder = AudioRecorder(
        mic_device=args.mic_device,
        loopback_device=loopback_dev,
        sample_rate=SAMPLE_RATE,
    )

    recording_start_dt = datetime.datetime.now()
    recording_start_str = recording_start_dt.strftime("%Y年%m月%d日 %H:%M:%S")

    # --- Ctrl+C で停止するための設定 ---
    stop_event = threading.Event()

    def signal_handler(signum, frame):
        print("\n[停止] 録音を停止します...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    # --- 録音開始 ---
    print()
    print("=" * 60)
    print("  WEB会議 録音ツール")
    print("=" * 60)
    print()
    print(f"  録音開始: {recording_start_str}")
    print(f"  Whisper モデル: {args.model}")
    print(f"  言語: {args.language}")
    print()
    print("  ⏺  録音中... Ctrl+C で停止します")
    print()

    recorder.start()

    # 録音時間を表示しつつ停止を待つ
    try:
        while not stop_event.is_set():
            elapsed = (datetime.datetime.now() - recording_start_dt).total_seconds()
            print(f"\r  ⏺  録音中: {format_timedelta(elapsed)}", end="", flush=True)
            stop_event.wait(timeout=1.0)
    except KeyboardInterrupt:
        pass

    recorder.stop()

    recording_end_dt = datetime.datetime.now()
    duration = (recording_end_dt - recording_start_dt).total_seconds()
    print(f"\n\n[完了] 録音時間: {format_timedelta(duration)}")

    # --- 音声データ取得 ---
    mixed_audio = recorder.get_mixed_audio()
    if mixed_audio.size == 0:
        print("[エラー] 録音データがありません。", file=sys.stderr)
        sys.exit(1)

    # --- WAV 保存 ---
    wav_filename = f"meeting_{ts}.wav"
    wav_path = os.path.join(args.output_dir, wav_filename)
    save_wav(wav_path, mixed_audio, SAMPLE_RATE)

    # --- 文字起こし ---
    segments = transcribe_audio(
        mixed_audio,
        sample_rate=SAMPLE_RATE,
        model_name=args.model,
        language=args.language,
    )

    # --- Markdown 保存 ---
    md_filename = f"meeting_{ts}_transcript.md"
    md_path = os.path.join(args.output_dir, md_filename)
    md_content = segments_to_markdown(
        segments,
        meeting_title=args.title,
        recording_start=recording_start_str,
        duration_seconds=duration,
        wav_filename=wav_filename,
    )
    save_markdown(md_path, md_content)

    # --- WAV 削除（オプション） ---
    if args.no_save_wav:
        os.remove(wav_path)
        print(f"[削除] WAV ファイルを削除しました: {wav_path}")

    # --- 完了メッセージ ---
    print()
    print("=" * 60)
    print("  ✅ 録音 & 文字起こし完了!")
    print("=" * 60)
    print()
    print(f"  トランスクリプト: {md_path}")
    if not args.no_save_wav:
        print(f"  音声ファイル:     {wav_path}")
    print()


if __name__ == "__main__":
    main()
