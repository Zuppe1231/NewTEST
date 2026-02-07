from __future__ import annotations

import dataclasses
import datetime as dt
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf


@dataclasses.dataclass(frozen=True)
class RecordingConfig:
    out_dir: Path
    system_device: Optional[int] = None
    mic_device: Optional[int] = None
    enable_system: bool = True
    enable_mic: bool = True
    samplerate: Optional[int] = None
    channels: int = 1
    duration: Optional[float] = None


@dataclasses.dataclass(frozen=True)
class RecordingOutputs:
    out_dir: Path
    started_at: dt.datetime
    ended_at: dt.datetime
    system_wav: Optional[Path]
    mic_wav: Optional[Path]
    info_txt: Path


def _import_sounddevice():
    try:
        import sounddevice as sd  # type: ignore
    except OSError as e:
        # Linux等でPortAudioが未導入だと import 時点で落ちるため、メッセージを分かりやすくする
        raise RuntimeError(
            "録音機能を使うにはPortAudioが必要です。Windowsでは通常pipで動作しますが、"
            "この環境ではPortAudioが見つからないため録音できません。"
        ) from e
    return sd


def list_devices_human() -> str:
    sd = _import_sounddevice()
    lines: list[str] = []
    lines.append("=== Devices (sounddevice) ===")
    hostapis = sd.query_hostapis()
    devices = sd.query_devices()
    default_in, default_out = sd.default.device
    lines.append(f"Default input device : {default_in}")
    lines.append(f"Default output device: {default_out}")
    lines.append("")
    for i, d in enumerate(devices):
        hostapi_name = hostapis[d["hostapi"]]["name"]
        lines.append(
            f"[{i}] {d['name']} | hostapi={hostapi_name} | "
            f"in={d['max_input_channels']} out={d['max_output_channels']} | "
            f"default_sr={d.get('default_samplerate')}"
        )
    lines.append("")
    lines.append(
        "ヒント: Windowsでシステム音を録音する場合は、出力デバイスを指定しWASAPI loopbackを使用します。"
    )
    return "\n".join(lines)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _default_output_device_index() -> int:
    sd = _import_sounddevice()
    _in, out = sd.default.device
    if out is None or out < 0:
        raise RuntimeError("既定の出力デバイスを取得できませんでした。--system-device を指定してください。")
    return int(out)


def _default_input_device_index() -> int:
    sd = _import_sounddevice()
    inp, _out = sd.default.device
    if inp is None or inp < 0:
        raise RuntimeError("既定の入力デバイスを取得できませんでした。--mic-device を指定してください。")
    return int(inp)


class _WriterThread(threading.Thread):
    def __init__(self, wav_path: Path, samplerate: int, channels: int):
        super().__init__(daemon=True)
        self.wav_path = wav_path
        self.samplerate = samplerate
        self.channels = channels
        self.q: "queue.Queue[np.ndarray | None]" = queue.Queue(maxsize=64)
        self._exc: Optional[BaseException] = None

    def run(self) -> None:
        try:
            with sf.SoundFile(
                str(self.wav_path),
                mode="w",
                samplerate=self.samplerate,
                channels=self.channels,
                subtype="PCM_16",
            ) as f:
                while True:
                    item = self.q.get()
                    if item is None:
                        break
                    f.write(item)
        except BaseException as e:  # noqa: BLE001
            self._exc = e

    def put(self, data: np.ndarray) -> None:
        self.q.put(data, block=True)

    def stop(self) -> None:
        self.q.put(None)

    def raise_if_failed(self) -> None:
        if self._exc is not None:
            raise self._exc


