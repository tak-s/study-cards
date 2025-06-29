# セットアップ自動化スクリプト

このスクリプトは、StudyCardsの初期セットアップを自動化します。

## 使用方法

### Linux/macOS
```bash
chmod +x setup.sh
./setup.sh
```

### Windows
```bash
setup.bat
```

スクリプトが以下の処理を自動で実行します：

1. Python 仮想環境の作成
2. 依存関係のインストール
3. datasets ディレクトリの作成
4. サンプルデータの生成（オプション）
5. アプリケーションの起動

## 手動セットアップ

自動スクリプトが動作しない場合は、以下の手順で手動セットアップしてください：

1. **Python の確認**
   ```bash
   python --version
   # または
   python3 --version
   ```

2. **仮想環境の作成**
   ```bash
   python -m venv venv
   ```

3. **仮想環境の有効化**
   
   Linux/macOS:
   ```bash
   source venv/bin/activate
   ```
   
   Windows:
   ```bash
   venv\Scripts\activate
   ```

4. **依存関係のインストール**
   ```bash
   pip install -r requirements.txt
   ```

5. **アプリケーションの起動**
   ```bash
   python app.py
   ```

6. **ブラウザでアクセス**
   ```
   http://localhost:5000
   ```

## トラブルシューティング

### よくある問題

**Python が見つからない場合:**
- `python3` コマンドを試してください
- Python 3.10 以上がインストールされていることを確認

**権限エラーの場合:**
- Linux/macOS: `sudo` を使わず、ユーザー権限で実行
- Windows: 管理者として実行

**ポート 5000 が使用中の場合:**
- `app.py` の最後の行でポート番号を変更
- 例: `app.run(debug=True, host='0.0.0.0', port=5001)`

**日本語フォントの問題:**
```bash
# Ubuntu/Debian
sudo apt-get install fonts-dejavu-core fonts-noto-cjk

# CentOS/RHEL
sudo yum install dejavu-sans-fonts google-noto-sans-cjk-fonts
```

## 必要な環境

- Python 3.10 以上
- pip (Python パッケージマネージャー)
- ウェブブラウザ
- 2GB 以上のディスク容量（フォント含む）
