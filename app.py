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
    """CSVファイルからデータセットを読み込み"""
    filepath = os.path.join(DATASETS_DIR, filename)
    data = []
    if os.path.exists(filepath):
        try:
            # まずShift_JISで試行
            with open(filepath, 'r', encoding='shift_jis') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
        except UnicodeDecodeError:
            # Shift_JISで読めない場合はUTF-8で試行
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data.append(row)
            except Exception as e:
                print(f"Error loading dataset {filename}: {e}")
        except Exception as e:
            print(f"Error loading dataset {filename}: {e}")
    return data

def save_dataset(filename, data, fieldnames=None):
    """データセットをCSVファイルに保存"""
    ensure_datasets_dir()
    filepath = os.path.join(DATASETS_DIR, filename)
    
    # 統一フォーマット: 質問,回答
    if fieldnames is None:
        fieldnames = ['質問', '回答']
    
    try:
        with open(filepath, 'w', encoding='shift_jis', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
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
    
    # 統一フォーマット: 質問,回答
    fieldnames = ['質問', '回答']
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
    
    # 統一フォーマット: 質問,回答
    fieldnames = ['質問', '回答']
    
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
    
    # 統一フォーマット: 質問,回答
    fieldnames = ['質問', '回答']
    new_item = {
        '質問': request.form.get('question', ''),
        '回答': request.form.get('answer', '')
    }
    
    # 空のフィールドチェック
    if not all(new_item.values()):
        return redirect(url_for('edit_dataset', filename=filename, error='すべてのフィールドを入力してください。'))
    
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
        # 統一フォーマット: 質問,回答
        fieldnames = ['質問', '回答']
        
        data.pop(index)
        
        if save_dataset(filename, data, fieldnames):
            return redirect(url_for('edit_dataset', filename=filename, msg='アイテムを削除しました。'))
        else:
            return redirect(url_for('edit_dataset', filename=filename, error='アイテムの削除に失敗しました。'))
    else:
        return redirect(url_for('edit_dataset', filename=filename, error='無効なアイテムです。'))

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
    
    num_questions = int(request.form.get('num_questions', 50))
    quiz_type = request.form.get('quiz_type', 'question_to_answer')
    output_type = request.form.get('output_type', 'practice')  # 新しいパラメータ
    
    # 問題数の調整（データセットのサイズまで）
    num_questions = min(num_questions, len(data))
    
    # ランダムに問題を選択
    selected_items = random.sample(data, num_questions)
    
    # PDF生成
    pdf_buffer = create_quiz_pdf(selected_items, filename[:-4], quiz_type, output_type)
    
    # ファイル名を出力タイプに応じて変更
    output_suffix = "_answers" if output_type == "answer_sheet" else "_quiz"
    
    # PDFをファイルとして返す
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f'{filename[:-4]}{output_suffix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
        mimetype='application/pdf'
    )

