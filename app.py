from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
import csv
import os
import random
from datetime import datetime, timedelta
import io
import base64
import time
import uuid
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.permanent_session_lifetime = timedelta(minutes=30)

# データセット保存ディレクトリ
DATASETS_DIR = 'datasets'

# オンラインテストセッション管理（メモリ内）
online_test_sessions = {}

def set_flash_message(message, message_type='info'):
    """セッションにメッセージを設定"""
    if 'flash_messages' not in session:
        session['flash_messages'] = {}
    if 'message_counter' not in session:
        session['message_counter'] = 0
    
    # メッセージID生成
    session['message_counter'] += 1
    message_id = f"msg_{session['message_counter']:03d}"
    
    # 期限切れメッセージをクリーンアップ
    cleanup_expired_messages()
    
    # メッセージ数制限（10件まで）
    if len(session['flash_messages']) >= 10:
        # 最も古いメッセージを削除
        oldest_id = min(session['flash_messages'].keys())
        del session['flash_messages'][oldest_id]
    
    # メッセージを保存
    current_time = time.time()
    session['flash_messages'][message_id] = {
        'text': message,
        'type': message_type,
        'timestamp': current_time,
        'expires_at': current_time + 300  # 5分後に期限切れ
    }
    session.permanent = True
    
    return message_id

def get_flash_message():
    """セッションからメッセージを取得して削除"""
    cleanup_expired_messages()
    
    if 'flash_messages' not in session or not session['flash_messages']:
        return '', 'info'
    
    # 最新のメッセージを取得
    message_id = max(session['flash_messages'].keys())
    message_data = session['flash_messages'].pop(message_id)
    
    return message_data['text'], message_data['type']

def cleanup_expired_messages():
    """期限切れメッセージを削除"""
    if 'flash_messages' not in session:
        return
    
    current_time = time.time()
    expired_ids = [
        msg_id for msg_id, msg_data in session['flash_messages'].items()
        if current_time > msg_data['expires_at']
    ]
    
    for msg_id in expired_ids:
        del session['flash_messages'][msg_id]

def get_message_and_type(request):
    """セッションからメッセージとタイプを取得"""
    return get_flash_message()

