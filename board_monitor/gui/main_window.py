"""
板監視システム メインウィンドウ v6

レイアウト:
  上段: BoardUnit × 5 (unit_1 ～ unit_5)
  下段: BoardUnit × 5 (unit_6 ～ unit_10)

各 BoardUnit は独立して 5 銘柄の Aリストを持つ。
10ユニット × 5銘柄 = 50銘柄を同時管理可能。
"""
import json
import logging
import tkinter as tk
import threading
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, Optional

from .board_unit import BoardUnit, STOCK_NAMES
from ..kabu_api.websocket_client import KabuWebSocketClient

logger = logging.getLogger(__name__)

UNITS_PER_ROW = 5  # 上段・下段それぞれのユニット数
SETTINGS_FILE = Path(__file__).parent.parent / "settings.json"


class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        data_queue: Queue,
        kabu_client: Optional[KabuWebSocketClient] = None,
    ):
        """
        Args:
            root        : Tkinter root window
            data_queue  : 受信データキュー（{"type":"update","stock_code":..., "board_data":...}）
            kabu_client : kabuStation クライアント（None でモック動作）
        """
        self.root = root
        self.root.title("板監視システム")
        self.root.geometry("1920x1080")
        self.root.configure(bg="black")

        self.data_queue  = data_queue
        self.kabu_client = kabu_client

        # unit_key → BoardUnit
        self.units: Dict[str, BoardUnit] = {}

        self._loading = False   # 設定読み込み中フラグ（保存ループ防止）
        self._create_layout()
        self._load_settings()   # 起動時に前回の銘柄・ウィンドウ位置を復元

        # データ受信スレッド
        self.polling = True
        self.data_thread = threading.Thread(target=self._poll_queue, daemon=True)
        self.data_thread.start()

    # ─────────────────────────────────────────────────────────
    #  レイアウト構築
    # ─────────────────────────────────────────────────────────

    def _create_layout(self):
        """上段5 + 下段5 のグリッドを構築"""
        self.main_frame = tk.Frame(self.root, bg="black")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 上段
        self.upper_frame = tk.Frame(self.main_frame, bg="black")
        self.upper_frame.pack(fill=tk.BOTH, expand=True)

        for n in range(1, UNITS_PER_ROW + 1):
            self._add_unit(self.upper_frame, f"unit_{n}")

        # セパレータ
        tk.Frame(self.main_frame, bg="gray30", height=2).pack(fill=tk.X)

        # 下段
        self.lower_frame = tk.Frame(self.main_frame, bg="black")
        self.lower_frame.pack(fill=tk.BOTH, expand=True)

        for n in range(UNITS_PER_ROW + 1, UNITS_PER_ROW * 2 + 1):
            self._add_unit(self.lower_frame, f"unit_{n}")

    def _add_unit(self, parent: tk.Frame, unit_key: str):
        """BoardUnit を親フレームに追加"""
        unit = BoardUnit(
            parent=parent,
            unit_key=unit_key,
            on_subscribe=self._on_subscribe,
            on_unsubscribe=self._on_unsubscribe,
            on_slot_change=self._on_slot_change,
        )
        unit.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.units[unit_key] = unit

    # ─────────────────────────────────────────────────────────
    #  データフロー
    # ─────────────────────────────────────────────────────────

    def _poll_queue(self):
        """バックグラウンドスレッドでキューを監視"""
        while self.polling:
            try:
                data = self.data_queue.get(timeout=1)
                # Tkinter は必ずメインスレッドから操作する
                self.root.after(0, self._process_data, data)
            except Empty:
                pass
            except Exception:
                pass

    def _process_data(self, data: dict):
        """受信データを該当ユニットへ配信"""
        if data.get("type") != "update":
            return

        code       = data.get("stock_code")
        board_data = data.get("board_data")
        if not code or not board_data:
            return

        for unit in self.units.values():
            # そのユニットのAリストに含まれている銘柄なら配信
            if code in unit.a_codes:
                unit.push_board_data(code, board_data)

    # ─────────────────────────────────────────────────────────
    #  kabuStation 購読管理
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────
    #  設定保存 / 読み込み
    # ─────────────────────────────────────────────────────────

    def _on_slot_change(self, unit_key: str, slot_idx: int, code: str):
        """銘柄スロット変更 → 設定を保存（読み込み中は無視）"""
        if not self._loading:
            self._save_settings()

    def _save_settings(self):
        """全ユニットの銘柄リスト＋ウィンドウ位置を JSON に保存"""
        # ウィンドウ状態（最大化 or 通常）と位置を保存
        try:
            win_state = self.root.state()          # 'zoomed' or 'normal'
            win_geom  = self.root.geometry()       # '1920x1080+0+0' など
        except Exception:
            win_state = "normal"
            win_geom  = "1920x1080"

        data = {
            "window_state": win_state,
            "window_geometry": win_geom,
            "units": {
                key: unit.a_codes[:]
                for key, unit in self.units.items()
            },
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"設定保存失敗: {e}")

    def _load_settings(self):
        """JSON から銘柄リスト・ウィンドウ位置を読み込み復元"""
        if not SETTINGS_FILE.exists():
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # ── ウィンドウ位置・サイズ復元
            geom  = data.get("window_geometry")
            state = data.get("window_state", "normal")
            if geom:
                self.root.geometry(geom)
            if state == "zoomed":
                self.root.state("zoomed")

            # ── 銘柄スロット復元（UIのみ・購読はバックグラウンドで後から）
            self._loading = True
            all_codes: list = []
            for unit_key, codes in data.get("units", {}).items():
                if unit_key not in self.units:
                    continue
                for slot_idx, code in enumerate(codes):
                    if code and slot_idx < 5:
                        name = STOCK_NAMES.get(code, "")
                        self.units[unit_key].set_a_slot(slot_idx, code, name)
                        if code not in all_codes:
                            all_codes.append(code)
            self._loading = False

            # 購読登録はバックグラウンドで（メインスレッドをブロックしない）
            if all_codes and self.kabu_client:
                codes_to_reg = all_codes
                def _register():
                    self.kabu_client.add_symbols(codes_to_reg)
                threading.Thread(target=_register, daemon=True).start()

            logger.info(f"設定読み込み完了: {SETTINGS_FILE}")
        except Exception as e:
            logger.warning(f"設定読み込み失敗: {e}")
        finally:
            self._loading = False

    def _on_subscribe(self, unit_key: str, stock_code: str):
        """銘柄の WebSocket 購読を開始"""
        if self.kabu_client:
            self.kabu_client.add_symbols([stock_code])

    def _on_unsubscribe(self, unit_key: str, stock_code: str):
        """銘柄の WebSocket 購読を停止（他ユニットで使用中でなければ）"""
        if not self.kabu_client:
            return
        # 全ユニットのAリストに同じコードがなければ解除
        all_codes = [c for u in self.units.values() for c in u.a_codes]
        if stock_code not in all_codes:
            self.kabu_client.remove_symbol(stock_code)

    # ─────────────────────────────────────────────────────────
    #  外部 API（test_ui.py から使用）
    # ─────────────────────────────────────────────────────────

    def set_a_slot(self, unit_key: str, slot_idx: int, code: str, name: str = ""):
        """指定ユニットのAリスト slot_idx に銘柄を設定

        Args:
            unit_key : "unit_1" ～ "unit_10"
            slot_idx : 0 ～ 4
            code     : 銘柄コード
            name     : 銘柄名（省略可）
        """
        if unit_key in self.units:
            self.units[unit_key].set_a_slot(slot_idx, code, name)

    def shutdown(self):
        """終了処理（ウィンドウ位置を保存してから終了）"""
        self._save_settings()   # 閉じる直前に位置・銘柄を保存
        self.polling = False
