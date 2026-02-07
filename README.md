# Meeting Transcriber (Windows)

Windows PCでWeb会議の音声を**録音**し、Whisperで**文字起こし**して**Markdown**を生成するPythonプログラムです。

## できること

- **システム音（WASAPI ループバック）**を録音（相手側の音声）
- **マイク音声**を録音（自分側の音声）
- 録音した音声から**文字起こし**して `transcript.md` を生成

## 前提

- Windows 10 / 11
- Python 3.10+（推奨）
- 初回の文字起こし時にWhisperモデルをダウンロードします（ネットワークが必要）

## セットアップ

PowerShellで以下を実行してください。

```bash
py -m pip install -r requirements.txt
```

## 使い方

### 1) 録音デバイス一覧を表示

```bash
py -m meeting_transcriber --list-devices
```

### 2) 録音（Enterで停止）

既定の「出力デバイス（システム音）」と「入力デバイス（マイク）」を使います。

```bash
py -m meeting_transcriber run --out output
```

`output/` に以下が出力されます。

- `system.wav`（システム音。相手の声が入る想定）
- `mic.wav`（マイク音声）
- `recording_info.txt`
- `transcript.md`（`system.wav` と `mic.wav` をそれぞれセクション分けして文字起こし）

### 3) デバイスを指定して録音

`--list-devices` の一覧から index を指定します。

```bash
py -m meeting_transcriber run --out output --system-device 3 --mic-device 1
```

### 4) 録音のみ

```bash
py -m meeting_transcriber record --out output
```

### 5) 文字起こしのみ

```bash
py -m meeting_transcriber transcribe --audio output/system.wav --out output/transcript.md --model small --language ja
```

`--language auto` にすると自動判定します。

## 注意点

- **システム音の録音はWindows(WASAPI)のみ対応**です。失敗する場合は `--system-device` を「hostapiがWASAPIの出力デバイス」に変更してください。
- 会議アプリ側のエコーキャンセル等により、マイク音声に相手の声が入ったり入らなかったりします。基本は `system.wav` を文字起こし対象にするのがおすすめです。
