"""
kabuStation API クライアント

役割:
- POST /kabusapi/token で X-API-KEY を取得
- PUT  /kabusapi/register   で監視銘柄を登録
- PUT  /kabusapi/unregister/all で登録解除
- ws://localhost:18080/kabusapi/websocket から板スナップショットを受信
- 受信データを board_parser で内部形式に整形し data_queue へ流す

kabuStation 本体（三菱UFJ eスマート証券）がローカルで起動している前提。
本番未起動時は data_queue にデータが流れない（モックテストは test_ui.py 側）。
"""
import json
import logging
import os
import threading
from queue import Queue
from typing import Iterable, List, Optional

import requests
import websocket

from .board_parser import parse_kabu_board

logger = logging.getLogger(__name__)

KABU_API_BASE = "http://localhost:18080/kabusapi"
KABU_WS_URL = "ws://localhost:18080/kabusapi/websocket"
DEFAULT_EXCHANGE = 1  # 1=東証


class KabuWebSocketClient:
    """kabuStation API クライアント（REST 認証 + WebSocket 受信）"""

    def __init__(self, data_queue: Queue):
        self.data_queue = data_queue
        self.running = False
        self.ws: Optional[websocket.WebSocketApp] = None
        self.thread: Optional[threading.Thread] = None

        self.api_password = os.getenv("KABU_API_PASSWORD", "")
        self.token: Optional[str] = None

        # 登録中の銘柄（add_symbol/remove_symbol で同期）
        self._registered: set[str] = set()
        self._lock = threading.Lock()

    # ---------- ライフサイクル ----------

    def start(self):
        """REST 認証 → WebSocket 接続をバックグラウンドで開始"""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("KabuWebSocketClient: スレッド起動")

    def stop(self):
        """WebSocket を停止し、登録銘柄を解除"""
        self.running = False
        try:
            self.unregister_all()
        except Exception as e:
            logger.warning(f"unregister_all 失敗: {e}")
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("KabuWebSocketClient: 停止")

    def _run(self):
        """認証 → WebSocket 接続ループ（切断時は自動再接続）"""
        import time

        if not self._authenticate():
            logger.error("kabuStation API 認証失敗。kabuStation 本体が起動しているか確認してください。")
            return
        logger.info("kabuStation API 認証成功")

        while self.running:
            try:
                logger.info("WebSocket 接続試行...")
                self._connect_websocket()  # ws.run_forever() がここでブロック
            except Exception as e:
                logger.error(f"WebSocket 例外: {e}", exc_info=True)

            if not self.running:
                break

            logger.info("WebSocket 切断。5秒後に再接続します...")
            time.sleep(5)

            # トークン再取得
            if not self._authenticate():
                logger.error("再認証失敗。10秒後にリトライします...")
                time.sleep(10)

    # ---------- REST ----------

    def _authenticate(self) -> bool:
        try:
            res = requests.post(
                f"{KABU_API_BASE}/token",
                json={"APIPassword": self.api_password},
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if res.status_code != 200:
                logger.error(f"認証失敗 {res.status_code}: {res.text}")
                return False
            self.token = res.json().get("Token")
            return bool(self.token)
        except Exception as e:
            logger.error(f"認証リクエスト失敗: {e}")
            return False

    def _auth_headers(self) -> dict:
        return {"Content-Type": "application/json", "X-API-KEY": self.token or ""}

    def add_symbols(self, symbols: Iterable[str], exchange: int = DEFAULT_EXCHANGE) -> bool:
        """PUT /kabusapi/register に銘柄を追加登録"""
        if not self.token:
            logger.warning("add_symbols: 未認証のためスキップ")
            return False
        new_syms = [s for s in symbols if s and s not in self._registered]
        if not new_syms:
            return True
        body = {"Symbols": [{"Symbol": s, "Exchange": exchange} for s in new_syms]}
        try:
            res = requests.put(
                f"{KABU_API_BASE}/register",
                headers=self._auth_headers(),
                data=json.dumps(body),
                timeout=5,
            )
            if res.status_code != 200:
                logger.error(f"register 失敗 {res.status_code}: {res.text}")
                return False
            with self._lock:
                self._registered.update(new_syms)
            logger.info(f"register OK: {new_syms}")
            return True
        except Exception as e:
            logger.error(f"register 例外: {e}")
            return False

    def remove_symbol(self, symbol: str, exchange: int = DEFAULT_EXCHANGE) -> bool:
        """PUT /kabusapi/unregister で1銘柄を解除"""
        if not self.token or symbol not in self._registered:
            return False
        body = {"Symbols": [{"Symbol": symbol, "Exchange": exchange}]}
        try:
            res = requests.put(
                f"{KABU_API_BASE}/unregister",
                headers=self._auth_headers(),
                data=json.dumps(body),
                timeout=5,
            )
            if res.status_code != 200:
                logger.error(f"unregister 失敗 {res.status_code}: {res.text}")
                return False
            with self._lock:
                self._registered.discard(symbol)
            return True
        except Exception as e:
            logger.error(f"unregister 例外: {e}")
            return False

    def unregister_all(self) -> bool:
        """PUT /kabusapi/unregister/all で全銘柄登録解除"""
        if not self.token:
            return False
        try:
            res = requests.put(
                f"{KABU_API_BASE}/unregister/all",
                headers=self._auth_headers(),
                timeout=5,
            )
            with self._lock:
                self._registered.clear()
            return res.status_code == 200
        except Exception as e:
            logger.error(f"unregister/all 例外: {e}")
            return False

    # ---------- WebSocket ----------

    def _connect_websocket(self):
        def on_open(ws):
            logger.info("WebSocket 接続開始")

        def on_message(ws, message):
            self._on_message(message)

        def on_error(ws, error):
            logger.error(f"WebSocket エラー: {error}")

        def on_close(ws, code, msg):
            logger.info(f"WebSocket 接続閉鎖 code={code} msg={msg}")

        self.ws = websocket.WebSocketApp(
            KABU_WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        # ping_interval=0 でping無効化（kabuStation ローカルWS は ping 不要）
        self.ws.run_forever(ping_interval=0)

    def _on_message(self, message: str):
        """板スナップショット受信 → パース → キュー投入"""
        try:
            raw = json.loads(message)
        except json.JSONDecodeError:
            logger.error(f"JSON decode error: {message[:200]}")
            return

        board = parse_kabu_board(raw)
        if not board:
            logger.debug(f"Board parse skip: {raw.get('Symbol', 'N/A')}")
            return

        logger.debug(f"Board update: {board['symbol']} {board['last_price']}")
        self.data_queue.put({
            "type": "update",
            "stock_code": board["symbol"],
            "board_data": board,
        })

    # ---------- introspection ----------

    @property
    def registered_symbols(self) -> List[str]:
        with self._lock:
            return sorted(self._registered)
