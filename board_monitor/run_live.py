"""
板監視システム 実運用起動スクリプト

kabuStation API のライブデータを使用してリアルタイム監視します。
"""
import logging
import sys
import tkinter as tk
from pathlib import Path
from queue import Queue
from dotenv import load_dotenv

# プロジェクトルートを Python path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# .env ファイルから環境変数を読み込み
load_dotenv(Path(__file__).parent.parent / ".env")

from board_monitor.gui.main_window import MainWindow
from board_monitor.kabu_api.websocket_client import KabuWebSocketClient

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / "board_monitor.log")
    ]
)
logger = logging.getLogger(__name__)


def main():
    """板監視システム起動（ライブ）"""
    root = tk.Tk()
    root.configure(bg="black")
    data_queue = Queue()

    # kabuStation API クライアント初期化
    logger.info("=" * 60)
    logger.info("板監視システム - ライブモード起動")
    logger.info("=" * 60)

    kabu_client = KabuWebSocketClient(data_queue)
    kabu_client.start()
    logger.info("kabuStation API クライアント起動完了")

    # メインウィンドウ初期化
    win = MainWindow(root, data_queue, kabu_client=kabu_client)
    logger.info("メインウィンドウ初期化完了")

    print("=" * 60)
    print("板監視システム - ライブモード")
    print("=" * 60)
    print("kabuStation API に接続中...")
    print("タブをダブルクリックして銘柄コードを入力してください")
    print("=" * 60)

    def on_closing():
        """終了処理"""
        logger.info("終了開始...")
        win.shutdown()
        kabu_client.stop()
        root.destroy()
        logger.info("終了完了")

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
