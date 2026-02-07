import argparse
import datetime as dt
import os
import sys
import threading

import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper
from whisper.audio import resample


def list_devices():
    hostapis = sd.query_hostapis()
    for idx, dev in enumerate(sd.query_devices()):
        hostapi = hostapis[dev["hostapi"]]["name"]
        print(
            f"{idx}: {dev['name']} ({hostapi}) "
            f"in={dev['max_input_channels']} out={dev['max_output_channels']}"
        )


def parse_device_arg(device_arg):
    if device_arg is None:
        return None
    try:
        return int(device_arg)
    except ValueError:
        pass
    needle = device_arg.lower()
    matches = [
        idx
        for idx, dev in enumerate(sd.query_devices())
        if needle in dev["name"].lower()
    ]
    if not matches:
        raise ValueError(f"no device matches: {device_arg}")
    if len(matches) > 1:
        raise ValueError(f"multiple devices match: {device_arg} -> {matches}")
    return matches[0]


def get_default_wasapi_output():
    for host in sd.query_hostapis():
        if str(host.get("type", "")).lower() == "wasapi":
            idx = host.get("default_output_device", None)
            if idx is not None and idx >= 0:
                return idx
    return None


def get_loopback_settings():
    try:
        return sd.WasapiSettings(loopback=True)
    except Exception:
        return None


class StreamRecorder:
    def __init__(self, device, samplerate, channels, extra_settings=None):
        self.device = device
        self.samplerate = samplerate
        self.channels = channels
        self.extra_settings = extra_settings
        self.frames = []
        self.lock = threading.Lock()
        self.status = None
        self.stream = sd.InputStream(
            device=self.device,
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            callback=self._callback,
            extra_settings=self.extra_settings,
        )

    def _callback(self, indata, frames, time_info, status):
        if status:
            self.status = status
        with self.lock:
            self.frames.append(indata.copy())

    def start(self):
        self.stream.start()

    def stop(self):
        self.stream.stop()
        self.stream.close()

    def get_audio(self):
        with self.lock:
            if not self.frames:
                return np.empty((0, self.channels), dtype=np.float32)
            return np.concatenate(self.frames, axis=0)


def to_mono(audio):
    if audio.ndim == 1:
        return audio
    return np.mean(audio, axis=1)


def normalize(audio):
    if audio.size == 0:
        return audio
    peak = np.max(np.abs(audio))
    if peak > 1.0:
        audio = audio / peak
    return audio


