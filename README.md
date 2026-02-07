# NewTEST
Windows web meeting recorder and transcript generator.

## Setup
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage
List audio devices:
```bash
python record_transcribe.py --list-devices
```

Record loopback audio (press Enter to stop):
```bash
python record_transcribe.py --output-dir outputs --model base --language ja
```

Record loopback + microphone:
```bash
python record_transcribe.py --include-mic --mic-device "Microphone" --mic-gain 1.0
```

Outputs:
- *_loopback.wav
- *_mic.wav (when enabled)
- *_mix_16000.wav
- *.md transcript
