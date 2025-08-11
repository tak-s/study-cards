#!/bin/bash

# StudyCards デーモン起動スクリプト
# 使用方法: ./daemon.sh {start|stop|restart|status} [--port ポート番号]

# 設定変数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
VENV_PATH="$APP_DIR/venv"
APP_FILE="app.py"
PID_FILE="$APP_DIR/studycards.pid"
LOG_FILE="$APP_DIR/studycards.log"
ERROR_LOG_FILE="$APP_DIR/studycards_error.log"
PYTHON_PATH="$VENV_PATH/bin/python"
USER=$(whoami)

# デフォルトポート
DEFAULT_PORT=5000
PORT=$DEFAULT_PORT

# 色付きメッセージ用の関数
print_success() {
    echo -e "\033[32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

print_info() {
    echo -e "\033[34m[INFO]\033[0m $1"
}

print_warning() {
    echo -e "\033[33m[WARNING]\033[0m $1"
}

# 引数解析
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port|-p)
                if [[ -n $2 && $2 =~ ^[0-9]+$ ]]; then
                    PORT="$2"
                    shift 2
                else
                    print_error "ポート番号が指定されていないか、無効です: $2"
                    exit 1
                fi
                ;;
            start|stop|restart|status|logs|help)
                COMMAND="$1"
                shift
                ;;
            *)
                print_error "不明なオプション: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 前提条件チェック
check_prerequisites() {
    # アプリディレクトリの存在確認
    if [ ! -d "$APP_DIR" ]; then
        print_error "アプリケーションディレクトリが見つかりません: $APP_DIR"
        exit 1
    fi
    
    # 仮想環境の存在確認
    if [ ! -d "$VENV_PATH" ]; then
        print_error "仮想環境が見つかりません: $VENV_PATH"
        print_info "セットアップスクリプトを実行してください: ./setup.sh"
        exit 1
    fi
    
    # Pythonインタープリターの存在確認
    if [ ! -f "$PYTHON_PATH" ]; then
        print_error "Pythonインタープリターが見つかりません: $PYTHON_PATH"
        exit 1
    fi
    
    # app.pyの存在確認
    if [ ! -f "$APP_DIR/$APP_FILE" ]; then
        print_error "アプリケーションファイルが見つかりません: $APP_DIR/$APP_FILE"
        exit 1
    fi
}

# プロセス開始
start_app() {
    print_info "StudyCards アプリケーションを開始しています（ポート: $PORT）..."
    
    # 既に実行中かチェック
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "アプリケーションは既に実行中です (PID: $PID)"
            return 1
        else
            print_info "古いPIDファイルを削除しています..."
            rm -f "$PID_FILE"
        fi
    fi
    
    # ポート使用状況チェック
    if netstat -tuln 2>/dev/null | grep -q ":$PORT " || ss -tuln 2>/dev/null | grep -q ":$PORT "; then
        print_error "ポート $PORT は既に使用中です"
        print_info "他のポートを使用するか、使用中のプロセスを停止してください"
        print_info "使用例: $0 start --port 5001"
        return 1
    fi
    
    # ログファイルのディレクトリ権限確認
    touch "$LOG_FILE" "$ERROR_LOG_FILE" 2>/dev/null
    if [ $? -ne 0 ]; then
        print_error "ログファイルの作成権限がありません"
        exit 1
    fi
    
    # アプリケーションディレクトリに移動
    cd "$APP_DIR" || exit 1
    
    # バックグラウンドでアプリケーションを起動（ポート指定）
    nohup "$PYTHON_PATH" "$APP_FILE" --port "$PORT" > "$LOG_FILE" 2> "$ERROR_LOG_FILE" &
    PID=$!
    
    # PIDファイルに保存
    echo $PID > "$PID_FILE"
    
    # 起動確認（3秒待って確認）
    sleep 3
    if ps -p $PID > /dev/null 2>&1; then
        print_success "アプリケーションが開始されました (PID: $PID)"
        print_info "ポート: $PORT"
        print_info "ログファイル: $LOG_FILE"
        print_info "エラーログ: $ERROR_LOG_FILE"
        print_info "アクセスURL: http://localhost:$PORT"
        return 0
    else
        print_error "アプリケーションの起動に失敗しました"
        print_info "エラー詳細: $(tail -5 "$ERROR_LOG_FILE")"
        rm -f "$PID_FILE"
        return 1
    fi
}

