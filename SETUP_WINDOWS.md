# Windows環境セットアップガイド

このガイドでは、Windows PC上でWEB会議録音・文字起こしプログラムを使用するための詳細なセットアップ手順を説明します。

## 目次

1. [システム要件](#システム要件)
2. [Pythonのインストール](#pythonのインストール)
3. [プログラムのダウンロードとセットアップ](#プログラムのダウンロードとセットアップ)
4. [音声デバイスの設定](#音声デバイスの設定)
5. [初回実行とテスト](#初回実行とテスト)
6. [トラブルシューティング](#トラブルシューティング)

## システム要件

- **OS**: Windows 10 (バージョン 1909以降) または Windows 11
- **CPU**: Intel Core i5以上（推奨: Intel Core i7以上）
- **メモリ**: 最低 8GB RAM（推奨: 16GB以上）
- **ストレージ**: 最低 5GB の空き容量
- **音声デバイス**: マイクまたはオーディオ入力デバイス
- **インターネット接続**: 初回セットアップとモデルダウンロードに必要

## Pythonのインストール

### 手順1: Python公式サイトからダウンロード

1. [Python公式ダウンロードページ](https://www.python.org/downloads/)にアクセス
2. 「Download Python 3.11.x」（最新の安定版）をクリック
3. ダウンロードした `python-3.11.x-amd64.exe` を実行

### 手順2: Pythonのインストール

1. インストーラーで **「Add Python to PATH」にチェックを入れる**（重要！）
2. 「Install Now」をクリック
3. インストールが完了するまで待つ
4. 「Close」をクリック

### 手順3: インストールの確認

コマンドプロンプトを開いて以下のコマンドを実行:

```cmd
python --version
```

`Python 3.11.x` のようなバージョン情報が表示されればOKです。

## プログラムのダウンロードとセットアップ

### 方法1: Gitを使用（推奨）

1. **Git for Windowsのインストール**:
   - [Git for Windows](https://git-scm.com/download/win)からダウンロード
   - インストーラーを実行（すべてデフォルト設定でOK）

2. **リポジトリのクローン**:
   ```cmd
   cd C:\Users\YourName\Documents
   git clone https://github.com/Zuppe1231/NewTEST.git
   cd NewTEST
   ```

### 方法2: ZIPファイルをダウンロード

1. GitHubのリポジトリページで「Code」→「Download ZIP」
2. ダウンロードしたZIPファイルを解凍
3. コマンドプロンプトで解凍したフォルダに移動

### 依存パッケージのインストール

```cmd
# 仮想環境の作成（推奨）
python -m venv venv

# 仮想環境の有効化
venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

**注意**: 
- 初回インストールには10〜30分かかる場合があります
- PyTorchなど大きなパッケージがダウンロードされます
- インターネット接続が必要です

## 音声デバイスの設定

### マイク録音の設定

1. **マイクのテスト**:
   - スタートメニュー → 設定 → システム → サウンド
   - 「入力」セクションで使用するマイクを選択
   - 「デバイスのプロパティ」でボリュームを調整
   - 「デバイスのテスト」で録音テスト

2. **プライバシー設定の確認**:
   - 設定 → プライバシーとセキュリティ → マイク
   - 「マイクへのアクセス」が「オン」になっていることを確認
   - 必要に応じて個別のアプリの権限を許可

### システムオーディオ（PC内部の音声）の録音設定

WEB会議の相手の声も含めて録音する場合、以下のいずれかの方法を使用します。

#### 方法A: ステレオミックスの有効化（Windows標準機能）

1. タスクバーのスピーカーアイコンを右クリック → 「サウンドの設定」
2. 「サウンドコントロールパネル」をクリック
3. 「録音」タブを開く
4. 空白部分を右クリック → 「無効なデバイスの表示」にチェック
5. 「ステレオミックス」が表示されたら右クリック → 「有効化」
6. 「ステレオミックス」を右クリック → 「既定のデバイスとして設定」

**注意**: 
- すべてのPCでステレオミックスが利用できるわけではありません
- オーディオドライバーによって名称が異なる場合があります

#### 方法B: 仮想オーディオケーブルの使用（推奨）

1. **VB-CABLEのインストール**:
   - [VB-CABLE公式サイト](https://vb-audio.com/Cable/)からダウンロード
   - `VBCABLE_Driver_Pack43.zip`を解凍
   - 管理者権限で`VBCABLE_Setup_x64.exe`を実行

2. **音声ルーティングの設定**:
   - サウンド設定で再生デバイスを「CABLE Input」に変更
   - WEB会議アプリ（Zoom、Teamsなど）の音声出力を「CABLE Input」に設定
   - 録音プログラムで「CABLE Output」を入力デバイスとして選択

3. **自分の声も聞こえるようにする**（オプション）:
   - 「CABLE Output」のプロパティ → 「聴く」タブ
   - 「このデバイスを聴く」にチェック
   - 再生デバイスを実際のスピーカー/ヘッドフォンに設定

## 初回実行とテスト

### ステップ1: 音声デバイスの確認

```cmd
python web_meeting_recorder.py --list-devices
```

利用可能なデバイス一覧が表示されます。使用したいデバイスの番号（ID）をメモしてください。

### ステップ2: 短時間録音テスト

```cmd
# 10秒間のテスト録音（日本語）
python web_meeting_recorder.py --duration 10 --model tiny
```

**初回実行時の注意**:
- Whisperモデルのダウンロードが始まります（数百MB）
- ダウンロードには数分かかる場合があります

### ステップ3: 結果の確認

1. `recordings/`フォルダに以下のファイルが作成されます:
   - `meeting_YYYYMMDD_HHMMSS.wav` - 録音ファイル
   - `transcript_YYYYMMDD_HHMMSS.md` - トランスクリプト

2. トランスクリプトファイルをメモ帳やVS Codeで開いて内容を確認

### ステップ4: 実際の会議で使用

```cmd
# Enterキーで停止する録音
python web_meeting_recorder.py --language ja

# 60分間の会議（3600秒）
python web_meeting_recorder.py --duration 3600 --model base --language ja
```

## トラブルシューティング

### エラー: `ModuleNotFoundError: No module named 'sounddevice'`

**原因**: 依存パッケージがインストールされていません。

**解決方法**:
```cmd
pip install -r requirements.txt
```

### エラー: 音声が録音されない

**確認事項**:
1. マイクが正しく接続されているか
2. Windowsのマイク設定で有効になっているか
3. 正しいデバイスIDを指定しているか（`--list-devices`で確認）

**解決方法**:
```cmd
# デバイス一覧を確認
python web_meeting_recorder.py --list-devices

# 特定のデバイスを指定
python web_meeting_recorder.py --device 1 --duration 10
```

### エラー: `OSError: [Errno -9996] Invalid input device`

**原因**: 指定したデバイスIDが無効、またはデバイスが使用できません。

**解決方法**:
1. `--list-devices`で正しいデバイスIDを確認
2. 他のアプリケーションがマイクを使用していないか確認
3. デバイスを指定せずに実行（デフォルトデバイスを使用）

### 文字起こしの精度が低い

**改善方法**:
1. より大きなモデルを使用:
   ```cmd
   python web_meeting_recorder.py --model medium
   ```

2. 音質を向上:
   ```cmd
   python web_meeting_recorder.py --sample-rate 44100 --channels 2
   ```

3. 環境の改善:
   - 静かな場所で録音
   - マイクを口に近づける
   - ノイズキャンセリング機能付きマイクを使用

### メモリ不足エラー

**解決方法**:
1. より小さなモデルを使用:
   ```cmd
   python web_meeting_recorder.py --model tiny
   ```

2. 長時間の録音を分割して処理

3. 他のアプリケーションを終了してメモリを解放

### Whisperモデルのダウンロードが遅い

**解決方法**:
1. インターネット接続を確認
2. ファイアウォールやセキュリティソフトウェアの設定を確認
3. 小さいモデル（tiny、base）から試す

## パフォーマンス最適化

### GPU（NVIDIA）を使用する場合

より高速な処理のために、NVIDIA GPUを活用できます。

```cmd
# PyTorch（CUDA版）のインストール
pip uninstall torch torchaudio
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**要件**:
- NVIDIA GPU（GTX 1060以上推奨）
- CUDA対応ドライバー
- 十分なGPUメモリ（最低4GB、推奨8GB以上）

### モデルサイズとパフォーマンス

| モデル | 処理速度（目安） | メモリ使用量 | 推奨環境 |
|--------|-----------------|-------------|----------|
| tiny   | 1時間→5分       | 1GB         | 低スペックPC |
| base   | 1時間→10分      | 1.5GB       | 標準的なPC（推奨） |
| small  | 1時間→20分      | 2GB         | 高性能PC |
| medium | 1時間→40分      | 5GB         | GPU搭載PC |
| large  | 1時間→60分      | 10GB        | ハイエンドGPU |

## 便利な使い方

### バッチファイルの作成

よく使う設定をバッチファイルにすると便利です。

`start_recording.bat`を作成:

```batch
@echo off
cd /d %~dp0
call venv\Scripts\activate
python web_meeting_recorder.py --duration 3600 --language ja --model base
pause
```

ダブルクリックするだけで録音を開始できます。

### タスクスケジューラーで定期実行

定例会議を自動録音することも可能です（タスクスケジューラーで設定）。

## サポート

問題が解決しない場合は、以下の情報を添えてGitHubのIssuesで報告してください:

1. Windowsのバージョン
2. Pythonのバージョン（`python --version`）
3. エラーメッセージの全文
4. 使用したコマンド
5. インストールしたパッケージのバージョン（`pip list`）

## 関連リンク

- [Python公式サイト](https://www.python.org/)
- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [VB-CABLE仮想オーディオデバイス](https://vb-audio.com/Cable/)
- [Git for Windows](https://git-scm.com/download/win)
