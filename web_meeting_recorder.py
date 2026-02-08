#!/usr/bin/env python3
"""
WEB会議 全音声録音プログラム (Windows WASAPI Loopback対応)

Windows PCでWEB会議を行う際、マイク音声（自分の発話）と
システム音声（相手の発話 / スピーカー出力）の両方を録音し、
1つのWAVファイルにミキシングして保存するプログラムです。

必要条件:
  - Windows 10 / 11
  - Python 3.8+
  - sounddevice, soundfile, numpy

使い方:
  python web_meeting_recorder.py
  python web_meeting_recorder.py --output-dir ./recordings --sample-rate 48000
  python web_meeting_recorder.py --list-devices
"""

import argparse
import datetime
import os
import sys
import threading
import time
import queue
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("[エラー] numpy がインストールされていません。")
    print("  pip install numpy")
    sys.exit(1)

try:
    import sounddevice as sd
except ImportError:
    print("[エラー] sounddevice がインストールされていません。")
    print("  pip install sounddevice")
    sys.exit(1)

try:
    import soundfile as sf
except ImportError:
    print("[エラー] soundfile がインストールされていません。")
    print("  pip install soundfile")
    sys.exit(1)


# =============================================================================
# 定数
# =============================================================================
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 1  # モノラル
DEFAULT_BLOCKSIZE = 1024
DEFAULT_OUTPUT_DIR = "./recordings"
VU_METER_WIDTH = 40


# =============================================================================
# ユーティリティ関数
# =============================================================================
def get_timestamp_filename(prefix: str = "recording", ext: str = "wav") -> str:
    """録音開始日時を含むファイル名を生成する"""
    now = datetime.datetime.now()
    return f"{prefix}_{now.strftime('%Y-%m-%d_%H-%M-%S')}.{ext}"


def amplitude_to_db(amplitude: float) -> float:
    """振幅をdBに変換する"""
    if amplitude <= 0:
        return -100.0
    return 20 * np.log10(amplitude)


def render_vu_meter(level: float, width: int = VU_METER_WIDTH) -> str:
    """VUメーター風の表示文字列を生成する"""
    # level: 0.0 ~ 1.0 にクリッピング
    level = max(0.0, min(1.0, level))
    filled = int(level * width)
    bar = "█" * filled + "░" * (width - filled)
    db = amplitude_to_db(level)
    return f"|{bar}| {db:>6.1f} dB"