# プロセス停止
stop_app() {
    print_info "StudyCards アプリケーションを停止しています..."
    
    if [ ! -f "$PID_FILE" ]; then
        print_warning "PIDファイルが見つかりません。アプリケーションは実行されていない可能性があります"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    # プロセスが実行中か確認
    if ! ps -p $PID > /dev/null 2>&1; then
        print_warning "指定されたPIDのプロセスは実行されていません (PID: $PID)"
        rm -f "$PID_FILE"
        return 1
    fi
    
    # プロセスを停止
    kill $PID
    
    # 停止確認（最大10秒待機）
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            print_success "アプリケーションが停止されました (PID: $PID)"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # 強制停止
    print_warning "通常停止に失敗しました。強制停止を実行します..."
    kill -9 $PID
    sleep 2
    
    if ! ps -p $PID > /dev/null 2>&1; then
        print_success "アプリケーションが強制停止されました"
        rm -f "$PID_FILE"
        return 0
    else
        print_error "アプリケーションの停止に失敗しました"
        return 1
    fi
}

# プロセス状態確認
status_app() {
    if [ ! -f "$PID_FILE" ]; then
        print_info "StudyCards アプリケーションは停止中です"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p $PID > /dev/null 2>&1; then
        print_success "StudyCards アプリケーションは実行中です (PID: $PID)"
        print_info "メモリ使用量: $(ps -p $PID -o rss= | awk '{printf "%.1f MB", $1/1024}')"
        print_info "CPU使用率: $(ps -p $PID -o %cpu= | awk '{print $1"%"}')"
        print_info "起動時間: $(ps -p $PID -o etime= | awk '{print $1}')"
        
        # 実際に使用されているポートを検出
        DETECTED_PORT=""
        if command -v netstat >/dev/null 2>&1; then
            DETECTED_PORT=$(netstat -tulpn 2>/dev/null | grep "$PID/python" | grep LISTEN | head -1 | awk '{print $4}' | cut -d':' -f2)
        elif command -v ss >/dev/null 2>&1; then
            DETECTED_PORT=$(ss -tulpn 2>/dev/null | grep "pid=$PID" | grep LISTEN | head -1 | awk '{print $5}' | cut -d':' -f2)
        fi
        
        if [ -n "$DETECTED_PORT" ]; then
            print_info "使用ポート: $DETECTED_PORT"
            print_info "アクセスURL: http://localhost:$DETECTED_PORT"
        else
            print_warning "ポート情報を取得できませんでした"
        fi
        return 0
    else
        print_warning "PIDファイルは存在しますが、プロセスは実行されていません"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 再起動
restart_app() {
    print_info "StudyCards アプリケーションを再起動しています..."
    stop_app
    sleep 2
    start_app
}

# ログ表示
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_info "=== アプリケーションログ (最新20行) ==="
        tail -20 "$LOG_FILE"
    else
        print_warning "ログファイルが見つかりません: $LOG_FILE"
    fi
    
    if [ -f "$ERROR_LOG_FILE" ]; then
        print_info "=== エラーログ (最新10行) ==="
        tail -10 "$ERROR_LOG_FILE"
    else
        print_warning "エラーログファイルが見つかりません: $ERROR_LOG_FILE"
    fi
}

# ヘルプ表示
show_help() {
    echo "StudyCards デーモン制御スクリプト"
    echo ""
    echo "使用方法: $0 {start|stop|restart|status|logs|help} [OPTIONS]"
    echo ""
    echo "コマンド:"
    echo "  start    - アプリケーションを開始"
    echo "  stop     - アプリケーションを停止"
    echo "  restart  - アプリケーションを再起動"
    echo "  status   - アプリケーションの状態確認"
    echo "  logs     - ログファイルの内容表示"
    echo "  help     - このヘルプを表示"
    echo ""
    echo "オプション:"
    echo "  --port, -p PORT    - ポート番号を指定 (デフォルト: 5000)"
    echo ""
    echo "ファイル:"
    echo "  PIDファイル: $PID_FILE"
    echo "  ログファイル: $LOG_FILE"
    echo "  エラーログ: $ERROR_LOG_FILE"
    echo ""
    echo "例:"
    echo "  $0 start             # デフォルトポート(5000)で開始"
    echo "  $0 start --port 8080 # ポート8080で開始"
    echo "  $0 start -p 3000     # ポート3000で開始"
    echo "  $0 status            # 実行状態確認"
    echo "  $0 logs              # ログ表示"
    echo "  $0 restart --port 9000 # ポート9000で再起動"
}

# メイン処理
main() {
    # 最初の引数がない場合はヘルプを表示
    if [ $# -eq 0 ]; then
        show_help
        exit 1
    fi
    
    # 引数解析
    parse_arguments "$@"
    
    # コマンドが設定されていない場合はエラー
    if [ -z "$COMMAND" ]; then
        print_error "コマンドが指定されていません"
        show_help
        exit 1
    fi
    
    case "$COMMAND" in
        start)
            check_prerequisites
            start_app
            ;;
        stop)
            stop_app
            ;;
        restart)
            check_prerequisites
            restart_app
            ;;
        status)
            status_app
            ;;
        logs)
            show_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "無効なコマンドです: $COMMAND"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"