def create_quiz_pdf(items, dataset_name, quiz_type, output_type='practice'):
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
    title_suffix = "解答付きシート" if output_type == 'answer_sheet' else "暗記問題"
    if font_available:
        title_text = f"{dataset_name} - {title_suffix} ({total_questions}問)"
    else:
        title_text = escape_japanese(f"{dataset_name} - {title_suffix} ({total_questions}問)")
    
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
                page_title = f"{dataset_name} - {title_suffix} (ページ {page_num})"
            else:
                page_title = escape_japanese(f"{dataset_name} - {title_suffix} (ページ {page_num})")
            
            story.append(Paragraph(page_title, title_style))
            story.append(Spacer(1, 10*mm))
        
        # 表データを準備（2列構成：左側25問、右側25問）
        table_data = []
        
        # ヘッダー行
        header_answer_col = '正解' if output_type == 'answer_sheet' else '解答欄'
        table_data.append(['問題', header_answer_col, '問題', header_answer_col])
        
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
                        left_question = f"{current_item_index + i + 1}. {question_text}"
                    else:
                        left_question = escape_japanese(f"{current_item_index + i + 1}. {question_text}")
                    
                    # 答えの表示を出力タイプに応じて変更
                    if output_type == 'answer_sheet':
                        # 正解を表示
                        if quiz_type == 'answer_to_question':
                            # 回答→質問の場合、質問が正解
                            correct_answer = (left_item.get('質問') or 
                                            left_item.get('question') or '')
                        else:
                            # 質問→回答の場合、回答が正解
                            correct_answer = (left_item.get('回答') or 
                                            left_item.get('answer') or '')
                        
                        if font_available:
                            left_answer = correct_answer
                        else:
                            left_answer = escape_japanese(correct_answer)
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
                else:
                    # 質問→回答（デフォルト）
                    question_text = (right_item.get('質問') or 
                                   right_item.get('question') or '')
                
                if question_text:
                    if font_available:
                        right_question = f"{current_item_index + i + 26}. {question_text}"
                    else:
                        right_question = escape_japanese(f"{current_item_index + i + 26}. {question_text}")
                    
                    # 答えの表示を出力タイプに応じて変更
                    if output_type == 'answer_sheet':
                        # 正解を表示
                        if quiz_type == 'answer_to_question':
                            # 回答→質問の場合、質問が正解
                            correct_answer = (right_item.get('質問') or 
                                            right_item.get('question') or '')
                        else:
                            # 質問→回答の場合、回答が正解
                            correct_answer = (right_item.get('回答') or 
                                            right_item.get('answer') or '')
                        
                        if font_available:
                            right_answer = correct_answer
                        else:
                            right_answer = escape_japanese(correct_answer)
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
    """データセットをCSVでエクスポート（統一フォーマット：質問,回答）"""
    filepath = os.path.join(DATASETS_DIR, filename)
    if os.path.exists(filepath):
        try:
            # 現在のファイルを読み込み
            data = load_dataset(filename)
            
            # 統一フォーマット: 質問,回答
            fieldnames = ['質問', '回答']
            
            if data:
                # メモリ内でCSVを作成
                import io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                csv_content = output.getvalue()
                output.close()
                
                # Shift_JISでエンコード
                csv_bytes = csv_content.encode('shift_jis')
                buffer = io.BytesIO(csv_bytes)
                
                # メモリから直接送信（一時ファイル不要）
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='text/csv'
                )
            else:
                # 空のファイルの場合
                import io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                csv_content = output.getvalue()
                output.close()
                
                csv_bytes = csv_content.encode('shift_jis')
                buffer = io.BytesIO(csv_bytes)
                
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='text/csv'
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
        
        # CSV形式の検証
        lines = content.strip().split('\n')
        if len(lines) < 1:
            return redirect(url_for('import_dataset_page', error='空のファイルです。'))
        
        header = lines[0].lower().strip()  # 小文字に変換して前後の空白を削除
        
        # 統一フォーマットのチェック
        if ('質問' in header and '回答' in header) or ('question' in header and 'answer' in header):
            # 統一フォーマット（日本語版または英語版）
            pass
        else:
            return redirect(url_for('import_dataset_page', error='無効なCSV形式です。ヘッダーは "質問,回答" または "question,answer" である必要があります。'))
        
        # ファイル名の重複チェック
        base_name = file.filename[:-4]  # .csvを除去
        filename = file.filename
        force_overwrite = request.form.get('force_overwrite')
        
        if os.path.exists(os.path.join(DATASETS_DIR, filename)) and not force_overwrite:
            return redirect(url_for('import_dataset_page', error=f'データセット "{base_name}" は既に存在します。上書きする場合はチェックボックスを選択してください。'))
        
        # ファイルを保存（Shift_JISで統一）
        ensure_datasets_dir()
        filepath = os.path.join(DATASETS_DIR, filename)
        
        # コンテンツをShift_JISで保存
        with open(filepath, 'w', encoding='shift_jis', newline='') as f:
            f.write(content)
        
        # データ数をカウント
        data = load_dataset(filename)
        
        return redirect(url_for('edit_dataset', filename=filename, msg=f'データセット "{filename[:-4]}" をインポートしました。({len(data)}件)'))
        
    except Exception as e:
        return redirect(url_for('import_dataset_page', error='ファイルのインポートに失敗しました。'))

if __name__ == '__main__':
    ensure_datasets_dir()
    app.run(debug=True, host='0.0.0.0', port=5000)
