from flask import Flask, render_template, request, redirect, url_for, send_file
import csv
import os
import random
from datetime import datetime
import io
import base64
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors

app = Flask(__name__)
# secret_key は不要です（flash()を使用せず、URLパラメータでメッセージを渡すため）

# データセット保存ディレクトリ
DATASETS_DIR = 'datasets'

def get_message_and_type(request):
    """URLパラメータからメッセージとタイプを取得"""
    msg = request.args.get('msg')
    error = request.args.get('error')
    
    if error:
        return error, 'error'
    elif msg:
        return msg, 'success'
    else:
        return '', ''

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
    """利用可能なデータセット一覧を取得"""
    ensure_datasets_dir()
    datasets = []
    for filename in os.listdir(DATASETS_DIR):
        if filename.endswith('.csv'):
            name = filename[:-4]  # .csvを除去
            datasets.append({
                'name': name,
                'filename': filename,
                'path': os.path.join(DATASETS_DIR, filename)
            })
    return datasets

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
    """メインページ"""
    datasets = get_datasets()
    message, message_type = get_message_and_type(request)
    return render_template('index.html', datasets=datasets, message=message, message_type=message_type)

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
        return redirect(url_for('create_dataset', error='データセット名を入力してください。'))
    
    filename = f"{name}.csv"
    
    # 重複チェック
    if os.path.exists(os.path.join(DATASETS_DIR, filename)):
        return redirect(url_for('create_dataset', error=f'データセット "{name}" は既に存在します。別の名前を使用してください。'))
    
    # 拡張フォーマット: 番号,質問,回答,正解数,総試行回数,習熟度スコア
    fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
    data = []
    
    if save_dataset(filename, data, fieldnames):
        return redirect(url_for('edit_dataset', filename=filename, msg='データセットを作成しました。'))
    else:
        return redirect(url_for('create_dataset', error='データセットの作成に失敗しました。'))