def format_ts(seconds):
    ms = int(seconds * 1000)
    s = ms // 1000
    ms = ms % 1000
    h = s // 3600
    s = s % 3600
    m = s // 60
    s = s % 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def build_markdown(
    output_path,
    started_at,
    loop_info,
    mic_info,
    loop_samplerate,
    mic_samplerate,
    model_name,
    result,
):
    lines = []
    lines.append("# Transcript")
    lines.append("")
    lines.append(f"- started_at: {started_at.isoformat()}")
    lines.append(f"- loopback_device: {loop_info}")
    lines.append(f"- mic_device: {mic_info}")
    lines.append(f"- loopback_samplerate: {loop_samplerate}")
    lines.append(f"- mic_samplerate: {mic_samplerate}")
    lines.append(f"- model: {model_name}")
    lines.append("")
    lines.append("## Full text")
    lines.append("")
    lines.append(result.get("text", "").strip())
    lines.append("")
    lines.append("## Segments")
    lines.append("")
    for seg in result.get("segments", []):
        start = format_ts(seg["start"])
        end = format_ts(seg["end"])
        text = seg["text"].strip()
        lines.append(f"- [{start} - {end}] {text}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Record Windows web meeting audio and transcribe to markdown."
    )
    parser.add_argument("--list-devices", action="store_true", help="List devices.")
    parser.add_argument(
        "--device",
        help="Loopback device index or name (default: WASAPI default output).",
    )
    parser.add_argument(
        "--include-mic",
        action="store_true",
        help="Also record microphone and mix into transcript audio.",
    )
    parser.add_argument("--mic-device", help="Microphone device index or name.")
    parser.add_argument("--duration", type=float, help="Seconds to record.")
    parser.add_argument("--samplerate", type=float, help="Override loopback samplerate.")
    parser.add_argument("--mic-samplerate", type=float, help="Override mic samplerate.")
    parser.add_argument(
        "--channels", type=int, default=2, help="Loopback channel count."
    )
    parser.add_argument(
        "--mic-channels", type=int, default=1, help="Microphone channel count."
    )
    parser.add_argument(
        "--mic-gain",
        type=float,
        default=1.0,
        help="Gain applied to mic audio before mixing.",
    )
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model name (tiny, base, small, medium, large).",
    )
    parser.add_argument("--language", help="Language code (optional).")
    parser.add_argument(
        "--output-dir", default="outputs", help="Directory for output files."
    )
    parser.add_argument(
        "--basename",
        help="Base name for output files (default: meeting_YYYYmmdd_HHMMSS).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.list_devices:
        list_devices()
        return 0

    os.makedirs(args.output_dir, exist_ok=True)

    loop_device = parse_device_arg(args.device)
    if loop_device is None:
        loop_device = get_default_wasapi_output()
    if loop_device is None:
        loop_device = sd.default.device[1]

    loop_info = sd.query_devices(loop_device)
    hostapis = sd.query_hostapis()
    loop_hostapi = hostapis[loop_info["hostapi"]]
    if str(loop_hostapi.get("type", "")).lower() == "wasapi":
        loopback_settings = get_loopback_settings()
    else:
        loopback_settings = None
    if loopback_settings is None:
        print(
            "WASAPI loopback not available; falling back to input capture.",
            file=sys.stderr,
        )
        if loop_info["max_input_channels"] < 1:
            loop_device = sd.default.device[0]
            loop_info = sd.query_devices(loop_device)
        if loop_info["max_input_channels"] < 1:
            print("No input channels available for capture.", file=sys.stderr)
            return 1
        loop_samplerate = args.samplerate or loop_info["default_samplerate"]
        loop_channels = max(1, min(args.channels, loop_info["max_input_channels"]))
    else:
        loop_samplerate = args.samplerate or loop_info["default_samplerate"]
        loop_channels = max(1, min(args.channels, loop_info["max_output_channels"]))
        if loop_info["max_output_channels"] < 1:
            print("Selected device has no output channels for loopback.", file=sys.stderr)
            return 1

    mic_recorder = None
    mic_info = None
    mic_samplerate = None
    if args.include_mic:
        mic_device = parse_device_arg(args.mic_device)
        if mic_device is None:
            mic_device = sd.default.device[0]
        mic_info = sd.query_devices(mic_device)
        mic_samplerate = args.mic_samplerate or mic_info["default_samplerate"]
        mic_channels = max(1, min(args.mic_channels, mic_info["max_input_channels"]))
        if mic_info["max_input_channels"] < 1:
            print("Selected mic device has no input channels.", file=sys.stderr)
            return 1
        mic_recorder = StreamRecorder(
            mic_device, mic_samplerate, mic_channels, extra_settings=None
        )

    loop_recorder = StreamRecorder(
        loop_device,
        loop_samplerate,
        loop_channels,
        extra_settings=loopback_settings,
    )

    stop_event = threading.Event()

    def wait_for_stop():
        if args.duration:
            stop_event.wait(args.duration)
        else:
            input("Press Enter to stop recording...\n")
        stop_event.set()

    started_at = dt.datetime.now()
    stopper = threading.Thread(target=wait_for_stop, daemon=True)
    stopper.start()

    try:
        if mic_recorder:
            mic_recorder.start()
        loop_recorder.start()
        stop_event.wait()
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        loop_recorder.stop()
        if mic_recorder:
            mic_recorder.stop()

    loop_audio = loop_recorder.get_audio()
    if loop_audio.size == 0:
        print("No loopback audio captured.", file=sys.stderr)
        return 1

    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    basename = args.basename or f"meeting_{timestamp}"
    loop_path = os.path.join(args.output_dir, f"{basename}_loopback.wav")
    sf.write(loop_path, loop_audio, int(loop_samplerate))

    mic_audio = None
    if mic_recorder:
        mic_audio = mic_recorder.get_audio()
        if mic_audio.size > 0:
            mic_path = os.path.join(args.output_dir, f"{basename}_mic.wav")
            sf.write(mic_path, mic_audio, int(mic_samplerate))

    loop_mono = to_mono(loop_audio)
    loop_resampled = resample(loop_mono, int(loop_samplerate), 16000)

    mix_audio = loop_resampled
    if mic_audio is not None and mic_audio.size > 0:
        mic_mono = to_mono(mic_audio) * float(args.mic_gain)
        mic_resampled = resample(mic_mono, int(mic_samplerate), 16000)
        max_len = max(len(loop_resampled), len(mic_resampled))
        if len(loop_resampled) < max_len:
            loop_resampled = np.pad(loop_resampled, (0, max_len - len(loop_resampled)))
        if len(mic_resampled) < max_len:
            mic_resampled = np.pad(mic_resampled, (0, max_len - len(mic_resampled)))
        mix_audio = loop_resampled + mic_resampled

    mix_audio = normalize(mix_audio.astype(np.float32))
    mix_path = os.path.join(args.output_dir, f"{basename}_mix_16000.wav")
    sf.write(mix_path, mix_audio, 16000)

    model = whisper.load_model(args.model)
    result = model.transcribe(
        mix_audio,
        language=args.language,
        task="transcribe",
        fp16=False,
        verbose=False,
    )

    md_path = os.path.join(args.output_dir, f"{basename}.md")
    build_markdown(
        md_path,
        started_at,
        loop_info["name"],
        mic_info["name"] if mic_info else "none",
        loop_samplerate,
        mic_samplerate if mic_samplerate else "none",
        args.model,
        result,
    )

    print(f"Saved: {loop_path}")
    if mic_audio is not None and mic_audio.size > 0:
        print(f"Saved: {mic_path}")
    print(f"Saved: {mix_path}")
    print(f"Saved: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
