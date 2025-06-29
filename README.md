# StudyCards

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)

あらゆる学習内容（漢字、英単語、歴史、理科など）の暗記を支援するWEBアプリケーションです。

## 🌟 主な特徴

- **シンプルなデータ管理**: 質問と回答のシンプルな学習
- **汎用性**: 漢字、英単語、歴史、理科、数学など、あらゆる暗記学習に対応
- **シンプル**: 統一フォーマット「質問,回答」で管理が簡単
- **印刷対応**: A4サイズの表形式PDFで出力、そのまま印刷して使用可能
- **日本語完全対応**: 漢字・ひらがな・カタカナが正しく表示
- **レスポンシブ**: スマートフォンやタブレットでも使用可能

## 📸 スクリーンショット

![StudyCards Screenshot1](resources/screenshot1.png)
![StudyCards Screenshot2](resources/screenshot2.png)

## 機能

### データセット管理機能
- テーマごとにデータセットを作成
- 統一フォーマット: 質問と回答のシンプルなペア
- 漢字、英単語、歴史年号、理科用語など、どんな内容でも対応
- CSV形式でデータを管理（外部編集可能）
- データのインポート/エクスポート機能

### 問題作成機能
- データセットからランダムに問題を生成
- デフォルト50問（1～データセット全体まで設定可能）
- A4サイズでPDF出力（印刷対応、表形式）
- 問題タイプの選択可能
  - 質問→回答（デフォルト）
  - 回答→質問
- 大量問題対応（50問を超える場合は複数ページ自動生成）

### WEBアプリ機能
- 直感的なユーザーインターフェース
- レスポンシブデザイン（モバイル対応）
- フラッシュメッセージでの操作フィードバック
- 日本語フォント完全対応

## 🚀 クイックスタート

### 自動セットアップ（推奨）

**Linux/macOS:**
```bash
git clone https://github.com/tak-s/study-cards.git
cd study-cards
chmod +x setup.sh
./setup.sh
```

**Windows:**
```bash
git clone https://github.com/tak-s/study-cards.git
cd study-cards
setup.bat
```

### 手動セットアップ

1. **リポジトリのクローン**
```bash
git clone https://github.com/tak-s/study-cards.git
cd study-cards
```

2. **仮想環境の作成と有効化**

**Linux/macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

4. **アプリケーションの起動**
```bash
python app.py
```

5. **ブラウザでアクセス**
```
http://localhost:5000
```

## 📚 使い方

### 1. データセットの作成
1. 「新しいデータセット」をクリック
2. データセット名を入力（例：中学1年漢字、英検3級単語、日本史年号など）
3. 「作成」をクリック

### 2. データの追加
1. 作成したデータセットの「編集」をクリック
2. 質問と回答のペアを入力
   - 漢字学習例：質問「大」→ 回答「だい」
   - 英単語例：質問「school」→ 回答「学校」
   - 歴史例：質問「関ヶ原の戦い」→ 回答「1600年」
3. 必要に応じてCSVファイルを直接編集

### 3. 問題の生成
1. データセットの「問題作成」をクリック
2. 問題数を設定（デフォルト50問）
3. 問題タイプを選択
   - 質問→回答（デフォルト）
   - 回答→質問
4. 「PDFを生成・ダウンロード」をクリック

## 📁 プロジェクト構成

```
study-cards/
├── app.py                      # メインアプリケーション
├── requirements.txt            # 本番用依存関係
├── requirements-dev.txt        # 開発用依存関係（flake8、pip-audit等）
├── README.md                   # このファイル
├── LICENSE                     # MITライセンス
├── SECURITY.md                 # セキュリティガイド
├── CONTRIBUTING.md             # 貢献ガイド
├── SETUP.md                    # 詳細セットアップガイド
├── setup.sh                    # Linux/macOS用セットアップ
├── setup.bat                   # Windows用セットアップ
├── templates/                  # HTMLテンプレート
│   ├── base.html              # ベーステンプレート
│   ├── index.html             # ホームページ
│   ├── create_dataset.html    # データセット作成ページ
│   ├── edit_dataset.html      # データセット編集ページ
│   ├── generate_quiz.html     # 問題生成ページ
│   └── import_dataset.html    # データインポートページ
└── datasets/                   # データセット保存ディレクトリ
    ├── 英単語.csv             # サンプル英単語データ
    └── 世界の国と首都.csv     # サンプル地理データ
```

## CSV形式について

### 統一フォーマット（推奨）
すべてのデータセットは「質問,回答」の統一フォーマットで管理されます：

```csv
質問,回答
大,だい
小,しょう
学校,がっこう
```

または英語ヘッダー版：
```csv
question,answer
school,学校
teacher,先生
apple,りんご
```

### 使用例

**漢字学習データセット:**
```csv
質問,回答
大,だい
学校,がっこう
先生,せんせい
```

**英単語学習データセット:**
```csv
質問,回答
school,学校
teacher,先生
student,学生
```

**歴史学習データセット:**
```csv
質問,回答
関ヶ原の戦い,1600年
江戸幕府開始,1603年
明治維新,1868年
```

**理科学習データセット:**
```csv
質問,回答
水の化学式,H2O
酸素の化学記号,O
炭素の化学記号,C
```

## 特徴

- **汎用性**: 漢字、英単語、歴史、理科、数学など、あらゆる暗記学習に対応
- **統一フォーマット**: シンプルな「質問,回答」形式で管理が簡単
- **手軽なデータ管理**: CSV形式なのでExcelやテキストエディタで編集可能
- **印刷対応**: A4サイズの表形式PDFで出力、そのまま印刷して使用可能
- **大量問題対応**: 50問を超える場合は自動で複数ページに分割
- **柔軟な問題設定**: 問題数や出題方向を自由に設定
- **日本語完全対応**: 漢字・ひらがな・カタカナが正しく表示
- **レスポンシブデザイン**: スマートフォンやタブレットでも使用可能
- **データインポート/エクスポート**: 既存データの再利用が簡単

### PDF生成時に日本語が表示されない場合
システムに日本語フォントがインストールされていない可能性があります。以下のパッケージをインストールしてください：

**Ubuntu/Debian:**
```bash
sudo apt-get install fonts-dejavu-core
```

**CentOS/RHEL:**
```bash
sudo yum install dejavu-sans-fonts
```

### ポート5000が使用中の場合
app.pyの最後の行を編集してポート番号を変更してください：
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # ポート番号を変更
```

## 🔒 セキュリティ

本番環境で使用する場合は、[SECURITY.md](SECURITY.md) を必ずお読みください。

## 🤝 貢献

プロジェクトへの貢献を歓迎します！詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📄 ライセンス

このプロジェクトは[MITライセンス](LICENSE)の下で公開されています。

## 🆘 サポート・質問

- バグ報告: [Issues](https://github.com/tak-s/study-cards/issues)
- 機能要求: [Issues](https://github.com/tak-s/study-cards/issues)
- 質問: [Discussions](https://github.com/tak-s/study-cards/discussions)

## ⚠️ 注意事項

- datasets内のサンプルデータは学習目的で用意したものではありません。実際に使用する際は、適切なデータセットを用意してください。
- 本番環境で使用する際は適切なセキュリティ設定を行ってください
- 大量のデータを扱う場合はサーバーのリソースにご注意ください