@app.route('/edit_dataset/<filename>')
def edit_dataset(filename):
    """データセット編集ページ"""
    data = load_dataset(filename)
    dataset_name = filename[:-4]  # .csvを除去
    
    # 拡張フォーマット: 番号,質問,回答,正解数,総試行回数,習熟度スコア
    fieldnames = ['番号', '質問', '回答', '正解数', '総試行回数', '習熟度スコア']
    
    message, message_type = get_message_and_type(request)
    
    return render_template('edit_dataset.html', 
                         dataset_name=dataset_name,
                         filename=filename,
                         data=data,
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
        return redirect(url_for('edit_dataset', filename=filename, error='質問と回答を入力してください。'))
    
    data.append(new_item)
    
    if save_dataset(filename, data, fieldnames):
        return redirect(url_for('edit_dataset', filename=filename, msg='アイテムを追加しました。'))
    else:
        return redirect(url_for('edit_dataset', filename=filename, error='アイテムの追加に失敗しました。'))

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
            return redirect(url_for('edit_dataset', filename=filename, msg='アイテムを削除しました。'))
        else:
            return redirect(url_for('edit_dataset', filename=filename, error='アイテムの削除に失敗しました。'))
    else:
        return redirect(url_for('edit_dataset', filename=filename, error='無効なアイテムです。'))

@app.route('/input_results/<filename>')
def input_results(filename):
    """印刷したテストの結果を手動で入力"""
    data = load_dataset(filename)
    dataset_name = filename[:-4]
    message, message_type = get_message_and_type(request)
    
    if not data:
        return redirect(url_for('index', error='データセットが空です。'))
    
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
        return redirect(url_for('input_results', filename=filename, error='データセットが空です。'))
    
    # 各問題の結果を処理
    updated_count = 0
    for i in range(len(data)):
        result = request.form.get(f'result_{i}')
        if result in ['correct', 'incorrect']:
            is_correct = (result == 'correct')
            if update_question_proficiency(filename, i, is_correct):
                updated_count += 1
    
    if updated_count > 0:
        return redirect(url_for('input_results', filename=filename, 
                              msg=f'{updated_count}問の結果を保存し、習熟度を更新しました。'))
    else:
        return redirect(url_for('input_results', filename=filename, 
                              error='結果が更新されませんでした。問題を選択してください。'))





@app.route('/generate_quiz/<filename>')
def generate_quiz(filename):
    """問題生成ページ"""
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
    """問題作成・PDF生成"""
    data = load_dataset(filename)
    
    if not data:
        return redirect(url_for('generate_quiz', filename=filename, error='データセットが空です。'))
    
    try:
        num_questions = int(request.form.get('num_questions', 50))
        quiz_type = request.form.get('quiz_type', 'question_to_answer')
        selection_method = request.form.get('selection_method', 'random')
        
        # 範囲設定の取得
        range_start = request.form.get('range_start')
        range_end = request.form.get('range_end')
        
        # 範囲の設定（空欄の場合はデフォルト値）
        start_index = int(range_start) - 1 if range_start else 0  # 1-based to 0-based
        end_index = int(range_end) - 1 if range_end else len(data) - 1  # 1-based to 0-based
        
        # 範囲の妥当性チェック
        if start_index < 0 or start_index >= len(data):
            return redirect(url_for('generate_quiz', filename=filename, error='開始位置が無効です。'))
        
        if end_index < 0 or end_index >= len(data):
            return redirect(url_for('generate_quiz', filename=filename, error='終了位置が無効です。'))
        
        if start_index > end_index:
            return redirect(url_for('generate_quiz', filename=filename, error='開始位置は終了位置以下にしてください。'))
        
        # 指定範囲のデータを取得
        range_data = data[start_index:end_index + 1]
        
        # 問題数の調整（範囲データのサイズまで）
        num_questions = min(max(1, num_questions), len(range_data))
        
        if num_questions < 1:
            return redirect(url_for('generate_quiz', filename=filename, error='問題数は1以上にしてください。'))
        
        # 問題の選択
        if selection_method == 'sequential':
            # 順番選択：範囲の最初から指定数を選択
            selected_items = range_data[:num_questions]
        else:
            # ランダム選択：範囲からランダムに選択
            selected_items = random.sample(range_data, num_questions)
            
    except ValueError as e:
        return redirect(url_for('generate_quiz', filename=filename, error='入力値が正しくありません。'))
    except Exception as e:
        return redirect(url_for('generate_quiz', filename=filename, error='予期しないエラーが発生しました。'))
    
    # PDF生成
    pdf_buffer = create_quiz_pdf(selected_items, filename[:-4], quiz_type)
    
    # PDFをファイルとして返す
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f'{filename[:-4]}_quiz_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
        mimetype='application/pdf'
    )

