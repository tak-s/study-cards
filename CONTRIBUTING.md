# StudyCardsへの貢献

このプロジェクトへの貢献を歓迎します！以下のガイドラインに従ってください。  
本プロジェクトは、主に GitHub Copilot Agent Mode with Claude Sonnet4 で開発されています。

## 貢献の方法

### 1. イシューの報告

バグを発見した場合や新機能の提案がある場合は、まずIssueを作成してください。

**バグ報告に含めるべき情報：**
- OS とバージョン
- Python のバージョン
- エラーメッセージ（あれば）
- 再現手順

**機能要求に含めるべき情報：**
- 機能の詳細な説明
- 使用ケース
- 期待される動作

### 2. 開発環境のセットアップ

**基本セットアップ：**
```bash
git clone https://github.com/tak-s/study-cards.git
cd study-cards
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
pip install -r requirements.txt
```

**開発用ツールのインストール：**
```bash
# コード品質チェックやセキュリティスキャン用ツール
pip install -r requirements-dev.txt

# または個別インストール
pip install flake8 pip-audit pytest black
```

**開発時のコードチェック：**
```bash
# コード品質チェック
flake8 app.py

# セキュリティスキャン
pip-audit --requirement requirements.txt

# コードフォーマット（推奨）
black app.py
```

### 3. プルリクエスト

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/新機能名`)
3. 変更をコミット (`git commit -am '新機能を追加'`)
4. ブランチにプッシュ (`git push origin feature/新機能名`)
5. プルリクエストを作成

### 4. コーディング規約

- PEP 8 に従った Python コードを書く
- 関数やクラスには適切なドキュメント文字列を追加
- 日本語コメントは歓迎（このアプリは日本語学習者向けのため）
- 新機能には適切なエラーハンドリングを実装

### 4. テスト

- 新機能やバグ修正には、可能な限りテストを追加
- 既存のテストが通ることを確認

## 開発環境のセットアップ

```bash
# リポジトリのクローン
git clone https://github.com/tak-s/study-cards.git
cd study-cards

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt

# アプリの起動
python app.py
```

## 重点的に貢献を求める分野

1. **UI/UX の改善**
   - レスポンシブデザインの強化
   - アクセシビリティの向上
   - ユーザビリティの改善

2. **機能追加**
   - 学習進捗の記録・分析機能
   - 問題の難易度設定
   - 複数選択問題の対応
   - 音声読み上げ機能

3. **テスト・品質向上**
   - 自動テストの追加
   - エラーハンドリングの改善
   - パフォーマンスの最適化

4. **ドキュメント**
   - 多言語対応（英語など）
   - チュートリアルの充実
   - API ドキュメント

## 質問・サポート

不明な点がある場合は、Issue を作成するか、以下の方法でお問い合わせください：

- GitHub Issues で質問
- プルリクエストでの議論

## ライセンス

このプロジェクトに貢献することで、あなたの貢献がMITライセンスの下で公開されることに同意したものとみなされます。
