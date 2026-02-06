# Obsidian WEB会議録音・トランスクリプト作成ガイド

Windows PCでWEB会議を録音し、トランスクリプト（文字起こし）をマークダウンファイルとして作成するためのObsidianプラグインおよびワークフローをまとめたガイドです。

---

## 結論

**単一のプラグインで「WEB会議の録音 → 文字起こし → Markdownファイル作成」をすべて完結できるObsidianプラグインは、現時点では存在しません。**

ただし、複数のプラグインやツールを組み合わせることで、このワークフローを実現できます。以下に主要な選択肢をまとめます。

---

## 1. Obsidianプラグイン（文字起こし関連）

### 1.1 Whisper Transcription（推奨）

- **プラグイン名**: `Whisper Transcription` / `obsidian-whisper`
- **概要**: OpenAIのWhisper APIを利用して、音声ファイルをテキストに変字起こしし、Obsidianのノートに貼り付けます。
- **機能**:
  - 音声ファイル（mp3, wav, m4a, webmなど）をアップロードして文字起こし
  - 結果をMarkdownノートとして保存
  - 日本語対応
- **必要なもの**: OpenAI APIキー（有料）
- **インストール**: Obsidian → 設定 → コミュニティプラグイン → 「Whisper」で検索

### 1.2 Audio Recorder

- **プラグイン名**: `Audio Recorder`
- **概要**: Obsidian内で直接音声を録音できるプラグイン
- **機能**:
  - マイク入力から音声を録音
  - 録音ファイルをVault内に保存
- **注意**: **システム音声（WEB会議の相手の声）は録音できない**場合があります。マイク入力のみの録音になるため、WEB会議の全体録音には不向きです。

### 1.3 Obsidian Transcription

- **プラグイン名**: `Transcription`
- **概要**: 音声・動画ファイルの文字起こしを行うプラグイン
- **機能**:
  - Whisper API または Azure Speech Services を利用
  - Vault内の音声/動画ファイルを右クリックで文字起こし
  - 結果をMarkdownノートとして出力

### 1.4 Google Cloud Speech to Text（非公式）

- 一部のコミュニティプラグインでGoogle Cloud Speech-to-Textを利用するものもあります。

---

## 2. 推奨ワークフロー

WEB会議の録音からMarkdownトランスクリプト作成までの推奨手順です。

### ワークフロー A: OBS Studio + Whisper Transcription（推奨）

```
WEB会議 → OBS Studioで録音 → 音声ファイル保存 → Whisper Transcriptionで文字起こし → Markdownノート完成
```

#### ステップ1: WEB会議の録音

**OBS Studio**（無料）を使用してシステム音声を含めた録音を行います。

