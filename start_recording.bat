@echo off
chcp 65001 >nul
REM WEB会議録音プログラム - クイックスタート

echo ============================================================
echo   WEB会議録音・文字起こしプログラム
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

echo プログラムを起動します...
echo Enterキーを押すと録音を停止します。
echo.

REM 録音と文字起こしを実行（日本語、baseモデル）
python web_meeting_recorder.py --language ja --model base

echo.
echo 処理が完了しました。
echo 結果は recordings フォルダに保存されています。
echo.
pause