def create_quiz_pdf(items, dataset_name, quiz_type):
    """問題のPDFを作成（統一フォーマット：質問,回答）"""
    buffer = io.BytesIO()
    
    # フォント設定
    font_available = setup_fonts()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
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
            spaceAfter=20
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
            spaceAfter=20
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
    story.append(Spacer(1, 10*mm))
    
    # 全ての問題を処理（50問を超えた場合は複数ページ）
    total_items = len(items)
    items_per_page = 50  # 1ページあたり最大50問（25行×2列）
    
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
            story.append(Spacer(1, 10*mm))
        
        # 表データを準備（2列構成：左側25問、右側25問）
        table_data = []
        
        # ヘッダー行
        table_data.append(['問題', '解答欄', '問題', '解答欄'])
        
        # 25行のデータを作成
        for i in range(25):
            left_item = page_items[i] if i < len(page_items) else None
            right_item = page_items[i + 25] if i + 25 < len(page_items) else None
            
            # 左側の問題
            if left_item:
                # 統一フォーマット：質問,回答 + 旧フォーマット互換性
                if quiz_type == 'answer_to_question':
                    # 回答→質問
                    question_text = (left_item.get('回答') or 
                                   left_item.get('answer') or '')
                else:
                    # 質問→回答（デフォルト）
                    question_text = (left_item.get('質問') or 
                                   left_item.get('question') or '')
                
                if question_text:
                    if font_available:
                        left_question = f"{left_item.get('番号', current_item_index + i + 1)}. {question_text}"
                    else:
                        left_question = escape_japanese(f"{left_item.get('番号', current_item_index + i + 1)}. {question_text}")
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
                else:
                    # 質問→回答（デフォルト）
                    question_text = (right_item.get('質問') or 
                                   right_item.get('question') or '')
                
                if question_text:
                    if font_available:
                        right_question = f"{right_item.get('番号', current_item_index + i + 26)}. {question_text}"
                    else:
                        right_question = escape_japanese(f"{right_item.get('番号', current_item_index + i + 26)}. {question_text}")
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
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # データ行のスタイル
            ('FONTNAME', (0, 1), (-1, -1), 'Japanese' if font_available else 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(table)
        
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
            story.append(Spacer(1, 3*mm))
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
            return redirect(url_for('index', msg='データセットを削除しました。'))
        else:
            return redirect(url_for('index', error='データセットが見つかりません。'))
    except Exception as e:
        return redirect(url_for('index', error='データセットの削除に失敗しました。'))

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
            return redirect(url_for('index', error='エクスポートに失敗しました。'))
    else:
        return redirect(url_for('index', error='データセットが見つかりません。'))

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
        return redirect(url_for('import_dataset_page', error='ファイルが選択されていません。'))
    
    if not file.filename.endswith('.csv'):
        return redirect(url_for('import_dataset_page', error='CSVファイルを選択してください。'))
    
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
            return redirect(url_for('import_dataset_page', error='ファイルの文字エンコーディングが認識できません。'))
        
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
                return redirect(url_for('import_dataset_page', error='ヘッダー行が見つかりません。'))
            
            # フィールド名を正規化（前後の空白を除去）
            header_fields = [field.strip() for field in header_fields]
            
            # フォーマットの検証
            has_number = '番号' in header_fields
            has_question = '質問' in header_fields or 'question' in header_fields
            has_answer = '回答' in header_fields or 'answer' in header_fields
            has_proficiency = all(field in header_fields for field in ['正解数', '総試行回数', '習熟度スコア'])
            
            if not (has_question and has_answer):
                return redirect(url_for('import_dataset_page', error='無効なCSV形式です。"質問"と"回答"（または"question"と"answer"）の列が必要です。'))
            
            # データ行の存在チェック
            data_rows = list(reader)
            if len(data_rows) == 0:
                return redirect(url_for('import_dataset_page', error='データ行が見つかりません。ヘッダー行のみのファイルです。'))
            
            print(f"CSV validation successful: {len(data_rows)} data rows found")
            print(f"Header fields: {header_fields}")
            
        except Exception as csv_error:
            print(f"CSV parsing error: {csv_error}")
            return redirect(url_for('import_dataset_page', error=f'CSVファイルの解析に失敗しました: {str(csv_error)}'))
        
        # ファイル名の重複チェック
        base_name = file.filename[:-4]  # .csvを除去
        filename = file.filename
        force_overwrite = request.form.get('force_overwrite')
        
        if os.path.exists(os.path.join(DATASETS_DIR, filename)) and not force_overwrite:
            return redirect(url_for('import_dataset_page', error=f'データセット "{base_name}" は既に存在します。上書きする場合はチェックボックスを選択してください。'))
        
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
        
        return redirect(url_for('edit_dataset', filename=filename, msg=f'データセット "{filename[:-4]}" をインポートしました。({len(data)}件)'))
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Import error details: {error_details}")
        return redirect(url_for('import_dataset_page', error=f'ファイルのインポートに失敗しました: {str(e)}'))

if __name__ == '__main__':
    ensure_datasets_dir()
    app.run(debug=True, host='0.0.0.0', port=5000)