1. [OBS Studio](https://obsproject.com/)をインストール
2. 「音声出力キャプチャ」を追加（デスクトップ音声をキャプチャ）
3. 「音声入力キャプチャ」を追加（マイク音声をキャプチャ）
4. 出力形式をmp4またはmkvに設定
5. WEB会議開始時に録画を開始

#### ステップ2: 音声の抽出（必要に応じて）

動画ファイルから音声のみ抽出する場合:

```powershell
# FFmpegを使用（wingetでインストール可能）
winget install FFmpeg
ffmpeg -i meeting.mp4 -vn -acodec libmp3lame meeting.mp3
```

#### ステップ3: Obsidianで文字起こし

1. 音声ファイルをObsidian Vaultにコピー
2. Whisper Transcriptionプラグインで文字起こし実行
3. Markdownノートとして自動保存

---

### ワークフロー B: Windows標準機能 + ローカルWhisper

```
WEB会議 → Windowsサウンドレコーダー/Xbox Game Bar → 音声ファイル → ローカルWhisperで文字起こし → Obsidianに保存
```

#### ステップ1: Windows標準機能で録音

- **Xbox Game Bar** (`Win + G`): ゲームバーの録画機能でデスクトップ音声を含めて録画可能
- **サウンドレコーダー**: Windows 11標準のサウンドレコーダーアプリ（マイク入力のみ）

#### ステップ2: ローカルWhisperで文字起こし（API不要・無料）

```powershell
# Python環境が必要
pip install openai-whisper

# 文字起こし実行（日本語指定）
whisper meeting.mp3 --language ja --output_format txt
```

#### ステップ3: Obsidianに手動で取り込み

生成されたテキストファイルの内容をMarkdownノートにコピー、またはスクリプトで自動化。

---

### ワークフロー C: 会議アプリ内蔵の文字起こし + Obsidian

多くのWEB会議ツールには文字起こし機能が内蔵されています：

| 会議ツール | 内蔵文字起こし | エクスポート形式 |
|-----------|--------------|----------------|
| Microsoft Teams | あり（Teams Premium / Copilot） | VTT, DOCX |
| Zoom | あり（有料プラン） | VTT, TXT |
| Google Meet | あり（Workspace有料プラン） | Google Docs |

エクスポートした文字起こしテキストをObsidianのMarkdownノートに変換して保存します。

---

## 3. 自動化のヒント

### Templaterプラグインとの連携

Obsidianの`Templater`プラグインを使えば、会議ノートのテンプレートを作成できます：

```markdown
---
date: <% tp.date.now("YYYY-MM-DD") %>
type: meeting-transcript
tags: [meeting, transcript]
---

# 会議メモ - <% tp.date.now("YYYY-MM-DD HH:mm") %>

## 参加者
- 

## トランスクリプト

<% tp.file.include("[[transcript_temp]]") %>

## アクションアイテム
- [ ] 
```

### PowerShellスクリプトによる自動化

録音から文字起こし、Obsidianへの保存までを自動化するスクリプト例：

```powershell
# 録音ファイルのパス
$audioFile = "C:\Users\username\recordings\meeting.mp3"
# ObsidianのVaultパス
$vaultPath = "C:\Users\username\ObsidianVault\Meetings"
# 日付
$date = Get-Date -Format "yyyy-MM-dd_HHmm"

# Whisperで文字起こし
whisper $audioFile --language ja --output_format txt --output_dir $env:TEMP

# Markdownファイル作成
$transcript = Get-Content "$env:TEMP\meeting.txt" -Raw
$markdown = @"
---
date: $(Get-Date -Format "yyyy-MM-dd")
type: meeting-transcript
---

# 会議トランスクリプト - $date

$transcript
"@

$markdown | Out-File "$vaultPath\Meeting_$date.md" -Encoding UTF8
Write-Host "トランスクリプトを保存しました: Meeting_$date.md"
```

---

## 4. おすすめの組み合わせ

| 用途 | 録音ツール | 文字起こし | コスト |
|------|-----------|-----------|--------|
| 手軽に始めたい | Xbox Game Bar | Whisper Transcription プラグイン（API） | 低（API従量課金） |
| 高品質・無料 | OBS Studio | ローカルWhisper | 無料（GPU推奨） |
| 企業利用 | Teams/Zoom内蔵録画 | Teams/Zoom内蔵文字起こし | 有料プラン |
| 完全自動化 | OBS Studio + スクリプト | ローカルWhisper + スクリプト | 無料（GPU推奨） |

---

## 5. 注意事項

- **プライバシー・法的配慮**: WEB会議の録音は、参加者全員の同意を得てから行ってください。
- **OpenAI API利用時**: 音声データがOpenAIのサーバーに送信されます。機密情報を含む会議の場合はローカルWhisperの利用を推奨します。
- **日本語精度**: Whisper large-v3モデルは日本語の文字起こし精度が高く推奨されます。ローカル実行にはGPU（VRAM 10GB以上）が望ましいです。
- **ステレオミキサー**: Windows PCでシステム音声を録音する場合、「ステレオミキサー」の有効化が必要な場合があります（サウンド設定 → 録音タブ）。

---

## 参考リンク

- [Obsidian コミュニティプラグイン一覧](https://obsidian.md/plugins)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [OBS Studio](https://obsproject.com/)
- [FFmpeg](https://ffmpeg.org/)