def format_duration(seconds: float) -> str:
    """秒数をHH:MM:SS形式にフォーマットする"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def check_disk_space(path: str, min_mb: int = 100) -> bool:
    """ディスクの空き容量をチェックする"""
    try:
        import shutil
        usage = shutil.disk_usage(path)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < min_mb:
            print(f"[警告] ディスク空き容量が少なくなっています: {free_mb:.0f} MB")
            return False
        return True
    except Exception:
        return True  # チェックできない場合はスキップ


# =============================================================================
# デバイス管理
# =============================================================================
def list_audio_devices():
    """利用可能なオーディオデバイスを一覧表示する"""
    devices = sd.query_devices()
    print("\n" + "=" * 70)
    print("  利用可能なオーディオデバイス一覧")
    print("=" * 70)

    print("\n--- 入力デバイス (マイク) ---")
    input_devices = []
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            input_devices.append(i)
            hostapi = sd.query_hostapis(dev["hostapi"])["name"]
            default_mark = " ★" if i == sd.default.device[0] else ""
            print(f"  [{i:>3}] {dev['name']:<45} "
                  f"(入力ch: {dev['max_input_channels']}, "
                  f"API: {hostapi}){default_mark}")

    print("\n--- 出力デバイス (スピーカー) ---")
    output_devices = []
    for i, dev in enumerate(devices):
        if dev["max_output_channels"] > 0:
            output_devices.append(i)
            hostapi = sd.query_hostapis(dev["hostapi"])["name"]
            default_mark = " ★" if i == sd.default.device[1] else ""
            print(f"  [{i:>3}] {dev['name']:<45} "
                  f"(出力ch: {dev['max_output_channels']}, "
                  f"API: {hostapi}){default_mark}")

    print("\n  ★ = デフォルトデバイス")
    print("=" * 70)
    return input_devices, output_devices


def find_wasapi_loopback_device(output_device_index: int):
    """
    指定された出力デバイスに対応するWASAPIループバックデバイスを探す。
    sounddeviceではWASAPIホストAPIのデバイスでloopback=Trueを指定することで
    システム音声をキャプチャできる。
    """
    devices = sd.query_devices()
    target_dev = devices[output_device_index]

    # WASAPIホストAPIのインデックスを検索
    wasapi_hostapi_idx = None
    for i, api in enumerate(sd.query_hostapis()):
        if "WASAPI" in api["name"]:
            wasapi_hostapi_idx = i
            break

    if wasapi_hostapi_idx is None:
        return None, "WASAPIホストAPIが見つかりません。Windows環境で実行してください。"

    # 同じ名前のWASAPIデバイスを探す
    target_name = target_dev["name"]
    for i, dev in enumerate(devices):
        if (dev["hostapi"] == wasapi_hostapi_idx
                and dev["max_output_channels"] > 0
                and target_name in dev["name"]):
            return i, None

    # 見つからない場合、WASAPIのデフォルト出力デバイスを使う
    for i, dev in enumerate(devices):
        if (dev["hostapi"] == wasapi_hostapi_idx
                and dev["max_output_channels"] > 0):
            return i, None

    return None, "WASAPIループバック可能なデバイスが見つかりません。"


def find_wasapi_input_device(input_device_index: int):
    """
    指定された入力デバイスに対応するWASAPIホストAPIのデバイスを探す。
    """
    devices = sd.query_devices()
    target_dev = devices[input_device_index]

    wasapi_hostapi_idx = None
    for i, api in enumerate(sd.query_hostapis()):
        if "WASAPI" in api["name"]:
            wasapi_hostapi_idx = i
            break

    if wasapi_hostapi_idx is None:
        return input_device_index  # WASAPIが無い場合はそのまま返す

    target_name = target_dev["name"]
    for i, dev in enumerate(devices):
        if (dev["hostapi"] == wasapi_hostapi_idx
                and dev["max_input_channels"] > 0
                and target_name in dev["name"]):
            return i

    return input_device_index  # 見つからなければそのまま返す


# =============================================================================
# AudioRecorder クラス
# =============================================================================
class AudioRecorder:
    """
    WEB会議の全音声を録音するメインクラス。
    マイク入力とシステム音声（WASAPIループバック）を同時にキャプチャし、
    ミキシングしてWAVファイルに書き出す。
    """

    def __init__(
        self,
        mic_device: int = None,
        speaker_device: int = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        blocksize: int = DEFAULT_BLOCKSIZE,
        output_dir: str = DEFAULT_OUTPUT_DIR,
    ):
        self.mic_device = mic_device
        self.speaker_device = speaker_device
        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        self.output_dir = output_dir

        # 状態管理
        self.is_recording = False
        self.start_time = None

        # 音声データキュー (スレッド間通信)
        self.mic_queue = queue.Queue()
        self.speaker_queue = queue.Queue()

        # 音量レベル (表示用)
        self.mic_level = 0.0
        self.speaker_level = 0.0

        # ストリーム
        self.mic_stream = None
        self.speaker_stream = None

        # 書き込みスレッド
        self.writer_thread = None

        # 出力ファイル
        self.output_file = None
        self.output_path = None

    def _mic_callback(self, indata, frames, time_info, status):
        """マイク入力のコールバック"""
        if status:
            print(f"\n[マイク警告] {status}")
        if self.is_recording:
            data = indata.copy()
            self.mic_queue.put(data)
            # RMSレベルを更新
            self.mic_level = float(np.sqrt(np.mean(data ** 2)))

    def _speaker_callback(self, indata, frames, time_info, status):
        """スピーカー（ループバック）のコールバック"""
        if status:
            print(f"\n[スピーカー警告] {status}")
        if self.is_recording:
            data = indata.copy()
            self.speaker_queue.put(data)
            # RMSレベルを更新
            self.speaker_level = float(np.sqrt(np.mean(data ** 2)))

    def _writer_loop(self):
        """
        録音データをファイルに書き出すスレッド。
        マイクとスピーカーの音声データをミキシングしてストリーミング書き込み。
        """
        mic_buffer = np.zeros((self.blocksize, self.channels), dtype=np.float32)
        speaker_buffer = np.zeros((self.blocksize, self.channels), dtype=np.float32)

        while self.is_recording or not self.mic_queue.empty() or not self.speaker_queue.empty():
            has_data = False

            # マイクデータの取得
            try:
                mic_data = self.mic_queue.get(timeout=0.05)
                # チャンネル数の調整
                if mic_data.ndim == 1:
                    mic_data = mic_data.reshape(-1, 1)
                if mic_data.shape[1] != self.channels:
                    if self.channels == 1:
                        mic_data = np.mean(mic_data, axis=1, keepdims=True)
                    else:
                        mic_data = np.repeat(mic_data[:, :1], self.channels, axis=1)
                mic_buffer = mic_data
                has_data = True
            except queue.Empty:
                mic_buffer = np.zeros((self.blocksize, self.channels), dtype=np.float32)

            # スピーカーデータの取得
            try:
                speaker_data = self.speaker_queue.get(timeout=0.01)
                # チャンネル数の調整
                if speaker_data.ndim == 1:
                    speaker_data = speaker_data.reshape(-1, 1)
                if speaker_data.shape[1] != self.channels:
                    if self.channels == 1:
                        speaker_data = np.mean(speaker_data, axis=1, keepdims=True)
                    else:
                        speaker_data = np.repeat(speaker_data[:, :1], self.channels, axis=1)
                speaker_buffer = speaker_data
                has_data = True
            except queue.Empty:
                speaker_buffer = np.zeros((self.blocksize, self.channels), dtype=np.float32)

            if has_data:
                # サイズを揃える
                min_len = min(len(mic_buffer), len(speaker_buffer))
                mic_chunk = mic_buffer[:min_len]
                speaker_chunk = speaker_buffer[:min_len]

                # ミキシング（単純加算 + クリッピング防止）
                mixed = mic_chunk + speaker_chunk
                mixed = np.clip(mixed, -1.0, 1.0)

                # ファイルに書き出し
                if self.output_file is not None:
                    self.output_file.write(mixed)

            # 定期的にディスク容量チェック
            if has_data and self.start_time:
                elapsed = time.time() - self.start_time
                if int(elapsed) % 60 == 0 and int(elapsed) > 0:
                    check_disk_space(self.output_dir)

    def select_devices_interactive(self):
        """対話的にデバイスを選択する"""
        input_devs, output_devs = list_audio_devices()

        if not input_devs:
            print("\n[エラー] 入力デバイス（マイク）が見つかりません。")
            return False
        if not output_devs:
            print("\n[エラー] 出力デバイス（スピーカー）が見つかりません。")
            return False

        # マイクの選択
        if self.mic_device is None:
            default_input = sd.default.device[0]
            print(f"\nマイクデバイスを選択してください (デフォルト: [{default_input}]): ", end="")
            try:
                choice = input().strip()
                if choice == "":
                    self.mic_device = default_input
                else:
                    self.mic_device = int(choice)
            except (ValueError, EOFError):
                self.mic_device = default_input

        # スピーカーの選択
        if self.speaker_device is None:
            default_output = sd.default.device[1]
            print(f"スピーカーデバイスを選択してください (デフォルト: [{default_output}]): ", end="")
            try:
                choice = input().strip()
                if choice == "":
                    self.speaker_device = default_output
                else:
                    self.speaker_device = int(choice)
            except (ValueError, EOFError):
                self.speaker_device = default_output

        devices = sd.query_devices()
        print(f"\n  マイク    : [{self.mic_device}] {devices[self.mic_device]['name']}")
        print(f"  スピーカー: [{self.speaker_device}] {devices[self.speaker_device]['name']}")

        return True

    def start_recording(self):
        """録音を開始する"""
        # 出力ディレクトリの作成
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # ディスク容量チェック
        if not check_disk_space(self.output_dir):
            print("[警告] ディスク容量が少ないですが、録音を続行します。")

        # 出力ファイルの準備
        filename = get_timestamp_filename()
        self.output_path = os.path.join(self.output_dir, filename)
        self.output_file = sf.SoundFile(
            self.output_path,
            mode="w",
            samplerate=self.sample_rate,
            channels=self.channels,
            format="WAV",
            subtype="FLOAT",
        )

        # WASAPIデバイスを探す
        wasapi_speaker, err = find_wasapi_loopback_device(self.speaker_device)
        if err:
            print(f"[警告] {err}")
            print("[情報] マイク音声のみを録音します。")
            wasapi_speaker = None

        wasapi_mic = find_wasapi_input_device(self.mic_device)

        self.is_recording = True
        self.start_time = time.time()

        # マイクストリームの開始
        try:
            self.mic_stream = sd.InputStream(
                device=wasapi_mic,
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.blocksize,
                dtype="float32",
                callback=self._mic_callback,
            )
            self.mic_stream.start()
            print("[OK] マイク録音を開始しました。")
        except Exception as e:
            print(f"[エラー] マイクストリームの開始に失敗しました: {e}")
            self.is_recording = False
            return False

        # スピーカー（ループバック）ストリームの開始
        if wasapi_speaker is not None:
            try:
                # WASAPIループバックモードで入力ストリームを作成
                # sounddevice の extra_settings で WASAPI 固有設定を行う
                wasapi_settings = sd.WasapiSettings(exclusive=False)
                self.speaker_stream = sd.InputStream(
                    device=wasapi_speaker,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    blocksize=self.blocksize,
                    dtype="float32",
                    callback=self._speaker_callback,
                    extra_settings=wasapi_settings,
                )
                self.speaker_stream.start()
                print("[OK] システム音声（ループバック）録音を開始しました。")
            except Exception as e:
                print(f"[警告] システム音声のキャプチャに失敗しました: {e}")
                print("[情報] マイク音声のみを録音します。")
                self.speaker_stream = None
        else:
            print("[情報] システム音声のキャプチャはスキップされました。")

        # 書き込みスレッドの開始
        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.writer_thread.start()

        return True

    def stop_recording(self):
        """録音を停止する"""
        self.is_recording = False
        elapsed = time.time() - self.start_time if self.start_time else 0

        print("\n\n録音を停止しています...")

        # ストリームの停止
        if self.mic_stream is not None:
            try:
                self.mic_stream.stop()
                self.mic_stream.close()
            except Exception:
                pass

        if self.speaker_stream is not None:
            try:
                self.speaker_stream.stop()
                self.speaker_stream.close()
            except Exception:
                pass

        # 書き込みスレッドの終了を待機
        if self.writer_thread is not None:
            self.writer_thread.join(timeout=5.0)

        # ファイルを閉じる
        if self.output_file is not None:
            self.output_file.close()

        print(f"\n{'=' * 50}")
        print(f"  録音完了!")
        print(f"  録音時間  : {format_duration(elapsed)}")
        print(f"  保存先    : {os.path.abspath(self.output_path)}")

        # ファイルサイズを表示
        if os.path.exists(self.output_path):
            size_mb = os.path.getsize(self.output_path) / (1024 * 1024)
            print(f"  ファイルサイズ: {size_mb:.1f} MB")

        print(f"{'=' * 50}")

    def display_status(self):
        """録音中のステータスを表示する"""
        if not self.is_recording or not self.start_time:
            return
        elapsed = time.time() - self.start_time
        duration = format_duration(elapsed)
        mic_meter = render_vu_meter(self.mic_level * 10)  # 感度調整
        speaker_meter = render_vu_meter(self.speaker_level * 10)

        status_line = (
            f"\r  ● REC {duration}  "
            f"マイク: {mic_meter}  "
            f"スピーカー: {speaker_meter}  "
        )
        print(status_line, end="", flush=True)


# =============================================================================
# MP3変換ユーティリティ
# =============================================================================
def convert_to_mp3(wav_path: str, mp3_path: str = None) -> str:
    """WAVファイルをMP3に変換する（pydubが必要）"""
    try:
        from pydub import AudioSegment
    except ImportError:
        print("[エラー] MP3変換にはpydubが必要です。")
        print("  pip install pydub")
        print("  また、ffmpegのインストールも必要です。")
        return None

    if mp3_path is None:
        mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"

    print(f"MP3に変換中: {mp3_path}")
    audio = AudioSegment.from_wav(wav_path)
    audio.export(mp3_path, format="mp3", bitrate="192k")
    print(f"MP3変換完了: {mp3_path}")
    return mp3_path


# =============================================================================
# メイン関数
# =============================================================================
def parse_args():
    """コマンドライン引数をパースする"""
    parser = argparse.ArgumentParser(
        description="WEB会議 全音声録音ツール (Windows WASAPI Loopback対応)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s                           # 対話的にデバイスを選択して録音
  %(prog)s --list-devices            # デバイス一覧を表示
  %(prog)s --mic 1 --speaker 4       # デバイスを指定して録音
  %(prog)s --output-dir ./my_rec     # 出力ディレクトリを指定
  %(prog)s --sample-rate 48000       # サンプルレートを指定
  %(prog)s --to-mp3                  # 録音後にMP3に変換
        """,
    )
    parser.add_argument(
        "--list-devices", action="store_true",
        help="利用可能なオーディオデバイスを一覧表示して終了",
    )
    parser.add_argument(
        "--mic", type=int, default=None,
        help="マイクデバイスのインデックス番号",
    )
    parser.add_argument(
        "--speaker", type=int, default=None,
        help="スピーカーデバイスのインデックス番号",
    )
    parser.add_argument(
        "--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE,
        help=f"サンプルレート (デフォルト: {DEFAULT_SAMPLE_RATE})",
    )
    parser.add_argument(
        "--channels", type=int, default=DEFAULT_CHANNELS, choices=[1, 2],
        help=f"チャンネル数: 1=モノラル, 2=ステレオ (デフォルト: {DEFAULT_CHANNELS})",
    )
    parser.add_argument(
        "--blocksize", type=int, default=DEFAULT_BLOCKSIZE,
        help=f"バッファサイズ (デフォルト: {DEFAULT_BLOCKSIZE})",
    )
    parser.add_argument(
        "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR,
        help=f"出力ディレクトリ (デフォルト: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--to-mp3", action="store_true",
        help="録音後にMP3に変換する (pydub + ffmpegが必要)",
    )
    return parser.parse_args()


