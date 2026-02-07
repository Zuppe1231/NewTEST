# Windows WEB会議 録音 & トランスクリプト作成ツール

Windows PC でWEB会議（Zoom, Teams, Google Meet など）の音声を録音し、  
[OpenAI Whisper](https://github.com/openai/whisper) を使って自動で文字起こし（トランスクリプト）を行い、  
**Markdown ファイル**として保存する Python ツールです。

## 主な機能

- **システム音声（WASAPI ループバック）**と**マイク音声**を同時録音
- WASAPI ループバックデバイスの自動検出
- 録音終了後に Whisper でローカル文字起こし（インターネット不要）
- タイムスタンプ付きのトランスクリプトを Markdown 形式で出力
- 既存の WAV ファイルからの文字起こしにも対応

## 動作環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.9 以上 |
| メモリ | 4GB 以上（`medium`/`large` モデル使用時は 8GB 以上推奨） |
| GPU | なくても動作しますが、CUDA 対応 GPU があると高速化されます |

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. 仮想環境の作成（推奨）

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

#### GPU (CUDA) を使う場合

PyTorch の CUDA 版を別途インストールしてください。

```bash
# CUDA 12.1 の場合
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

詳細は [PyTorch 公式サイト](https://pytorch.org/get-started/locally/) を参照してください。

## 使い方

### 基本的な録音 & 文字起こし

```bash
python meeting_recorder.py
```

実行すると録音が開始されます。**Ctrl+C** を押すと録音が停止し、自動的に文字起こしが行われます。

生成されるファイル:
- `recordings/meeting_YYYYMMDD_HHMMSS.wav` — 録音音声
- `recordings/meeting_YYYYMMDD_HHMMSS_transcript.md` — トランスクリプト

### オーディオデバイスの確認

```bash
python meeting_recorder.py --list-devices
```

利用可能なオーディオデバイスの一覧が表示されます。デバイス番号を `--mic-device` や `--loopback-device` に指定できます。

### デバイスを指定して録音

```bash
python meeting_recorder.py --mic-device 1 --loopback-device 4
```

### Whisper モデルの指定

精度と速度のトレードオフに応じてモデルを選択できます。

| モデル | サイズ | 速度 | 精度 |
|--------|--------|------|------|
| `tiny` | 39M | 最速 | 低 |
| `base` | 74M | 速い | 中 |
| `small` | 244M | 普通 | 中高 |
| `medium` | 769M | 遅い | 高 |
| `large` | 1.5GB | 最遅 | 最高 |

```bash
# 高精度モデルを使用
python meeting_recorder.py --model medium

# 高速モデルを使用
python meeting_recorder.py --model tiny
```

### 会議タイトルを指定

```bash
python meeting_recorder.py --title "プロジェクト定例会議"
```

### 既存の WAV ファイルから文字起こし

すでに録音済みの WAV ファイルがある場合、文字起こしのみ実行できます。

```bash
python meeting_recorder.py --transcribe-only recordings/meeting_20260207.wav
```

### 英語会議の文字起こし

```bash
python meeting_recorder.py --language en
```

### WAV ファイルを保存しない

ディスク容量を節約したい場合、文字起こし後に WAV ファイルを自動削除できます。

```bash
python meeting_recorder.py --no-save-wav
```

### 出力先ディレクトリの変更

```bash
python meeting_recorder.py --output-dir ./my_meetings
```

## コマンドラインオプション一覧

| オプション | 説明 | デフォルト |
|------------|------|------------|
| `--list-devices` | オーディオデバイス一覧を表示 | — |
| `--mic-device` | マイクデバイス番号 | 自動検出 |
| `--loopback-device` | ループバックデバイス番号 | 自動検出 |
| `--model` | Whisper モデル (tiny/base/small/medium/large) | `base` |
| `--language` | 文字起こし言語コード | `ja` |
| `--title` | 会議タイトル | — |
| `--output-dir` | 出力先ディレクトリ | `recordings` |
| `--transcribe-only` | 既存 WAV から文字起こしのみ実行 | — |
| `--no-save-wav` | WAV ファイルを保存しない | `false` |

## 出力例

生成される Markdown ファイルの例:

```markdown
# プロジェクト定例会議

## 会議情報

| 項目 | 内容 |
|------|------|
| 録音日時 | 2026年02月07日 14:00:00 |
| 録音時間 | 00:30:15 |
| 音声ファイル | `meeting_20260207_140000.wav` |
| セグメント数 | 42 |

## トランスクリプト

**[00:00:03 - 00:00:08]**
それでは定例会議を始めます。本日の議題は3つあります。

**[00:00:09 - 00:00:15]**
まず最初に、先週のタスクの進捗確認からお願いします。

...
```

## トラブルシューティング

### 「ループバックデバイスが見つかりません」と表示される

- `--list-devices` でデバイス一覧を確認し、WASAPI の出力デバイスを `--loopback-device` で手動指定してください
- Windows の「サウンド設定」で「ステレオミキサー」を有効にすることで解決する場合もあります

### 音声が録音されない

- Windows の「プライバシーとセキュリティ」→「マイク」でアプリのマイクアクセスが許可されているか確認してください
- 他のアプリがマイクを占有していないか確認してください

### 文字起こしの精度が低い

- `--model medium` や `--model large` を試してください（より多くのメモリと時間が必要です）
- 静かな環境で録音してください
- 外部マイクを使用すると精度が向上する場合があります

### CUDA が使えない

- [PyTorch 公式サイト](https://pytorch.org/get-started/locally/) から CUDA 対応版をインストールしてください
- `nvidia-smi` コマンドで GPU が認識されているか確認してください

## ライセンス

MIT License
