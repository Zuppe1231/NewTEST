@echo off
chcp 65001 >nul
REM 音声デバイスの確認

echo ============================================================
echo   音声デバイスの確認
echo ============================================================
echo.

REM 仮想環境の有効化
if not exist venv (
    echo [エラー] 仮想環境が見つかりません。
    echo まず install.bat を実行してください。
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo 利用可能な音声デバイスを一覧表示します...
echo.

python web_meeting_recorder.py --list-devices

echo.
pause
