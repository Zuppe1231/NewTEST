# WEB会議 全音声録音ツール

Windows PCでWEB会議（Zoom, Microsoft Teams, Google Meet等）を行う際に、**すべての音声**（マイク入力 + システム音声出力）を録音するPythonプログラムです。

## 特徴

- **マイク音声**: 自分の発話を録音
- **システム音声**: 相手の発話（スピーカー出力）を WASAPI ループバックでキャプチャ
- **ミキシング**: マイクとシステム音声を1つのWAVファイルに合成
- **リアルタイムモニタリング**: 録音中の経過時間と音量レベルをVUメーター風に表示
- **ストリーミング書き込み**: 長時間録音でもメモリを圧迫しない設計
- **MP3変換**: オプションでWAVからMP3への変換にも対応

## 動作環境

- **OS**: Windows 10 / 11
- **Python**: 3.8 以上
- **管理者権限**: 不要

## インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd <repository-name>

# 依存ライブラリのインストール
pip install -r requirements.txt
```

### MP3変換を利用する場合（オプション）

MP3変換には `ffmpeg` が別途必要です。

```bash
# winget でインストール
winget install ffmpeg

# または chocolatey でインストール
choco install ffmpeg
```

## 使い方

### 基本的な使い方（対話モード）

```bash
python web_meeting_recorder.py
```

1. プログラムが起動するとデバイス一覧が表示されます
2. マイクデバイスとスピーカーデバイスの番号を選択します
3. Enterキーで録音開始
4. Enterキー または Ctrl+C で録音停止
5. `recordings/` フォルダにWAVファイルが保存されます

### デバイス一覧の確認

```bash
python web_meeting_recorder.py --list-devices
```

### デバイスを指定して録音

```bash
python web_meeting_recorder.py --mic 1 --speaker 4
```

### 出力先やフォーマットの指定

```bash
# 出力ディレクトリを指定
python web_meeting_recorder.py --output-dir ./my_recordings

# サンプルレートを48000Hzに変更
python web_meeting_recorder.py --sample-rate 48000

# ステレオで録音
python web_meeting_recorder.py --channels 2

# 録音後にMP3に変換
python web_meeting_recorder.py --to-mp3
```

### すべてのオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--list-devices` | デバイス一覧を表示して終了 | - |
| `--mic` | マイクデバイスのインデックス番号 | 対話で選択 |
| `--speaker` | スピーカーデバイスのインデックス番号 | 対話で選択 |
| `--sample-rate` | サンプルレート (Hz) | 44100 |
| `--channels` | チャンネル数 (1: モノラル, 2: ステレオ) | 1 |
| `--blocksize` | バッファサイズ | 1024 |
| `--output-dir` | 出力ディレクトリ | `./recordings` |
| `--to-mp3` | 録音後にMP3に変換 | 無効 |

## 仕組み

### WASAPI ループバック

Windowsの **WASAPI（Windows Audio Session API）** には「ループバック」モードがあり、スピーカーに出力されるすべての音声をキャプチャできます。仮想オーディオデバイス等の追加ソフトウェアは不要です。

### アーキテクチャ

```
マイク ──→ [入力ストリーム] ──→ ┐
                                  ├─→ [ミキサー] ──→ [WAVファイル]
スピーカー ──→ [WASAPIループバック] ──→ ┘
```

1. **マイクストリーム**: `sounddevice.InputStream` で標準入力をキャプチャ
2. **ループバックストリーム**: WASAPI ループバックモードでシステム音声をキャプチャ
3. **ミキサー**: 別スレッドで2つの音声ストリームをNumPyで加算・ミキシング
4. **ライター**: `soundfile` でストリーミング書き込み

## プロンプト

このプログラムを作成するために使用したプロンプトは `PROMPT.md` に記載されています。

## 注意事項

- このプログラムは **Windows 専用** です（WASAPIループバックはWindows固有の機能です）
- 一部のオーディオデバイスではサンプルレートの変更が必要な場合があります
- WEB会議の録音は、参加者への事前告知が必要な場合があります（法律・社内規定をご確認ください）

## ライセンス

MIT License
