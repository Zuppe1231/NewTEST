# WEB会議録音・文字起こしプログラム

Windows PCでWEB会議の音声を録音し、自動的にトランスクリプト（文字起こし）をマークダウンファイルで作成するPythonプログラムです。

## 機能

- 🎤 **高品質な音声録音**: システムオーディオやマイクからの音声を録音
- 📝 **自動文字起こし**: OpenAI Whisperを使用した高精度な文字起こし
- ⏱️ **タイムスタンプ付き**: 発言ごとにタイムスタンプを記録
- 📄 **マークダウン出力**: 見やすいマークダウン形式でトランスクリプトを保存
- 🌍 **多言語対応**: 日本語、英語など多数の言語に対応

## 必要環境

- Windows 10/11
- Python 3.8以上
- マイクまたは音声入力デバイス

## インストール

### 1. Pythonのインストール

[Python公式サイト](https://www.python.org/downloads/)から最新版のPython 3.8以上をダウンロードしてインストールしてください。

### 2. 依存パッケージのインストール

コマンドプロンプトまたはPowerShellで以下を実行:

```bash
pip install -r requirements.txt
```

**注意**: 
- 初回実行時にWhisperモデルがダウンロードされます（数百MB〜数GB）
- PyTorchのインストールに時間がかかる場合があります

### 3. Windows用の追加設定（必要な場合）

システムオーディオを録音する場合、以下の設定が必要です：

1. **ステレオミックスの有効化**:
   - サウンド設定を開く（タスクバーのスピーカーアイコンを右クリック → 「サウンドの設定」）
   - 「サウンドコントロールパネル」を開く
   - 「録音」タブで「ステレオミックス」を右クリック → 「有効化」
   
2. または **仮想オーディオケーブル**を使用:
   - [VB-CABLE](https://vb-audio.com/Cable/) などのソフトウェアをインストール

## 使い方

### 基本的な使い方（録音して文字起こし）

```bash
# 日本語の会議を録音（Enterキーで停止）
python web_meeting_recorder.py

# 英語の会議を録音
python web_meeting_recorder.py --language en

# 録音時間を指定（例: 60秒）
python web_meeting_recorder.py --duration 60
```

### 音声デバイスの選択

```bash
# 利用可能なデバイスを一覧表示
python web_meeting_recorder.py --list-devices

# 特定のデバイスを使用（デバイスIDを指定）
python web_meeting_recorder.py --device 1
```

### 既存の音声ファイルを文字起こし

```bash
# WAVファイルを文字起こし
python web_meeting_recorder.py --audio-file meeting.wav

# MP3やM4Aなども対応
python web_meeting_recorder.py --audio-file recording.mp3 --language ja
```

### 詳細オプション

```bash
python web_meeting_recorder.py \
  --duration 120 \           # 録音時間（秒）
  --device 1 \               # デバイスID
  --language ja \            # 言語（ja, en, etc.）
  --model medium \           # Whisperモデル（tiny, base, small, medium, large）
  --sample-rate 44100 \      # サンプリングレート（Hz）
  --channels 2 \             # チャンネル数（1=モノラル, 2=ステレオ）
  --output-dir recordings    # 出力ディレクトリ
```

## Whisperモデルの選択

| モデル | サイズ | 速度 | 精度 | 推奨用途 |
|--------|--------|------|------|----------|
| tiny   | 39 MB  | 最速 | 低   | テスト用 |
| base   | 74 MB  | 高速 | 中   | デフォルト（推奨） |
| small  | 244 MB | 中速 | 高   | 高品質な文字起こし |
| medium | 769 MB | 低速 | 最高 | 専門的な会議 |
| large  | 1550 MB| 最遅 | 最高 | 最高品質（GPU推奨） |

## 出力ファイル

プログラムは以下のファイルを`recordings/`ディレクトリに生成します：

- `meeting_YYYYMMDD_HHMMSS.wav`: 録音した音声ファイル
- `transcript_YYYYMMDD_HHMMSS.md`: 文字起こしのマークダウンファイル

### マークダウンファイルの構造

```markdown
# WEB会議トランスクリプト

**作成日時**: 2026年02月07日 14:30:00
**音声ファイル**: meeting_20260207_143000.wav

## 全文

会議の全文がここに表示されます...

## タイムスタンプ付き詳細

### [00:00 - 00:15]

会議を始めます。本日の議題は...

### [00:15 - 00:30]

次の項目について説明します...

---

## メタデータ

- **言語**: ja
- **総時間**: 05:30
- **セグメント数**: 22
```

## トラブルシューティング

### 音声が録音されない

1. マイクやオーディオデバイスが正しく接続されているか確認
2. `--list-devices`で利用可能なデバイスを確認
3. 正しいデバイスIDを`--device`オプションで指定

### システムオーディオ（PC内部の音声）が録音できない

1. Windowsのステレオミックスを有効化
2. または仮想オーディオケーブル（VB-CABLEなど）を使用
3. Zoom/TeamsなどのWEB会議ツールの録音機能と併用も検討

### 文字起こしの精度が低い

1. より大きなモデルを使用: `--model medium`または`--model large`
2. 音質の良いマイクを使用
3. 静かな環境で録音
4. 正しい言語を指定: `--language ja`

### メモリ不足エラー

1. より小さなモデルを使用: `--model tiny`または`--model base`
2. 長時間の録音を分割して処理
3. 不要なアプリケーションを終了

## コード例: Pythonスクリプトから使用

```python
from web_meeting_recorder import WebMeetingRecorder

# レコーダーインスタンスを作成
recorder = WebMeetingRecorder(
    sample_rate=16000,
    channels=2,
    output_dir="my_recordings",
    whisper_model="base"
)

# 録音と文字起こしを実行
audio_file, transcript_file = recorder.record_and_transcribe(
    duration=None,  # Enterキーで停止
    language="ja"
)

print(f"完了！トランスクリプト: {transcript_file}")
```

## ライセンス

このプログラムは教育・個人利用を目的としています。商用利用の場合は、使用するライブラリ（特にOpenAI Whisper）のライセンスを確認してください。

## 注意事項

- 会議の録音には参加者の同意が必要な場合があります
- プライバシーと著作権に配慮してご使用ください
- 生成されたトランスクリプトは100%正確ではない可能性があります
- 重要な会議では必ず内容を確認してください

## サポート

問題や質問がある場合は、GitHubのIssuesでお知らせください。
