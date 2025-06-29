# Copilot 利用ガイドライン（プロジェクト専用）

## プロジェクト概要

StudyCardsは日本語学習支援Webアプリケーション（Flask製）です。
- **統一データフォーマット**: `質問,回答` のCSV形式
- **日本語対応**: PDF生成でShift_JIS文字エンコーディング使用
- **対応ブラウザ**: モバイル対応のレスポンシブデザイン

## コーディングスタイル

### Python コード
- **エンコーディング**: CSVファイルはShift_JIS、その他はUTF-8
- **命名規則**: 関数名は日本語コメント付きスネークケース
- **エラーハンドリング**: ユーザーフレンドリーなエラーメッセージ（日本語）
- **フォント処理**: `setup_fonts()`でクロスプラットフォーム対応

### HTML/CSS
- **Bootstrap 5.1.3** 使用
- **Font Awesome 6.0.0** アイコン
- **日本語フォント**: システムフォント優先、フォールバック対応

## 重要な関数・パターン

### データ処理
```python
# 統一フォーマット: 質問,回答
fieldnames = ['質問', '回答']

# エンコーディング自動判定
encodings = ['shift_jis', 'utf-8', 'cp932']
```

### PDF生成
```python
# 日本語フォント設定必須
font_available = setup_fonts()
# HTMLエンティティエスケープ使用
```

### Flask ルーティング
```python
# URLパラメータでメッセージ送信（flash()不使用）
return redirect(url_for('route_name', msg='成功', error='エラー'))
```

## ファイル構成の重要ポイント

- `requirements.txt`: 本番用依存関係のみ
- `requirements-dev.txt`: 開発・テスト用ツール
- `datasets/`: CSVデータ保存（Shift_JIS）
- `templates/`: Jinja2テンプレート（Bootstrap使用）

## テスト・品質管理

### 開発時チェック
```bash
flake8 app.py                           # コード品質
pip-audit --requirement requirements.txt # セキュリティ
```

### GitHub Actions対応
- Ubuntu環境での日本語フォント対応
- Python 3.10+ マトリックステスト
- タイムアウト付きアプリ起動テスト

## Gitコミットメッセージ

- コミットメッセージは以下のPrefixを使用し、内容を明確にします。
  - `feat: 新機能の追加`
  - `fix: バグ修正`
  - `docs: ドキュメントの更新`
  - `style: コードのフォーマット変更`
  - `refactor: リファクタリング`
  - `test: テストの追加・修正`
  - `chore: その他の変更（ビルド、CI等）`

## 注意事項

- **文字エンコーディング**: CSVはShift_JIS必須（日本語環境互換性）
- **フォント依存**: PDF生成は日本語フォント必要
- **モバイル対応**: レスポンシブデザイン維持
- **エラーハンドリング**: 日本語でユーザーフレンドリーに
