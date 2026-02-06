# Meeting Transcriber - Obsidian プラグイン

WEB会議を録音してトランスクリプト（文字起こし）をマークダウンファイルで作成するObsidianプラグインです。

## 機能

- 🎙️ **リアルタイム録音**: マイクまたはシステムオーディオからの音声を録音
- 📝 **自動文字起こし**: 録音中にリアルタイムで音声をテキストに変換
- 📁 **自動保存**: トランスクリプトを自動的にマークダウンファイルとして保存
- ⏱️ **タイムスタンプ**: 発言ごとにタイムスタンプを追加（オプション）
- 🌍 **多言語対応**: 日本語、英語、中国語、韓国語など複数の言語をサポート
- 🤖 **複数の音声認識エンジン対応**:
  - Web Speech API (無料、Chrome推奨)
  - OpenAI Whisper API (有料、高精度)

## インストール方法

### 手動インストール

1. このリポジトリをクローンまたはダウンロード
2. `npm install` で依存関係をインストール
3. `npm run build` でプラグインをビルド
4. `main.js`、`manifest.json`、`styles.css` を Obsidianのプラグインフォルダにコピー
   - Windowsの場合: `%APPDATA%/Obsidian/plugins/meeting-transcriber/`
   - macOSの場合: `~/Library/Application Support/obsidian/plugins/meeting-transcriber/`
   - Linuxの場合: `~/.config/obsidian/plugins/meeting-transcriber/`
5. Obsidianを再起動し、設定からプラグインを有効化

### 開発モード

```bash
npm install
npm run dev
```

開発モードでは、ファイルの変更を監視し、自動的に再ビルドされます。

## 使い方

### 基本的な使い方

1. **録音を開始**:
   - 左サイドバーのマイクアイコンをクリック、または
   - コマンドパレット（Ctrl/Cmd + P）から「会議の録音を開始」を選択

2. **録音モーダルが表示されます**:
   - 「録音開始」ボタンをクリックして録音を開始
   - リアルタイムでトランスクリプトが表示されます（Web Speech API使用時）

3. **録音を停止**:
   - 「録音停止」ボタンをクリック
   - トランスクリプトが自動的にマークダウンファイルとして保存されます

### 設定

設定画面（Settings → Meeting Transcriber）から以下の項目を設定できます：

- **保存フォルダ**: トランスクリプトを保存するフォルダ（デフォルト: `Meetings`）
- **ファイル名フォーマット**: ファイル名のフォーマット（`{{date}}`と`{{time}}`を使用可能）
- **タイムスタンプを含める**: トランスクリプトにタイムスタンプを含めるかどうか
- **言語**: 音声認識の言語（日本語、英語など）
- **トランスクリプションサービス**: 
  - Web Speech API（無料、Chrome推奨）
  - OpenAI Whisper API（有料、高精度）
- **OpenAI APIキー**: Whisper APIを使用する場合に必要

## 生成されるマークダウンファイルの例

```markdown
# 会議トランスクリプト

**日付**: 2024-01-15
**時刻**: 14:30:00

---

## トランスクリプト

[14:30:05] こんにちは、今日の会議を始めます。

[14:30:15] 議題は新製品の開発についてです。

[14:30:30] まず、現状の進捗を確認しましょう。

---

*このトランスクリプトは Meeting Transcriber プラグインによって自動生成されました*
```

## 対応ブラウザ・環境

### Web Speech API
- Google Chrome / Microsoft Edge (推奨)
- Chromiumベースのブラウザ
- デスクトップ版のみ（Windows、macOS、Linux）

### Whisper API
- すべてのプラットフォームで動作
- OpenAI APIキーが必要

## トラブルシューティング

### マイクへのアクセスが拒否される
- ブラウザの設定でマイクへのアクセスを許可してください
- Obsidianを再起動してみてください

### 音声認識が動作しない
- Google ChromeまたはMicrosoft Edgeを使用していることを確認してください
- インターネット接続を確認してください（Web Speech APIはオンラインで動作します）
- 別の音声認識サービス（Whisper API）を試してみてください

### Whisper APIが動作しない
- OpenAI APIキーが正しく設定されているか確認してください
- APIキーに十分なクレジットがあるか確認してください
- インターネット接続を確認してください

## プライバシーとセキュリティ

- **Web Speech API**: 音声データはGoogleのサーバーに送信されて処理されます
- **Whisper API**: 音声データはOpenAIのサーバーに送信されて処理されます
- APIキーはObsidianのプラグイン設定にローカル保存されます
- 録音データとトランスクリプトはすべてローカルに保存されます

## 技術スタック

- TypeScript
- Obsidian API
- Web Speech API / SpeechRecognition
- MediaRecorder API
- OpenAI Whisper API

## ライセンス

MIT

## 貢献

バグ報告や機能要望は、GitHubのIssuesでお願いします。
プルリクエストも歓迎します！

## 開発者

Meeting Transcriber Team

## 更新履歴

### 1.0.0 (2024-01-15)
- 初回リリース
- 基本的な録音・転写機能
- Web Speech API対応
- Whisper API対応
- リアルタイムトランスクリプション
- マークダウンファイル自動生成

## サポート

問題が発生した場合は、GitHubのIssuesでご報告ください。
