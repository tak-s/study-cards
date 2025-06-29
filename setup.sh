#!/bin/bash

# StudyCards セットアップスクリプト (Linux/macOS)

echo "==================================="
echo "StudyCards セットアップ開始"
echo "==================================="

# Pythonの確認
echo "1. Python環境の確認..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "✓ Python3が見つかりました"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo "✓ Pythonが見つかりました"
else
    echo "❌ Pythonが見つかりません。Python 3.10以上をインストールしてください。"
    exit 1
fi

# Pythonバージョンの確認
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "Pythonバージョン: $PYTHON_VERSION"

# 仮想環境の作成
echo ""
echo "2. 仮想環境の作成..."
if [ -d "venv" ]; then
    echo "✓ 仮想環境は既に存在します"
else
    $PYTHON_CMD -m venv venv
    if [ $? -eq 0 ]; then
        echo "✓ 仮想環境を作成しました"
    else
        echo "❌ 仮想環境の作成に失敗しました"
        exit 1
    fi
fi

# 仮想環境の有効化
echo ""
echo "3. 仮想環境の有効化..."
source venv/bin/activate
if [ $? -eq 0 ]; then
    echo "✓ 仮想環境を有効化しました"
else
    echo "❌ 仮想環境の有効化に失敗しました"
    exit 1
fi

# 依存関係のインストール
echo ""
echo "4. 依存関係のインストール..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✓ 依存関係をインストールしました"
else
    echo "❌ 依存関係のインストールに失敗しました"
    exit 1
fi

# datasetsディレクトリの作成
echo ""
echo "5. データセットディレクトリの作成..."
if [ ! -d "datasets" ]; then
    mkdir datasets
    echo "✓ datasetsディレクトリを作成しました"
else
    echo "✓ datasetsディレクトリは既に存在します"
fi

# 日本語フォントの確認・インストール提案
echo ""
echo "6. 日本語フォントの確認..."
FONT_PATHS=(
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
    "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf"
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
)

FONT_FOUND=false
for font_path in "${FONT_PATHS[@]}"; do
    if [ -f "$font_path" ]; then
        echo "✓ 日本語フォントが見つかりました: $font_path"
        FONT_FOUND=true
        break
    fi
done

if [ "$FONT_FOUND" = false ]; then
    echo "⚠️  日本語フォントが見つかりません"
    echo "   PDF生成で日本語が正しく表示されない可能性があります"
    echo "   以下のコマンドでフォントをインストールできます："
    
    # OSの判定とフォントインストールコマンドの提案
    if command -v apt-get &> /dev/null; then
        echo "   sudo apt-get install fonts-dejavu-core fonts-noto-cjk"
    elif command -v yum &> /dev/null; then
        echo "   sudo yum install dejavu-sans-fonts google-noto-sans-cjk-fonts"
    elif command -v brew &> /dev/null; then
        echo "   brew install font-noto-sans-cjk"
    else
        echo "   お使いのOSに適したフォントパッケージをインストールしてください"
    fi
fi

echo ""
echo "==================================="
echo "セットアップ完了！"
echo "==================================="
echo ""
echo "アプリケーションを起動するには："
echo "1. 仮想環境を有効化: source venv/bin/activate"
echo "2. アプリを起動: python app.py"
echo "3. ブラウザで http://localhost:5000 にアクセス"
echo ""
echo "今すぐ起動しますか？ (y/n)"
read -p "> " start_now

if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ] || [ "$start_now" = "yes" ]; then
    echo ""
    echo "アプリケーションを起動しています..."
    echo "Ctrl+C で停止できます"
    echo "ブラウザで http://localhost:5000 にアクセスしてください"
    echo ""
    $PYTHON_CMD app.py
else
    echo ""
    echo "後でアプリケーションを起動する場合は："
    echo "source venv/bin/activate && python app.py"
fi