# 日本語フォントの設定
def setup_fonts():
    """日本語フォントの設定"""
    try:
        # システムにある日本語フォントを探して登録
        font_paths = [
            # Linux系 - 新しくインストールしたフォントを優先
            '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf',
            '/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/noto/NotoSansJP-Regular.otf',
            # macOS
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/Library/Fonts/Arial Unicode MS.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            # Windows
            '/Windows/Fonts/msgothic.ttc',
            '/Windows/Fonts/meiryo.ttc',
            '/Windows/Fonts/msmincho.ttc'
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    # より安全なフォント登録
                    if font_path.endswith('.ttc'):
                        # .ttcファイルの場合、最初のフォントを使用
                        pdfmetrics.registerFont(TTFont('Japanese', font_path, subfontIndex=0))
                    else:
                        pdfmetrics.registerFont(TTFont('Japanese', font_path))
                    print(f"Font registered successfully: {font_path}")
                    
                    # フォントが正しく登録されたかテスト
                    from reportlab.lib.fonts import addMapping
                    addMapping('Japanese', 0, 0, 'Japanese')  # normal
                    addMapping('Japanese', 1, 0, 'Japanese')  # bold
                    addMapping('Japanese', 0, 1, 'Japanese')  # italic
                    addMapping('Japanese', 1, 1, 'Japanese')  # bold italic
                    
                    return True
                except Exception as font_error:
                    print(f"Failed to register font {font_path}: {font_error}")
                    continue
        
        # デフォルトフォントでUnicode対応を試行
        print("No Japanese font found, trying default Unicode support...")
        return False
        
    except Exception as e:
        print(f"Font setup error: {e}")
        return False

def download_noto_font():
    """Notoフォントをダウンロードして登録"""
    try:
        import urllib.request
        font_dir = os.path.join(os.getcwd(), 'fonts')
        if not os.path.exists(font_dir):
            os.makedirs(font_dir)
        
        font_path = os.path.join(font_dir, 'NotoSansCJK-Regular.ttc')
        
        if not os.path.exists(font_path):
            print("Downloading Noto Sans CJK font...")
            url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTC/NotoSansCJK-Regular.ttc"
            urllib.request.urlretrieve(url, font_path)
        
        pdfmetrics.registerFont(TTFont('Japanese', font_path))
        print(f"Downloaded font registered: {font_path}")
        return True
    except Exception as e:
        print(f"Failed to download font: {e}")
        # フォールバック: reportlabのデフォルトフォントを使用
        return False

def get_dataset_type(filename):
    """CSVファイルのヘッダーからデータセットタイプを判定（廃止予定）"""
    # 統一フォーマット「質問,回答」に移行
    return 'unified'

def calculate_proficiency_score(correct_count, total_attempts):
    """習熟度スコアを計算（0.0-1.0）"""
    if total_attempts == 0:
        return 0.0
    return round(correct_count / total_attempts, 3)

# オンラインテスト機能
def create_online_test_session(filename, questions, settings, is_quick_10=False):
    """オンラインテストセッションを作成"""
    session_id = str(uuid.uuid4())
    
    online_test_sessions[session_id] = {
        'filename': filename,
        'questions': questions,
        'current_question': 0,
        'user_judgments': [None] * len(questions),  # True/False/None
        'question_states': ['question'] * len(questions),  # "question"/"answer"/"judged"
        'start_time': datetime.now(),
        'settings': settings,
        'is_quick_10': is_quick_10,  # クイック10フラグ
        'results': {
            'score': 0,
            'total_questions': len(questions)
        }
    }
    
    # 期限切れセッションのクリーンアップ
    cleanup_expired_test_sessions()
    
    return session_id

def get_online_test_session(session_id):
    """オンラインテストセッションを取得"""
    return online_test_sessions.get(session_id)

def cleanup_expired_test_sessions():
    """期限切れテストセッションを削除（1時間経過）"""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, session_data in online_test_sessions.items():
        if current_time - session_data['start_time'] > timedelta(hours=1):
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del online_test_sessions[session_id]

def update_question_proficiency(filename, question_index, is_correct):
    """問題の習熟度データを更新"""
    data = load_dataset(filename)
    
    if 0 <= question_index < len(data):
        item = data[question_index]
        
        # 試行回数を増加
        item['総試行回数'] = int(item['総試行回数']) + 1
        
        # 正解の場合は正解数を増加
        if is_correct:
            item['正解数'] = int(item['正解数']) + 1
        
        # 習熟度スコアを再計算
        item['習熟度スコア'] = calculate_proficiency_score(
            int(item['正解数']), int(item['総試行回数'])
        )
        
        # データセットを保存
        fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
        return save_dataset(filename, data, fieldnames)
    
    return False


def ensure_datasets_dir():
    """データセットディレクトリの作成"""
    if not os.path.exists(DATASETS_DIR):
        os.makedirs(DATASETS_DIR)

def get_datasets():
    """利用可能なデータセット一覧を取得（統計情報付き）"""
    ensure_datasets_dir()
    datasets = []
    for filename in os.listdir(DATASETS_DIR):
        if filename.endswith('.csv'):
            name = filename[:-4]  # .csvを除去
            stats = get_dataset_stats(filename)
            datasets.append({
                'name': name,
                'filename': filename,
                'path': os.path.join(DATASETS_DIR, filename),
                'stats': stats
            })
    
    # 日本語対応の名前順でソート
    import locale
    try:
        # 日本語ロケールを設定（利用可能な場合）
        locale.setlocale(locale.LC_ALL, 'ja_JP.UTF-8')
    except locale.Error:
        try:
            # フォールバック: C.UTF-8ロケール
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except locale.Error:
            # フォールバック: デフォルトロケール
            pass
    
    # 名前でソート（日本語対応）
    datasets.sort(key=lambda x: locale.strxfrm(x['name']))
    
    return datasets

def get_dataset_stats(data_or_filename):
    """データセットの統計情報を取得（習熟度スコアベース）"""
    # データまたはファイル名を受け取り、データを取得
    if isinstance(data_or_filename, str):
        # ファイル名が渡された場合
        data = load_dataset(data_or_filename)
    else:
        # データリストが直接渡された場合
        data = data_or_filename
    
    if not data:
        return {
            'total_problems': 0,
            'average_mastery': 0.0,
            'total_attempts': 0,
            'total_correct': 0,
            'studied_problems': 0
        }
    
    total_problems = len(data)
    total_attempts = 0
    total_correct = 0
    mastery_sum = 0.0
    
    # 習熟度ベースの統計
    mastered_problems = 0      # 習熟度80%以上（習得済み）
    learning_problems = 0      # 習熟度60-79%（学習中）  
    struggling_problems = 0    # 習熟度1-59%（要練習）
    untouched_problems = 0     # 習熟度0%（未着手）
    
    for item in data:
        try:
            correct = int(item.get('正解数', 0) or 0)
            attempts = int(item.get('総試行回数', 0) or 0)
            mastery_score = float(item.get('習熟度スコア', 0.0) or 0.0)
            
            total_correct += correct
            total_attempts += attempts
            mastery_sum += mastery_score
            
            # 習熟度に基づく分類
            if mastery_score >= 0.8:
                mastered_problems += 1    # 習得済み
            elif mastery_score >= 0.6:
                learning_problems += 1    # 学習中
            elif mastery_score > 0.0:
                struggling_problems += 1  # 要練習
            else:
                untouched_problems += 1   # 未着手
                
        except (ValueError, TypeError):
            untouched_problems += 1
            continue
    
    # 平均習熟度スコアを計算（0-100の範囲で表示）
    average_mastery = (mastery_sum / total_problems * 100) if total_problems > 0 else 0.0
    
    # 取り組み済み問題数（習熟度が0%を超える問題）
    attempted_problems = total_problems - untouched_problems
    
    return {
        'total_problems': total_problems,
        'average_mastery': round(average_mastery, 1),
        'total_attempts': total_attempts,
        'total_correct': total_correct,
        'mastered_problems': mastered_problems,      # 習得済み（80%以上）
        'learning_problems': learning_problems,      # 学習中（60-79%）
        'struggling_problems': struggling_problems,  # 要練習（1-59%）
        'untouched_problems': untouched_problems,    # 未着手（0%）
        'attempted_problems': attempted_problems,    # 取り組み済み（0%を超える）
        # 旧形式との互換性のため残す
        'studied_problems': attempted_problems
    }

def get_weak_problems(data, threshold=0.6):
    """習熟度が閾値未満の問題を抽出"""
    weak_problems = []
    for item in data:
        try:
            mastery_score = float(item.get('習熟度スコア', 0.0) or 0.0)
            if mastery_score < threshold:
                weak_problems.append(item)
        except (ValueError, TypeError):
            # 習熟度スコアが不正な場合は弱点問題として扱う
            weak_problems.append(item)
    return weak_problems

def get_mastery_distribution(data):
    """習熟度分布を取得（UI表示用）"""
    total_problems = len(data)
    if total_problems == 0:
        return {'weak': 0, 'moderate': 0, 'strong': 0, 'total': 0}
    
    weak_count = 0
    moderate_count = 0
    strong_count = 0
    
    for item in data:
        try:
            mastery_score = float(item.get('習熟度スコア', 0.0) or 0.0)
            if mastery_score < 0.6:
                weak_count += 1
            elif mastery_score < 0.8:
                moderate_count += 1
            else:
                strong_count += 1
        except (ValueError, TypeError):
            # 習熟度スコアが不正な場合は弱点問題として扱う
            weak_count += 1
    
    return {
        'weak': weak_count,
        'moderate': moderate_count,
        'strong': strong_count,
        'total': total_problems
    }

def load_dataset(filename):
    """CSVファイルからデータセットを読み込み（習熟度データ対応）"""
    filepath = os.path.join(DATASETS_DIR, filename)
    data = []
    if os.path.exists(filepath):
        # エンコーディングを試行する順序
        encodings = ['shift_jis', 'utf-8', 'cp932']
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    # ファイルの最初の行を読んでCSVかTSVかを判定
                    first_line = f.readline()
                    f.seek(0)  # ファイルポインタを先頭に戻す
                    
                    # タブかカンマで区切られているかを判定
                    delimiter = '\t' if '\t' in first_line and ',' not in first_line else ','
                    delimiter_name = 'TAB' if delimiter == '\t' else 'COMMA'
                    print(f"Detected delimiter: {delimiter_name} for file {filename}")
                    
                    reader = csv.DictReader(f, delimiter=delimiter)
                    
                    for row_num, row in enumerate(reader, 1):
                        try:
                            # フィールド名の前後の空白を除去
                            cleaned_row = {key.strip(): value.strip() if value else '' for key, value in row.items()}
                            
                            # 番号がない旧形式の場合はデフォルト値を設定
                            if '番号' not in cleaned_row:
                                cleaned_row['番号'] = len(data) + 1
                            
                            # 習熟度データがない旧形式の場合はデフォルト値を設定
                            if '正解数' not in cleaned_row:
                                cleaned_row['正解数'] = 0
                            if '総試行回数' not in cleaned_row:
                                cleaned_row['総試行回数'] = 0
                            if '習熟度スコア' not in cleaned_row:
                                cleaned_row['習熟度スコア'] = 0.0
                            
                            # 数値型に変換
                            try:
                                cleaned_row['番号'] = int(cleaned_row['番号']) if cleaned_row['番号'] else len(data) + 1
                                cleaned_row['正解数'] = int(cleaned_row['正解数']) if cleaned_row['正解数'] else 0
                                cleaned_row['総試行回数'] = int(cleaned_row['総試行回数']) if cleaned_row['総試行回数'] else 0
                                cleaned_row['習熟度スコア'] = float(cleaned_row['習熟度スコア']) if cleaned_row['習熟度スコア'] else 0.0
                            except (ValueError, TypeError) as conv_error:
                                print(f"Number conversion error in row {row_num}: {conv_error}")
                                cleaned_row['番号'] = len(data) + 1
                                cleaned_row['正解数'] = 0
                                cleaned_row['総試行回数'] = 0
                                cleaned_row['習熟度スコア'] = 0.0
                            
                            data.append(cleaned_row)
                            
                        except Exception as row_error:
                            print(f"Error processing row {row_num}: {row_error}")
                            continue
                    
                    print(f"Successfully loaded {len(data)} rows from {filename} with {encoding} encoding")
                    break  # 成功したらループを抜ける
                    
            except UnicodeDecodeError as decode_error:
                print(f"Failed to decode {filename} with {encoding}: {decode_error}")
                continue
            except Exception as e:
                print(f"Error loading dataset {filename} with {encoding}: {e}")
                continue
        
        if not data:
            print(f"Failed to load any data from {filename}")
    
    return data

def save_dataset(filename, data, fieldnames=None):
    """データセットをCSVファイルに保存（習熟度データ含む）"""
    ensure_datasets_dir()
    filepath = os.path.join(DATASETS_DIR, filename)
    
    # 拡張フォーマット: 番号,質問,回答,正解数,総試行回数,習熟度スコア
    if fieldnames is None:
        fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
    
    # データの習熟度フィールドを確保
    enhanced_data = []
    for i, item in enumerate(data):
        enhanced_item = item.copy()
        # 番号がない場合は自動設定
        if '番号' not in enhanced_item:
            enhanced_item['番号'] = i + 1
        # 習熟度データがない場合はデフォルト値を設定
        if '正解数' not in enhanced_item:
            enhanced_item['正解数'] = 0
        if '総試行回数' not in enhanced_item:
            enhanced_item['総試行回数'] = 0
        if '習熟度スコア' not in enhanced_item:
            enhanced_item['習熟度スコア'] = 0.0
        enhanced_data.append(enhanced_item)
    
    try:
        # Shift_JISでの保存を試行（エラー時はUTF-8で保存）
        try:
            with open(filepath, 'w', encoding='shift_jis', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(enhanced_data)
            print(f"Dataset saved successfully with shift_jis encoding: {filename}")
        except UnicodeEncodeError as encode_error:
            print(f"Shift_JIS encoding failed for {filename}: {encode_error}")
            print("Saving with UTF-8 encoding instead...")
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(enhanced_data)
            print(f"Dataset saved successfully with UTF-8 encoding: {filename}")
        return True
    except Exception as e:
        print(f"Error saving dataset {filename}: {e}")
        return False

@app.route('/')
def index():
    """メインダッシュボードページ"""
    datasets = get_datasets()
    message, message_type = get_message_and_type(request)
    return render_template('index.html', datasets=datasets, message=message, message_type=message_type)

@app.route('/api/datasets')
def api_datasets():
    """データセット一覧API（AJAX用）"""
    datasets = get_datasets()
    return jsonify(datasets)

@app.route('/create_dataset')
def create_dataset():
    """新しいデータセット作成ページ"""
    message, message_type = get_message_and_type(request)
    return render_template('create_dataset.html', message=message, message_type=message_type)

@app.route('/save_dataset', methods=['POST'])
def save_dataset_route():
    """データセット保存処理"""
    name = request.form.get('name')
    
    if not name:
        set_flash_message('データセット名を入力してください。', 'error')
        return redirect(url_for('create_dataset'))
    
    filename = f"{name}.csv"
    
    # 重複チェック
    if os.path.exists(os.path.join(DATASETS_DIR, filename)):
        set_flash_message(f'データセット "{name}" は既に存在します。別の名前を使用してください。', 'error')
        return redirect(url_for('create_dataset'))
    
    # 拡張フォーマット: 番号,質問,回答,正解数,総試行回数,習熟度スコア
    fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
    data = []
    
    if save_dataset(filename, data, fieldnames):
        set_flash_message('データセットを作成しました。', 'success')
        return redirect(url_for('edit_dataset', filename=filename))
    else:
        set_flash_message('データセットの作成に失敗しました。', 'error')
        return redirect(url_for('create_dataset'))

@app.route('/edit_dataset/<filename>')
def edit_dataset(filename):
    """データセット編集ページ"""
    data = load_dataset(filename)
    dataset_name = filename[:-4]  # .csvを除去
    
    # 統計情報を取得
    stats = get_dataset_stats(data)
    
    # 拡張フォーマット: 番号,質問,回答,正解数,総試行回数,習熟度スコア
    fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
    
    message, message_type = get_message_and_type(request)
    
    return render_template('edit_dataset.html', 
                         dataset_name=dataset_name,
                         filename=filename,
                         data=data,
                         stats=stats,
                         fieldnames=fieldnames,
                         message=message,
                         message_type=message_type)

@app.route('/add_item/<filename>', methods=['POST'])
def add_item(filename):
    """データセットにアイテム追加"""
    data = load_dataset(filename)
    
    # 次の番号を計算
    next_number = max([int(item.get('番号', 0)) for item in data], default=0) + 1
    
    # 拡張フォーマット: 番号,質問,回答,正解数,総試行回数,習熟度スコア
    fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
    new_item = {
        '番号': next_number,
        '質問': request.form.get('question', ''),
        '回答': request.form.get('answer', ''),
        '正解数': 0,
        '総試行回数': 0,
        '習熟度スコア': 0.0
    }
    
    # 空のフィールドチェック（必須フィールドのみ）
    if not new_item['質問'] or not new_item['回答']:
        set_flash_message('質問と回答を入力してください。', 'error')
        return redirect(url_for('edit_dataset', filename=filename))
    
    data.append(new_item)
    
    if save_dataset(filename, data, fieldnames):
        set_flash_message('アイテムを追加しました。', 'success')
        return redirect(url_for('edit_dataset', filename=filename))
    else:
        set_flash_message('アイテムの追加に失敗しました。', 'error')
        return redirect(url_for('edit_dataset', filename=filename))

@app.route('/delete_item/<filename>/<int:index>')
def delete_item(filename, index):
    """データセットからアイテム削除"""
    data = load_dataset(filename)
    
    if 0 <= index < len(data):
        # 拡張フォーマット: 番号,質問,回答,正解数,総試行回数,習熟度スコア
        fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
        
        data.pop(index)
        
        # 削除後、番号を振り直し
        for i, item in enumerate(data):
            item['番号'] = i + 1
        
        if save_dataset(filename, data, fieldnames):
            set_flash_message('アイテムを削除しました。', 'success')
            return redirect(url_for('edit_dataset', filename=filename))
        else:
            set_flash_message('アイテムの削除に失敗しました。', 'error')
            return redirect(url_for('edit_dataset', filename=filename))
    else:
        set_flash_message('無効なアイテムです。', 'error')
        return redirect(url_for('edit_dataset', filename=filename))

@app.route('/reset_mastery/<filename>/<int:index>')
def reset_single_mastery(filename, index):
    """個別問題の習熟度をリセット"""
    data = load_dataset(filename)
    
    if 0 <= index < len(data):
        # 習熟度データをリセット
        data[index]['正解数'] = 0
        data[index]['総試行回数'] = 0
        data[index]['習熟度スコア'] = 0.0
        
        fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
        
        if save_dataset(filename, data, fieldnames):
            set_flash_message('習熟度をリセットしました。', 'success')
            return redirect(url_for('edit_dataset', filename=filename))
        else:
            set_flash_message('習熟度のリセットに失敗しました。', 'error')
            return redirect(url_for('edit_dataset', filename=filename))
    else:
        set_flash_message('無効なアイテムです。', 'error')
        return redirect(url_for('edit_dataset', filename=filename))

@app.route('/reset_all_mastery/<filename>')
def reset_all_mastery(filename):
    """全問題の習熟度を一括リセット"""
    data = load_dataset(filename)
    
    if not data:
        set_flash_message('データセットが空です。', 'error')
        return redirect(url_for('edit_dataset', filename=filename))
    
    # 全問題の習熟度データをリセット
    for item in data:
        item['正解数'] = 0
        item['総試行回数'] = 0
        item['習熟度スコア'] = 0.0
    
    fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
    
    if save_dataset(filename, data, fieldnames):
        set_flash_message(f'全{len(data)}問の習熟度をリセットしました。', 'success')
        return redirect(url_for('edit_dataset', filename=filename))
    else:
        set_flash_message('習熟度の一括リセットに失敗しました。', 'error')
        return redirect(url_for('edit_dataset', filename=filename))

@app.route('/input_results/<filename>')
def input_results(filename):
    """印刷したテストの結果を手動で入力"""
    data = load_dataset(filename)
    dataset_name = filename[:-4]
    message, message_type = get_message_and_type(request)
    
    if not data:
        set_flash_message('データセットが空です。', 'error')
        return redirect(url_for('index'))
    
    return render_template('input_results.html',
                         dataset_name=dataset_name,
                         filename=filename,
                         data=data,
                         message=message,
                         message_type=message_type)


@app.route('/save_results/<filename>', methods=['POST'])
def save_results(filename):
    """手動入力した結果を保存して習熟度を更新"""
    data = load_dataset(filename)
    
    if not data:
        set_flash_message('データセットが空です。', 'error')
        return redirect(url_for('input_results', filename=filename))
    
    # 各問題の結果を処理
    updated_count = 0
    for i in range(len(data)):
        result = request.form.get(f'result_{i}')
        if result in ['correct', 'incorrect']:
            is_correct = (result == 'correct')
            if update_question_proficiency(filename, i, is_correct):
                updated_count += 1
    
    if updated_count > 0:
        set_flash_message(f'{updated_count}問の結果を保存し、習熟度を更新しました。', 'success')
        return redirect(url_for('input_results', filename=filename))
    else:
        set_flash_message('結果が更新されませんでした。問題を選択してください。', 'error')
        return redirect(url_for('input_results', filename=filename))

# オンラインテスト機能
@app.route('/online_test/<filename>')
def online_test_setup(filename):
    """オンラインテスト設定画面"""
    data = load_dataset(filename)
    
    if not data:
        set_flash_message('データセットが見つかりません。', 'error')
        return redirect(url_for('index'))
    
    # 既存の統計データがあれば取得
    total_items = len(data)
    
    # 習熟度分布を取得
    mastery_dist = get_mastery_distribution(data)
    
    return render_template('online_test_setup.html',
                         filename=filename,
                         dataset_name=filename[:-4],
                         total_items=total_items,
                         mastery_distribution=mastery_dist)

@app.route('/quick_10/<filename>')
def quick_10_test(filename):
    """クイック10テスト: 習熟度が低い問題から10問をランダム選択して即開始"""
    data = load_dataset(filename)
    
    if not data:
        set_flash_message('データセットが見つかりません。', 'error')
        return redirect(url_for('index'))
    
    # 習熟度が低い問題（60%未満）を抽出
    weak_problems = get_weak_problems(data, threshold=0.6)
    
    # 習熟度の低い問題が10問未満の場合、閾値を上げて問題を追加
    if len(weak_problems) < 10:
        # 80%未満まで拡張
        weak_problems = get_weak_problems(data, threshold=0.8)
        
        # まだ足りない場合は全問題から選択
        if len(weak_problems) < 10:
            weak_problems = data
    
    # 最大10問を選択
    num_questions = min(10, len(weak_problems))
    if num_questions == 0:
        set_flash_message('出題可能な問題がありません。', 'error')
        return redirect(url_for('index'))
    
    # ランダムに問題を選択
    selected_problems = random.sample(weak_problems, num_questions)
    
    # テスト設定
    settings = {
        'quiz_type': 'question_to_answer'
    }
    
    # オンラインテストセッションを作成
    session_id = create_online_test_session(filename, selected_problems, settings, is_quick_10=True)
    
    return redirect(url_for('online_test_session', session_id=session_id))

@app.route('/start_online_test/<filename>', methods=['POST'])
def start_online_test(filename):
    """オンラインテスト開始"""
    data = load_dataset(filename)
    
    if not data:
        set_flash_message('データセットが空です。', 'error')
        return redirect(url_for('online_test_setup', filename=filename))
    
    try:
        num_questions = int(request.form.get('num_questions', 10))
        quiz_type = request.form.get('quiz_type', 'question_to_answer')
        selection_method = request.form.get('selection_method', 'random')
        problem_mode = request.form.get('problem_mode', 'normal')
        
        # 弱点問題特化モードの処理
        if problem_mode == 'weak':
            # 弱点問題のみを対象とする
            weak_data = get_weak_problems(data, threshold=0.6)
            if not weak_data:
                set_flash_message('弱点問題が見つかりません。通常モードをお試しください。', 'warning')
                return redirect(url_for('online_test_setup', filename=filename))
            range_data = weak_data
            # 弱点問題モードでは範囲指定は無効
            num_questions = min(max(1, num_questions), len(range_data))
        else:
            # 通常モード：範囲設定の取得
            range_start = request.form.get('range_start')
            range_end = request.form.get('range_end')
            
            # 範囲の設定（空欄の場合はデフォルト値）
            start_index = int(range_start) - 1 if range_start else 0  # 1-based to 0-based
            end_index = int(range_end) - 1 if range_end else len(data) - 1  # 1-based to 0-based
            
            # 範囲の妥当性チェック
            if start_index < 0 or start_index >= len(data):
                set_flash_message('開始位置が無効です。', 'error')
                return redirect(url_for('online_test_setup', filename=filename))
            
            if end_index < 0 or end_index >= len(data):
                set_flash_message('終了位置が無効です。', 'error')
                return redirect(url_for('online_test_setup', filename=filename))
            
            if start_index > end_index:
                set_flash_message('開始位置は終了位置以下にしてください。', 'error')
                return redirect(url_for('online_test_setup', filename=filename))
            
            # 指定範囲のデータを取得
            range_data = data[start_index:end_index + 1]
            
            # 問題数の調整（範囲データのサイズまで）
            num_questions = min(max(1, num_questions), len(range_data))
        
        # 問題の選択
        if selection_method == 'sequential':
            # 順番選択：範囲の最初から指定数を選択
            selected_items = range_data[:num_questions]
        else:
            # ランダム選択：範囲からランダムに選択
            selected_items = random.sample(range_data, num_questions)
        
        # テスト設定
        settings = {
            'quiz_type': quiz_type
        }
        
        # オンラインテストセッションを作成
        session_id = create_online_test_session(filename, selected_items, settings, is_quick_10=False)
        
        return redirect(url_for('online_test_session', session_id=session_id))
        
    except ValueError as e:
        set_flash_message('入力値が正しくありません。', 'error')
        return redirect(url_for('online_test_setup', filename=filename))
    except Exception as e:
        set_flash_message('予期しないエラーが発生しました。', 'error')
        return redirect(url_for('online_test_setup', filename=filename))

@app.route('/online_test_session/<session_id>')
def online_test_session(session_id):
    """オンラインテスト実行画面"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        set_flash_message('テストセッションが見つかりません。', 'error')
        return redirect(url_for('index'))
    
    return render_template('online_test.html',
                         session_id=session_id,
                         test_session=test_session)

@app.route('/show_answer/<session_id>', methods=['POST'])
def show_answer(session_id):
    """回答を表示"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        return jsonify({'error': 'セッションが見つかりません'}), 404
    
    current_index = test_session['current_question']
    
    # 状態を"answer"に変更
    test_session['question_states'][current_index] = 'answer'
    
    return jsonify({'success': True})

@app.route('/submit_judgment/<session_id>', methods=['POST'])
def submit_judgment(session_id):
    """自己判定を提出"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        return jsonify({'error': 'セッションが見つかりません'}), 404
    
    current_index = test_session['current_question']
    is_correct = request.json.get('is_correct', False)
    
    # 判定結果を記録
    test_session['user_judgments'][current_index] = is_correct
    test_session['question_states'][current_index] = 'judged'
    
    # スコアを更新
    if is_correct:
        test_session['results']['score'] += 1
    
    # 習熟度データを更新（オンラインテストの結果をCSVに反映）
    try:
        # 現在の問題のオリジナルインデックスを取得
        current_question = test_session['questions'][current_index]
        filename = test_session['filename']
        
        # 元のデータセットを読み込んで該当問題のインデックスを見つける
        all_data = load_dataset(filename)
        original_index = None
        
        for i, item in enumerate(all_data):
            if (item.get('質問') == current_question.get('質問') and 
                item.get('回答') == current_question.get('回答')):
                original_index = i
                break
        
        # 習熟度データを更新
        if original_index is not None:
            update_question_proficiency(filename, original_index, is_correct)
            
    except Exception as e:
        print(f"習熟度更新エラー: {e}")
        # エラーが発生してもテストは継続
    
    return jsonify({'success': True})

@app.route('/next_question/<session_id>', methods=['POST'])
def next_question(session_id):
    """次の問題へ移動"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        return jsonify({'error': 'セッションが見つかりません'}), 404
    
    current_index = test_session['current_question']
    total_questions = len(test_session['questions'])
    
    if current_index + 1 < total_questions:
        test_session['current_question'] = current_index + 1
        return jsonify({'success': True, 'next_question_index': current_index + 1})
    else:
        # テスト終了
        return jsonify({'success': True, 'test_completed': True})

@app.route('/finish_test/<session_id>', methods=['POST'])
def finish_test(session_id):
    """テストを終了"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        return jsonify({'error': 'セッションが見つかりません'}), 404
    
    # テスト終了フラグを設定
    test_session['finished'] = True
    
    return jsonify({'success': True, 'test_completed': True})

@app.route('/skip_question/<session_id>', methods=['POST'])
def skip_question(session_id):
    """問題をスキップ"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        return jsonify({'error': 'セッションが見つかりません'}), 404
    
    current_index = test_session['current_question']
    
    # スキップは不正解として記録
    test_session['user_judgments'][current_index] = False
    test_session['question_states'][current_index] = 'judged'
    
    # 習熟度データを更新（スキップは不正解として記録）
    try:
        current_question = test_session['questions'][current_index]
        filename = test_session['filename']
        
        # 元のデータセットを読み込んで該当問題のインデックスを見つける
        all_data = load_dataset(filename)
        original_index = None
        
        for i, item in enumerate(all_data):
            if (item.get('質問') == current_question.get('質問') and 
                item.get('回答') == current_question.get('回答')):
                original_index = i
                break
        
        # 習熟度データを更新（不正解として記録）
        if original_index is not None:
            update_question_proficiency(filename, original_index, False)
            
    except Exception as e:
        print(f"習熟度更新エラー: {e}")
        # エラーが発生してもテストは継続
    
    # 次の問題へ移動
    total_questions = len(test_session['questions'])
    
    if current_index + 1 < total_questions:
        test_session['current_question'] = current_index + 1
        return jsonify({'success': True, 'next_question_index': current_index + 1})
    else:
        # テスト終了
        return jsonify({'success': True, 'test_completed': True})

@app.route('/test_results/<session_id>')
def test_results(session_id):
    """テスト結果表示"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        set_flash_message('テストセッションが見つかりません。', 'error')
        return redirect(url_for('index'))
    
    # 結果を計算
    score = test_session['results']['score']
    total = test_session['results']['total_questions']
    percentage = round((score / total) * 100, 1) if total > 0 else 0
    
    return render_template('test_results.html',
                         session_id=session_id,
                         test_session=test_session,
                         score=score,
                         total=total,
                         percentage=percentage)

@app.route('/test_progress/<session_id>')
def test_progress(session_id):
    """テスト進捗取得（Ajax用）"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        return jsonify({'error': 'セッションが見つかりません'}), 404
    
    # 実際に回答済みの問題数を計算
    answered_questions = sum(1 for judgment in test_session['user_judgments'] if judgment is not None)
    
    return jsonify({
        'current_question': test_session['current_question'],
        'total_questions': test_session['results']['total_questions'],
        'score': test_session['results']['score'],
        'total': test_session['results']['total_questions'],
        'answered_questions': answered_questions
    })

@app.route('/get_historical_accuracy/<session_id>')
def get_historical_accuracy(session_id):
    """現在の問題の過去の正解率を取得"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        return jsonify({'error': 'セッションが見つかりません'}), 404
    
    try:
        current_index = test_session['current_question']
        current_question = test_session['questions'][current_index]
        filename = test_session['filename']
        
        # 元のデータセットを読み込んで該当問題のインデックスを見つける
        all_data = load_dataset(filename)
        original_index = None
        
        for i, item in enumerate(all_data):
            if (item.get('質問') == current_question.get('質問') and 
                item.get('回答') == current_question.get('回答')):
                original_index = i
                break
        
        if original_index is not None:
            item = all_data[original_index]
            correct_count = int(item.get('正解数', 0))
            total_attempts = int(item.get('総試行回数', 0))
            
            return jsonify({
                'success': True,
                'correct_count': correct_count,
                'total_attempts': total_attempts,
                'accuracy': correct_count / total_attempts if total_attempts > 0 else 0
            })
        else:
            return jsonify({
                'success': True,
                'correct_count': 0,
                'total_attempts': 0,
                'accuracy': 0
            })
            
    except Exception as e:
        print(f"過去正解率取得エラー: {e}")
        return jsonify({'error': '過去の正解率取得に失敗しました'}), 500

@app.route('/get_current_question/<session_id>')
def get_current_question(session_id):
    """現在の問題データを取得"""
    test_session = get_online_test_session(session_id)
    
    if not test_session:
        return jsonify({'error': 'セッションが見つかりません'}), 404
    
    try:
        current_index = test_session['current_question']
        current_question = test_session['questions'][current_index]
        quiz_type = test_session['settings']['quiz_type']
        
        # 問題文と回答文を決定
        if quiz_type == 'question_to_answer':
            question_text = current_question.get('質問', '')
            answer_text = current_question.get('回答', '')
        else:
            question_text = current_question.get('回答', '')
            answer_text = current_question.get('質問', '')
        
        return jsonify({
            'success': True,
            'current_question': current_index,
            'total_questions': test_session['results']['total_questions'],
            'question_text': question_text,
            'answer_text': answer_text
        })
        
    except Exception as e:
        print(f"現在問題取得エラー: {e}")
        return jsonify({'error': '現在の問題取得に失敗しました'}), 500


@app.route('/generate_quiz/<filename>')
def generate_quiz(filename):
    """テスト作成ページ"""
    data = load_dataset(filename)
    dataset_name = filename[:-4]
    message, message_type = get_message_and_type(request)
    
    return render_template('generate_quiz.html',
                         dataset_name=dataset_name,
                         filename=filename,
                         total_items=len(data),
                         message=message,
                         message_type=message_type)

@app.route('/create_quiz/<filename>', methods=['POST'])
def create_quiz(filename):
    """テスト作成・PDF生成"""
    data = load_dataset(filename)
    
    if not data:
        set_flash_message('データセットが空です。', 'error')
        return redirect(url_for('generate_quiz', filename=filename))
    
    try:
        num_questions = int(request.form.get('num_questions', 40))
        quiz_type = request.form.get('quiz_type', 'question_to_answer')
        selection_method = request.form.get('selection_method', 'random')
        include_answers = request.form.get('include_answers', 'no')
        
        # 範囲設定の取得
        range_start = request.form.get('range_start')
        range_end = request.form.get('range_end')
        
        # 範囲の設定（空欄の場合はデフォルト値）
        start_index = int(range_start) - 1 if range_start else 0  # 1-based to 0-based
        end_index = int(range_end) - 1 if range_end else len(data) - 1  # 1-based to 0-based
        
        # 範囲の妥当性チェック
        if start_index < 0 or start_index >= len(data):
            set_flash_message('開始位置が無効です。', 'error')
            return redirect(url_for('generate_quiz', filename=filename))
        
        if end_index < 0 or end_index >= len(data):
            set_flash_message('終了位置が無効です。', 'error')
            return redirect(url_for('generate_quiz', filename=filename))
        
        if start_index > end_index:
            set_flash_message('開始位置は終了位置以下にしてください。', 'error')
            return redirect(url_for('generate_quiz', filename=filename))
        
        # 指定範囲のデータを取得
        range_data = data[start_index:end_index + 1]
        
        # 問題数の調整（範囲データのサイズまで）
        num_questions = min(max(1, num_questions), len(range_data))
        
        if num_questions < 1:
            set_flash_message('問題数は1以上にしてください。', 'error')
            return redirect(url_for('generate_quiz', filename=filename))
        
        # 問題の選択
        if selection_method == 'sequential':
            # 順番選択：範囲の最初から指定数を選択
            selected_items = range_data[:num_questions]
        else:
            # ランダム選択：範囲からランダムに選択
            selected_items = random.sample(range_data, num_questions)
            
    except ValueError as e:
        set_flash_message('入力値が正しくありません。', 'error')
        return redirect(url_for('generate_quiz', filename=filename))
    except Exception as e:
        set_flash_message('予期しないエラーが発生しました。', 'error')
        return redirect(url_for('generate_quiz', filename=filename))
    
    # PDF生成
    pdf_buffer = create_test_pdf(selected_items, filename[:-4], quiz_type, include_answers)
    
    # PDFをファイルとして返す
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f'{filename[:-4]}_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
        mimetype='application/pdf'
    )

def create_test_pdf(items, dataset_name, quiz_type, include_answers='no'):
    """問題のPDFを作成（統一フォーマット：質問,回答）"""
    buffer = io.BytesIO()
    
    # フォント設定
    font_available = setup_fonts()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=10*mm, bottomMargin=10*mm, 
                          leftMargin=10*mm, rightMargin=10*mm)
    story = []
    
    # スタイル設定
    styles = getSampleStyleSheet()
    
    # 日本語文字をHTMLエンティティに変換する関数
    def escape_japanese(text):
        """日本語文字をHTMLエンティティに変換"""
        result = ""
        for char in text:
            if ord(char) > 127:  # ASCII以外の文字
                result += f"&#{ord(char)};"
            else:
                result += char
        return result
    
    # 日本語対応のスタイル設定
    if font_available:
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName='Japanese',
            fontSize=16,
            spaceAfter=5
        )
        
        question_style = ParagraphStyle(
            'QuestionStyle',
            parent=styles['Normal'],
            fontName='Japanese',
            fontSize=10,
            spaceAfter=2
        )
    else:
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=5
        )
        
        question_style = ParagraphStyle(
            'QuestionStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=2
        )
    
    # タイトル
    total_questions = len(items)
    if font_available:
        title_text = f"{dataset_name} - 問題 ({total_questions}問)"
    else:
        title_text = escape_japanese(f"{dataset_name} - 問題 ({total_questions}問)")
    
    title_paragraph = Paragraph(title_text, title_style)
    story.append(title_paragraph)
    story.append(Spacer(1, 3*mm))
    
    # 全ての問題を処理（40問を超えた場合は複数ページ）
    total_items = len(items)
    items_per_page = 40  # 1ページあたり最大40問（20行×2列）
    
    # ページごとに処理
    current_item_index = 0
    
    while current_item_index < total_items:
        # 現在のページの問題数を計算
        remaining_items = total_items - current_item_index
        current_page_items = min(remaining_items, items_per_page)
        page_items = items[current_item_index:current_item_index + current_page_items]
        
        # 新しいページの場合はページブレークを追加（最初のページ以外）
        if current_item_index > 0:
            from reportlab.platypus import PageBreak
            story.append(PageBreak())
            
            # 2ページ目以降のタイトル
            page_num = (current_item_index // items_per_page) + 1
            if font_available:
                page_title = f"{dataset_name} - 問題 (ページ {page_num})"
            else:
                page_title = escape_japanese(f"{dataset_name} - 問題 (ページ {page_num})")
            
            story.append(Paragraph(page_title, title_style))
            story.append(Spacer(1, 3*mm))
        
        # 表データを準備（2列構成：左側25問、右側25問）
        table_data = []
        
        # ヘッダー行
        table_data.append(['問題', '解答欄', '問題', '解答欄'])
        
        # 25行のデータを作成
        for i in range(20):
            left_item = page_items[i] if i < len(page_items) else None
            right_item = page_items[i + 20] if i + 20 < len(page_items) else None
            
            # 左側の問題
            if left_item:
                # 統一フォーマット：質問,回答 + 旧フォーマット互換性
                if quiz_type == 'answer_to_question':
                    # 回答→質問
                    question_text = (left_item.get('回答') or 
                                   left_item.get('answer') or '')
                    answer_text = (left_item.get('質問') or 
                                 left_item.get('question') or '')
                else:
                    # 質問→回答（デフォルト）
                    question_text = (left_item.get('質問') or 
                                   left_item.get('question') or '')
                    answer_text = (left_item.get('回答') or 
                                 left_item.get('answer') or '')
                
                if question_text:
                    if font_available:
                        left_question = f"{left_item.get('番号', current_item_index + i + 1)}. {question_text}"
                    else:
                        left_question = escape_japanese(f"{left_item.get('番号', current_item_index + i + 1)}. {question_text}")
                    
                    # 回答欄の処理
                    if include_answers == 'red':
                        # 薄い赤字で回答を表示（赤シートで隠しやすいように）
                        if font_available:
                            left_answer = f"<font color='#FF6666'>{answer_text}</font>"
                        else:
                            left_answer = f"<font color='#FF6666'>{escape_japanese(answer_text)}</font>"
                        left_answer = Paragraph(left_answer, question_style)
                    else:
                        left_answer = "________________"
                else:
                    left_question = ""
                    left_answer = ""
            else:
                left_question = ""
                left_answer = ""
            
            # 右側の問題
            if right_item:
                # 統一フォーマット：質問,回答 + 旧フォーマット互換性
                if quiz_type == 'answer_to_question':
                    # 回答→質問
                    question_text = (right_item.get('回答') or 
                                   right_item.get('answer') or '')
                    answer_text = (right_item.get('質問') or 
                                 right_item.get('question') or '')
                else:
                    # 質問→回答（デフォルト）
                    question_text = (right_item.get('質問') or 
                                   right_item.get('question') or '')
                    answer_text = (right_item.get('回答') or 
                                 right_item.get('answer') or '')
                
                if question_text:
                    if font_available:
                        right_question = f"{right_item.get('番号', current_item_index + i + 26)}. {question_text}"
                    else:
                        right_question = escape_japanese(f"{right_item.get('番号', current_item_index + i + 26)}. {question_text}")
                    
                    # 回答欄の処理
                    if include_answers == 'red':
                        # 薄い赤字で回答を表示（赤シートで隠しやすいように）
                        if font_available:
                            right_answer = f"<font color='#FF6666'>{answer_text}</font>"
                        else:
                            right_answer = f"<font color='#FF6666'>{escape_japanese(answer_text)}</font>"
                        right_answer = Paragraph(right_answer, question_style)
                    else:
                        right_answer = "________________"
                else:
                    right_question = ""
                    right_answer = ""
            else:
                right_question = ""
                right_answer = ""
            
            # 行を追加
            if left_question or right_question:
                table_data.append([
                    Paragraph(left_question, question_style) if left_question else "",
                    left_answer,
                    Paragraph(right_question, question_style) if right_question else "",
                    right_answer
                ])
        
        # 表を作成（4列：問題、解答欄、問題、解答欄）
        table = Table(table_data, colWidths=[55*mm, 35*mm, 55*mm, 35*mm], rowHeights=[8*mm] * len(table_data))
        
        # 表のスタイル設定
        table.setStyle(TableStyle([
            # ヘッダー行のスタイル
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Japanese' if font_available else 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            
            # データ行のスタイル
            ('FONTNAME', (0, 1), (-1, -1), 'Japanese' if font_available else 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(table)
        
        # 回答を下部に含める場合は、回答セクションを追加
        if include_answers == 'bottom':
            # 回答セクション用のスペース
            story.append(Spacer(1, 5*mm))
            
            # 回答セクションのタイトル
            if font_available:
                answer_title_text = "回答"
            else:
                answer_title_text = escape_japanese("回答")
            
            answer_title_style = ParagraphStyle(
                'AnswerTitle',
                parent=styles['Heading2'],
                fontName='Japanese' if font_available else 'Helvetica-Bold',
                fontSize=12,
                spaceAfter=3
            )
            
            story.append(Paragraph(answer_title_text, answer_title_style))
            
            # 回答データを作成（現在のページの問題に対応）
            answer_data = []
            answers_per_row = 5  # 1行に5個の回答を配置
            
            for i, item in enumerate(page_items):
                # 回答テキストを取得
                if quiz_type == 'answer_to_question':
                    # 回答→質問の場合、質問が答え
                    answer_text = (item.get('質問') or item.get('question') or '')
                else:
                    # 質問→回答の場合、回答が答え
                    answer_text = (item.get('回答') or item.get('answer') or '')
                
                question_number = item.get('番号', current_item_index + i + 1)
                
                if font_available:
                    answer_entry = f"{question_number}. {answer_text}"
                else:
                    answer_entry = escape_japanese(f"{question_number}. {answer_text}")
                
                answer_data.append(answer_entry)
            
            # 回答を表形式で配置（1行に複数個）
            answer_table_data = []
            answer_style = ParagraphStyle(
                'AnswerStyle',
                parent=styles['Normal'],
                fontName='Japanese' if font_available else 'Helvetica',
                fontSize=8,
                spaceAfter=2
            )
            
            for i in range(0, len(answer_data), answers_per_row):
                row_data = []
                for j in range(answers_per_row):
                    if i + j < len(answer_data):
                        # 薄い赤字で回答を表示
                        if font_available:
                            red_answer = f"<font color='#FF6666'>{answer_data[i + j]}</font>"
                        else:
                            red_answer = f"<font color='#FF6666'>{answer_data[i + j]}</font>"
                        row_data.append(Paragraph(red_answer, answer_style))
                    else:
                        row_data.append("")
                answer_table_data.append(row_data)
            
            if answer_table_data:
                answer_table = Table(answer_table_data, colWidths=[38*mm] * answers_per_row)
                answer_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Japanese' if font_available else 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(answer_table)
        
        # 次のページの準備
        current_item_index += current_page_items
    
    try:
        doc.build(story)
    except Exception as e:
        print(f"PDF generation error: {e}")
        # フォールバック: 簡単な形式でPDFを作成
        story = []
        story.append(Paragraph(f"{dataset_name} - Quiz ({len(items)} questions)", title_style))
        for i, item in enumerate(items, 1):
            question_text = (item.get('質問') or 
                           item.get('question') or '問題')
            story.append(Paragraph(f"{i}. {question_text} Answer: ___________", question_style))
            story.append(Spacer(1, 1*mm))
        
        # フォールバック時も回答を含める
        if include_answers == 'bottom':
            story.append(Spacer(1, 5*mm))
            story.append(Paragraph("回答", title_style))
            for i, item in enumerate(items, 1):
                if quiz_type == 'answer_to_question':
                    answer_text = (item.get('質問') or item.get('question') or '')
                else:
                    answer_text = (item.get('回答') or item.get('answer') or '')
                # 薄い赤字で回答を表示
                red_answer = f"<font color='#FF6666'>{i}. {answer_text}</font>"
                story.append(Paragraph(red_answer, question_style))
        elif include_answers == 'red':
            # 赤字で回答を表示する場合は既に問題文に含まれているのでここでは何もしない
            pass
        
        doc.build(story)
    
    buffer.seek(0)
    return buffer

@app.route('/delete_dataset/<filename>')
def delete_dataset(filename):
    """データセット削除"""
    filepath = os.path.join(DATASETS_DIR, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            set_flash_message('データセットを削除しました。', 'success')
            return redirect(url_for('index'))
        else:
            set_flash_message('データセットが見つかりません。', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        set_flash_message('データセットの削除に失敗しました。', 'error')
        return redirect(url_for('index'))

@app.route('/export_dataset/<filename>')
def export_dataset(filename):
    """データセットをCSVでエクスポート（拡張フォーマット：番号,質問,回答,正解数,総試行回数,習熟度スコア）"""
    filepath = os.path.join(DATASETS_DIR, filename)
    if os.path.exists(filepath):
        try:
            # 現在のファイルを読み込み
            data = load_dataset(filename)
            
            # 拡張フォーマット: 番号,質問,回答,正解数,総試行回数,習熟度スコア
            fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
            
            if data:
                # メモリ内でCSVを作成
                import io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                # 各アイテムに習熟度データを含めて出力
                for item in data:
                    export_item = {
                        '番号': item.get('番号', ''),
                        '質問': item.get('質問', ''),
                        '回答': item.get('回答', ''),
                        '正解数': item.get('正解数', 0),
                        '総試行回数': item.get('総試行回数', 0),
                        '習熟度スコア': item.get('習熟度スコア', 0.0)
                    }
                    writer.writerow(export_item)
                
                csv_content = output.getvalue()
                output.close()
                
                # Excel対応のエンコーディング処理
                try:
                    # まずShift_JISを試行（日本語Excelで最も互換性が高い）
                    csv_bytes = csv_content.encode('shift_jis')
                    mimetype = 'text/csv; charset=shift_jis'
                except UnicodeEncodeError as encode_error:
                    print(f"Export: Shift_JIS encoding failed: {encode_error}")
                    print("Export: Using UTF-8 with BOM for Excel compatibility")
                    # UTF-8 with BOM（ExcelがUTF-8を正しく認識するため）
                    bom = '\ufeff'
                    csv_content_with_bom = bom + csv_content
                    csv_bytes = csv_content_with_bom.encode('utf-8')
                    mimetype = 'text/csv; charset=utf-8'
                
                buffer = io.BytesIO(csv_bytes)
                
                # メモリから直接送信（一時ファイル不要）
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype=mimetype
                )
            else:
                # 空のファイルの場合
                import io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                csv_content = output.getvalue()
                output.close()
                
                # Excel対応のエンコーディング処理
                try:
                    csv_bytes = csv_content.encode('shift_jis')
                    mimetype = 'text/csv; charset=shift_jis'
                except UnicodeEncodeError:
                    # UTF-8 with BOM（ExcelがUTF-8を正しく認識するため）
                    bom = '\ufeff'
                    csv_content_with_bom = bom + csv_content
                    csv_bytes = csv_content_with_bom.encode('utf-8')
                    mimetype = 'text/csv; charset=utf-8'
                
                buffer = io.BytesIO(csv_bytes)
                
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype=mimetype
                )
        except Exception as e:
            print(f"Export error: {e}")
            set_flash_message('エクスポートに失敗しました。', 'error')
            return redirect(url_for('index'))
    else:
        set_flash_message('データセットが見つかりません。', 'error')
        return redirect(url_for('index'))

@app.route('/import_dataset')
def import_dataset_page():
    """データセットインポートページ"""
    message, message_type = get_message_and_type(request)
    return render_template('import_dataset.html', message=message, message_type=message_type)

@app.route('/upload_dataset', methods=['POST'])
def upload_dataset():
    """データセットファイルのアップロード処理（統一フォーマット：質問,回答）"""
    if 'file' not in request.files:
        return redirect(url_for('import_dataset_page', error='ファイルが選択されていません。'))
    
    file = request.files['file']
    if file.filename == '':
        set_flash_message('ファイルが選択されていません。', 'error')
        return redirect(url_for('import_dataset_page'))
    
    if not file.filename.endswith('.csv'):
        set_flash_message('CSVファイルを選択してください。', 'error')
        return redirect(url_for('import_dataset_page'))
    
    try:
        # ファイル内容を読み込んで検証（エンコーディング自動判定）
        content = None
        encodings = ['shift_jis', 'utf-8', 'cp932']
        
        for encoding in encodings:
            try:
                content = file.read().decode(encoding)
                print(f"File decoded successfully with {encoding}")
                break
            except UnicodeDecodeError:
                file.seek(0)  # ファイルポインタを先頭に戻す
                continue
        
        if content is None:
            set_flash_message('ファイルの文字エンコーディングが認識できません。', 'error')
            return redirect(url_for('import_dataset_page'))
        
        file.seek(0)  # ファイルポインタを先頭に戻す
        
        # CSV形式の検証（CSVのパースを実際に試行して検証）
        try:
            # StringIOを使ってCSVを実際にパースしてみる
            from io import StringIO
            csv_data = StringIO(content)
            
            # 最初の行を読んで区切り文字を判定
            first_line = csv_data.readline()
            csv_data.seek(0)  # ファイルポインタを先頭に戻す
            
            # タブかカンマで区切られているかを判定
            delimiter = '\t' if '\t' in first_line and first_line.count('\t') > first_line.count(',') else ','
            delimiter_name = 'TAB' if delimiter == '\t' else 'COMMA'
            
            reader = csv.DictReader(csv_data, delimiter=delimiter)
            
            # ヘッダーを取得
            header_fields = reader.fieldnames
            if not header_fields:
                set_flash_message('ヘッダー行が見つかりません。', 'error')
                return redirect(url_for('import_dataset_page'))
            
            # フィールド名を正規化（前後の空白を除去）
            header_fields = [field.strip() for field in header_fields]
            
            # フォーマットの検証
            has_number = '番号' in header_fields
            has_question = '質問' in header_fields or 'question' in header_fields
            has_answer = '回答' in header_fields or 'answer' in header_fields
            has_proficiency = all(field in header_fields for field in ['正解数', '総試行回数', '習熟度スコア'])
            
            if not (has_question and has_answer):
                set_flash_message('無効なCSV形式です。"質問"と"回答"（または"question"と"answer"）の列が必要です。', 'error')
                return redirect(url_for('import_dataset_page'))
            
            # データ行の存在チェック
            data_rows = list(reader)
            if len(data_rows) == 0:
                set_flash_message('データ行が見つかりません。ヘッダー行のみのファイルです。', 'error')
                return redirect(url_for('import_dataset_page'))
            
            print(f"CSV validation successful: {len(data_rows)} data rows found")
            print(f"Header fields: {header_fields}")
            
        except Exception as csv_error:
            print(f"CSV parsing error: {csv_error}")
            set_flash_message(f'CSVファイルの解析に失敗しました: {str(csv_error)}', 'error')
            return redirect(url_for('import_dataset_page'))
        
        # ファイル名の重複チェック
        base_name = file.filename[:-4]  # .csvを除去
        filename = file.filename
        force_overwrite = request.form.get('force_overwrite')
        
        if os.path.exists(os.path.join(DATASETS_DIR, filename)) and not force_overwrite:
            set_flash_message(f'データセット "{base_name}" は既に存在します。上書きする場合はチェックボックスを選択してください。', 'error')
            return redirect(url_for('import_dataset_page'))
        
        # ファイルを保存（エンコーディング処理を改善）
        ensure_datasets_dir()
        filepath = os.path.join(DATASETS_DIR, filename)
        
        # Shift_JISでエンコードできない文字を処理
        try:
            # まずShift_JISで保存を試行
            with open(filepath, 'w', encoding='shift_jis', newline='') as f:
                f.write(content)
            print(f"File saved successfully with shift_jis encoding")
        except UnicodeEncodeError as encode_error:
            print(f"Shift_JIS encoding failed: {encode_error}")
            print("Trying to save with UTF-8 encoding and convert problematic characters...")
            
            # Shift_JISでエンコードできない文字を置換
            content_fixed = content.replace('～', '~')  # 全角チルダを半角チルダに
            content_fixed = content_fixed.replace('　', ' ')  # 全角スペースを半角スペースに
            content_fixed = content_fixed.replace('－', '-')  # 全角ハイフンを半角ハイフンに
            content_fixed = content_fixed.replace('＋', '+')  # 全角プラスを半角プラスに
            
            try:
                # 修正後の内容でShift_JIS保存を再試行
                with open(filepath, 'w', encoding='shift_jis', newline='') as f:
                    f.write(content_fixed)
                print(f"File saved successfully with shift_jis encoding after character conversion")
            except UnicodeEncodeError:
                # それでも失敗する場合はUTF-8で保存
                print("Still failed with shift_jis, saving with UTF-8 encoding")
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    f.write(content)
                print(f"File saved with UTF-8 encoding")
        
        # データ数をカウント
        data = load_dataset(filename)
        
        set_flash_message(f'データセット "{filename[:-4]}" をインポートしました。({len(data)}件)', 'success')
        return redirect(url_for('edit_dataset', filename=filename))
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Import error details: {error_details}")
        set_flash_message(f'ファイルのインポートに失敗しました: {str(e)}', 'error')
        return redirect(url_for('import_dataset_page'))

@app.before_request
def cleanup_on_request():
    """リクエスト前のクリーンアップ（期限切れメッセージの削除）"""
    import random
    if random.random() < 0.1:  # 10%の確率でクリーンアップ実行
        cleanup_expired_messages()

if __name__ == '__main__':
    ensure_datasets_dir()
    app.run(debug=True, host='0.0.0.0', port=5000)