def record_audio(cfg: RecordingConfig) -> RecordingOutputs:
    sd = _import_sounddevice()
    if not cfg.enable_system and not cfg.enable_mic:
        raise ValueError("enable_system と enable_mic の両方が無効です。")

    if cfg.enable_system:
        if sys.platform != "win32":
            raise RuntimeError("システム音(ループバック)録音はWindows(WASAPI)のみ対応です。--no-system を指定してください。")
        if not hasattr(sd, "WasapiSettings"):
            raise RuntimeError("この環境のsounddeviceがWASAPI設定に対応していません。")

    out_dir = cfg.out_dir
    _ensure_dir(out_dir)
    started_at = dt.datetime.now(dt.timezone.utc).astimezone()

    system_wav = out_dir / "system.wav" if cfg.enable_system else None
    mic_wav = out_dir / "mic.wav" if cfg.enable_mic else None
    info_txt = out_dir / "recording_info.txt"

    stop_event = threading.Event()

    def _wait_for_enter() -> None:
        try:
            input("録音中... Enterで停止します。")
        except EOFError:
            pass
        stop_event.set()

    if cfg.duration is None:
        threading.Thread(target=_wait_for_enter, daemon=True).start()

    # デバイス/サンプルレートの決定
    system_dev = None
    mic_dev = None
    if cfg.enable_system:
        system_dev = cfg.system_device if cfg.system_device is not None else _default_output_device_index()
    if cfg.enable_mic:
        mic_dev = cfg.mic_device if cfg.mic_device is not None else _default_input_device_index()

    system_sr = None
    mic_sr = None
    if cfg.enable_system:
        system_sr = int(cfg.samplerate or sd.query_devices(system_dev)["default_samplerate"])
    if cfg.enable_mic:
        mic_sr = int(cfg.samplerate or sd.query_devices(mic_dev)["default_samplerate"])

    # 音声ストリーム開始
    writers: list[_WriterThread] = []
    streams: list[object] = []

    def _make_callback(w: _WriterThread):
        def cb(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                # statusはエラーではないこともあるため、stderrに出すだけ
                print(f"[audio] {status}", file=sys.stderr)
            w.put(indata.copy())

        return cb

    try:
        if cfg.enable_system and system_wav and system_sr is not None and system_dev is not None:
            w = _WriterThread(system_wav, samplerate=system_sr, channels=cfg.channels)
            w.start()
            writers.append(w)

            # Windows WASAPI loopback (システム音の録音)
            try:
                extra = sd.WasapiSettings(loopback=True)
            except Exception as e:  # noqa: BLE001
                raise RuntimeError(
                    "WASAPI loopbackの初期化に失敗しました。"
                    " 出力デバイス(スピーカー等)を選び、hostapiがWASAPIのものを指定してください。"
                ) from e
            s = sd.InputStream(
                device=system_dev,
                channels=cfg.channels,
                samplerate=system_sr,
                dtype="float32",
                callback=_make_callback(w),
                extra_settings=extra,
            )
            s.start()
            streams.append(s)

        if cfg.enable_mic and mic_wav and mic_sr is not None and mic_dev is not None:
            w = _WriterThread(mic_wav, samplerate=mic_sr, channels=cfg.channels)
            w.start()
            writers.append(w)

            s = sd.InputStream(
                device=mic_dev,
                channels=cfg.channels,
                samplerate=mic_sr,
                dtype="float32",
                callback=_make_callback(w),
            )
            s.start()
            streams.append(s)

        if not streams:
            raise RuntimeError("録音ストリームを開始できませんでした。デバイス設定を確認してください。")

        t0 = time.time()
        while True:
            if cfg.duration is not None and (time.time() - t0) >= cfg.duration:
                break
            if stop_event.is_set():
                break
            time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        for s in streams:
            try:
                s.stop()
            except Exception:  # noqa: BLE001
                pass
            try:
                s.close()
            except Exception:  # noqa: BLE001
                pass
        for w in writers:
            w.stop()
        for w in writers:
            w.join(timeout=10)
            w.raise_if_failed()

    ended_at = dt.datetime.now(dt.timezone.utc).astimezone()

    # 情報を書き出し
    lines: list[str] = []
    lines.append(f"started_at: {started_at.isoformat()}")
    lines.append(f"ended_at  : {ended_at.isoformat()}")
    lines.append("")
    lines.append("system:")
    if cfg.enable_system:
        lines.append(f"  enabled: true")
        lines.append(f"  device_index: {system_dev}")
        lines.append(f"  samplerate: {system_sr}")
        lines.append(f"  wav: {system_wav}")
    else:
        lines.append("  enabled: false")
    lines.append("")
    lines.append("mic:")
    if cfg.enable_mic:
        lines.append(f"  enabled: true")
        lines.append(f"  device_index: {mic_dev}")
        lines.append(f"  samplerate: {mic_sr}")
        lines.append(f"  wav: {mic_wav}")
    else:
        lines.append("  enabled: false")
    info_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return RecordingOutputs(
        out_dir=out_dir,
        started_at=started_at,
        ended_at=ended_at,
        system_wav=system_wav if (system_wav and system_wav.exists()) else None,
        mic_wav=mic_wav if (mic_wav and mic_wav.exists()) else None,
        info_txt=info_txt,
    )