def main():
    """メインエントリポイント"""
    args = parse_args()

    # ヘッダー表示
    print("=" * 60)
    print("  WEB会議 全音声録音ツール")
    print("  (Windows WASAPI Loopback対応)")
    print("=" * 60)

    # プラットフォームチェック
    if sys.platform != "win32":
        print("\n[警告] このプログラムはWindows専用です。")
        print("  WASAPIループバック機能はWindowsでのみ利用可能です。")
        print("  現在のOS: " + sys.platform)
        print("  マイク録音のみで続行しますか？ (y/N): ", end="")
        try:
            answer = input().strip().lower()
            if answer != "y":
                print("終了します。")
                return
        except (EOFError, KeyboardInterrupt):
            print("\n終了します。")
            return

    # デバイス一覧表示モード
    if args.list_devices:
        list_audio_devices()
        return

    # レコーダーの初期化
    recorder = AudioRecorder(
        mic_device=args.mic,
        speaker_device=args.speaker,
        sample_rate=args.sample_rate,
        channels=args.channels,
        blocksize=args.blocksize,
        output_dir=args.output_dir,
    )

    # デバイス選択
    if not recorder.select_devices_interactive():
        print("[エラー] デバイスの選択に失敗しました。")
        return

    # 録音開始の確認
    print(f"\n  サンプルレート: {args.sample_rate} Hz")
    print(f"  チャンネル数  : {args.channels} ({'モノラル' if args.channels == 1 else 'ステレオ'})")
    print(f"  出力先        : {os.path.abspath(args.output_dir)}")
    print(f"\n  Enterキーで録音開始... (Ctrl+C で中止)")

    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print("\n中止しました。")
        return

    # 録音開始
    if not recorder.start_recording():
        print("[エラー] 録音の開始に失敗しました。")
        return

    print(f"\n  ● 録音中... (Enterキー または Ctrl+C で停止)\n")

    # 録音中のステータス表示ループ
    try:
        # 別スレッドでEnterキーを待つ
        stop_event = threading.Event()

        def wait_for_enter():
            try:
                input()
                stop_event.set()
            except (EOFError, KeyboardInterrupt):
                stop_event.set()

        enter_thread = threading.Thread(target=wait_for_enter, daemon=True)
        enter_thread.start()

        while not stop_event.is_set():
            recorder.display_status()
            time.sleep(0.1)

    except KeyboardInterrupt:
        pass

    # 録音停止
    recorder.stop_recording()

    # MP3変換
    if args.to_mp3 and recorder.output_path:
        convert_to_mp3(recorder.output_path)

    print("\nお疲れ様でした！")


if __name__ == "__main__":
    main()
