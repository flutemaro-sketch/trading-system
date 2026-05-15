"""
板監視システム メインアプリケーション
- kabuStation WebSocket に接続
- リアルタイム板データを受信
- Tkinter GUI に表示
"""
import tkinter as tk
from queue import Queue
import logging
from pathlib import Path
import sys

# プロジェクトルートを Python path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from board_monitor.gui.main_window import MainWindow
from board_monitor.kabu_api.websocket_client import KabuWebSocketClient

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("board_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """メインアプリケーション"""
    logger.info("板監視システム 起動")

    # データキュー（kabuStation → GUI）
    data_queue = Queue()

    # Tkinter root ウィンドウ
    root = tk.Tk()
    root.configure(bg="black")

    try:
        # kabuStation WebSocket クライアント生成（起動はメインウィンドウ作成後）
        ws_client = KabuWebSocketClient(data_queue)

        # メインウィンドウ作成
        main_window = MainWindow(root, data_queue,
                                 kabu_client=ws_client)

        # WebSocket クライアント起動
        ws_client.start()

        logger.info("WebSocket クライアント 起動")

        # Tkinter メインループ
        root.mainloop()

    except KeyboardInterrupt:
        logger.info("ユーザー割り込み")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
    finally:
        logger.info("板監視システム 終了")
        if 'main_window' in locals():
            main_window.shutdown()
        if 'ws_client' in locals():
            ws_client.stop()
        root.quit()


if __name__ == "__main__":
    main()
