@echo off
chcp 65001 > nul

echo ===================================
echo StudyCards セットアップ開始
echo ===================================

REM Pythonの確認
echo 1. Python環境の確認...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    echo ✓ Pythonが見つかりました
) else (
    python3 --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python3
        echo ✓ Python3が見つかりました
    ) else (
        echo ❌ Pythonが見つかりません。Python 3.10以上をインストールしてください。
        echo https://www.python.org/downloads/ からダウンロードできます。
        pause
        exit /b 1
    )
)

REM Pythonバージョンの表示
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version') do set PYTHON_VERSION=%%i
echo Pythonバージョン: %PYTHON_VERSION%

REM 仮想環境の作成
echo.
echo 2. 仮想環境の作成...
if exist "venv" (
    echo ✓ 仮想環境は既に存在します
) else (
    %PYTHON_CMD% -m venv venv
    if %errorlevel% equ 0 (
        echo ✓ 仮想環境を作成しました
    ) else (
        echo ❌ 仮想環境の作成に失敗しました
        pause
        exit /b 1
    )
)

REM 仮想環境の有効化
echo.
echo 3. 仮想環境の有効化...
call venv\Scripts\activate.bat
if %errorlevel% equ 0 (
    echo ✓ 仮想環境を有効化しました
) else (
    echo ❌ 仮想環境の有効化に失敗しました
    pause
    exit /b 1
)

REM 依存関係のインストール
echo.
echo 4. 依存関係のインストール...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% equ 0 (
    echo ✓ 依存関係をインストールしました
) else (
    echo ❌ 依存関係のインストールに失敗しました
    pause
    exit /b 1
)

REM datasetsディレクトリの作成
echo.
echo 5. データセットディレクトリの作成...
if not exist "datasets" (
    mkdir datasets
    echo ✓ datasetsディレクトリを作成しました
) else (
    echo ✓ datasetsディレクトリは既に存在します
)

REM フォントの確認
echo.
echo 6. 日本語フォントの確認...
set FONT_FOUND=false

if exist "C:\Windows\Fonts\msgothic.ttc" (
    echo ✓ 日本語フォントが見つかりました: MS Gothic
    set FONT_FOUND=true
) else if exist "C:\Windows\Fonts\meiryo.ttc" (
    echo ✓ 日本語フォントが見つかりました: Meiryo
    set FONT_FOUND=true
) else if exist "C:\Windows\Fonts\msmincho.ttc" (
    echo ✓ 日本語フォントが見つかりました: MS Mincho
    set FONT_FOUND=true
)

if "%FONT_FOUND%"=="false" (
    echo ⚠️  標準的な日本語フォントが見つかりません
    echo    PDF生成で日本語が正しく表示されない可能性があります
    echo    Windowsの設定で日本語フォントを確認してください
)

echo.
echo ===================================
echo セットアップ完了！
echo ===================================
echo.
echo アプリケーションを起動するには：
echo 1. 仮想環境を有効化: venv\Scripts\activate.bat
echo 2. アプリを起動: python app.py
echo 3. ブラウザで http://localhost:5000 にアクセス
echo.
set /p start_now="今すぐ起動しますか？ (y/n): "

if /i "%start_now%"=="y" goto start_app
if /i "%start_now%"=="yes" goto start_app
goto end

:start_app
echo.
echo アプリケーションを起動しています...
echo Ctrl+C で停止できます
echo ブラウザで http://localhost:5000 にアクセスしてください
echo.
python app.py
goto end

:end
echo.
echo 後でアプリケーションを起動する場合は：
echo venv\Scripts\activate.bat ^&^& python app.py
pause
