@echo off
chcp 65001 >nul
REM WEB会議録音プログラム - インストールスクリプト

echo ============================================================
echo   WEB会議録音・文字起こしプログラム
echo   インストールスクリプト
echo ============================================================
echo.

REM Pythonがインストールされているか確認
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Pythonがインストールされていません。
    echo.
    echo 以下のURLからPython 3.8以上をダウンロードしてインストールしてください:
    echo https://www.python.org/downloads/
    echo.
    echo インストール時に「Add Python to PATH」にチェックを入れてください。
    pause
    exit /b 1
)

echo [1/4] Pythonバージョンを確認中...
python --version
echo.

REM 仮想環境の作成
echo [2/4] 仮想環境を作成中...
if exist venv (
    echo 仮想環境は既に存在します。
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [エラー] 仮想環境の作成に失敗しました。
        pause
        exit /b 1
    )
    echo 仮想環境を作成しました。
)
echo.

REM 仮想環境の有効化
echo [3/4] 仮想環境を有効化中...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [エラー] 仮想環境の有効化に失敗しました。
    pause
    exit /b 1
)
echo.

REM pipのアップグレード
echo pipを最新版にアップグレード中...
python -m pip install --upgrade pip
echo.

REM 依存パッケージのインストール
echo [4/4] 依存パッケージをインストール中...
echo この処理には10〜30分かかる場合があります。
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo [エラー] パッケージのインストールに失敗しました。
    echo.
    echo インターネット接続を確認して、もう一度実行してください。
    pause
    exit /b 1
)
echo.

echo ============================================================
echo   インストールが完了しました！
echo ============================================================
echo.
echo セットアップチェックを実行しますか？
choice /C YN /M "実行する場合は Y を押してください"

if errorlevel 2 goto skip_check
if errorlevel 1 goto run_check

:run_check
echo.
python setup_check.py
goto end

:skip_check
echo.
echo セットアップチェックをスキップしました。
echo 後で以下のコマンドで実行できます:
echo   python setup_check.py
echo.

:end
echo.
echo ============================================================
echo 次のステップ:
echo ============================================================
echo.
echo 1. セットアップチェック:
echo    python setup_check.py
echo.
echo 2. 音声デバイスの確認:
echo    python web_meeting_recorder.py --list-devices
echo.
echo 3. 録音と文字起こし:
echo    python web_meeting_recorder.py
echo.
echo 詳しくはREADME.mdまたはSETUP_WINDOWS.mdを参照してください。
echo.
pause
