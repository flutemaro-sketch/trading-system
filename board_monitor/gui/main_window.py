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
from datetime import datetime, date
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, Optional

from .board_unit import BoardUnit, STOCK_NAMES
from ..kabu_api.websocket_client import KabuWebSocketClient
from ..monitors.candle_builder import CandleBuilder
from ..monitors.pennant_detector import PennantDetector
from ..monitors.alert_popup import AlertPopup

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

        # ── パターン検知エンジン
        self._candle_builder  = CandleBuilder(interval_minutes=5, max_candles=60)
        self._pennant_detector = PennantDetector()
        self._alert_popup      = AlertPopup(root)
        # 直前のアラート記録（同一銘柄の連続発火を防ぐ: 足3本分クールダウン）
        self._last_alert: Dict[str, int] = {}  # symbol → 最後にアラートを出した足index

        # 始値アラート状態（1日1回ずつ発報）
        # code → {"approach": bool, "break": bool, "date": date}
        self._open_alerts: Dict[str, dict] = {}

        # OVER/UNDER 逆転アラート状態
        # code → "OVER" or "UNDER" or "" (前回の優勢サイド)
        self._ou_state: Dict[str, str] = {}

        # unit_key → BoardUnit
        self.units: Dict[str, BoardUnit] = {}

        self._loading = False   # 設定読み込み中フラグ（保存ループ防止）
        self._create_layout()
        self._load_settings()   # 起動時に前回の銘柄・ウィンドウ位置を復元

        # データ受信ループ（メインスレッド: after で定期実行）
        self.polling = True
        self.root.after(50, self._poll_queue)

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
        """メインスレッドでキューを定期監視（遅延防止: 同一銘柄は最新データのみ処理）"""
        latest: dict = {}
        try:
            while True:
                data = self.data_queue.get_nowait()
                if data.get("type") == "update":
                    code = data.get("stock_code")
                    if code:
                        latest[code] = data  # 同一銘柄は最新で上書き
                else:
                    latest[f"__other_{id(data)}"] = data
        except Empty:
            pass
        except Exception:
            pass

        # 最新データのみ処理（古いデータはスキップ）
        for data in latest.values():
            try:
                self._process_data(data)
            except Exception:
                pass

        # 次のポーリング（50ms 間隔）
        if self.polling:
            self.root.after(50, self._poll_queue)

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

        # ── 始値ブレイク / 始値接近アラート
        self._check_open_price_alert(code, board_data)

        # ── OVER/UNDER 逆転アラート
        self._check_ou_alert(code, board_data)

        # ── ローソク足組み立て + ペナント検知（メインスレッド上で実行）
        self._update_candle_and_detect(code, board_data)

    def _check_open_price_alert(self, code: str, board_data: dict):
        """始値ブレイク / 始値接近 / 始値割れ後の回復アラートを発報する"""
        last_price = board_data.get("last_price", 0)
        open_price = board_data.get("open", 0)

        if not last_price or last_price <= 0:
            return
        if not open_price or open_price <= 0:
            return

        today = date.today()

        # アラート状態を初期化（日付が変わったらリセット）
        state = self._open_alerts.get(code, {})
        if state.get("date") != today:
            state = {"approach": False, "break": False, "below_open": False, "date": today}
            self._open_alerts[code] = state

        symbol_name = board_data.get("symbol_name", code)

        # ── 始値ブレイクアラート（初回：始値を初めて超えた）
        if not state["break"] and last_price > open_price:
            state["break"] = True
            state["approach"] = True  # 接近アラートもスキップ
            state["below_open"] = False
            self._alert_popup.show(
                symbol      = code,
                symbol_name = symbol_name,
                price       = last_price,
                pattern     = "open_break",
                detail      = f"始値 {open_price:.0f} ブレイク！ 現在値 {last_price:.0f}",
            )
            logger.info(f"[始値ブレイク] {code} {last_price:.0f} > 始値{open_price:.0f}")
            return

        # ── 始値を割り込んだ状態を記録
        if state["break"] and last_price < open_price:
            state["below_open"] = True

        # ── 始値割れ後の回復アラート（始値を割った後に再ブレイク）
        if state["break"] and state["below_open"] and last_price > open_price:
            state["below_open"] = False
            self._alert_popup.show(
                symbol      = code,
                symbol_name = symbol_name,
                price       = last_price,
                pattern     = "open_break",
                detail      = f"始値 {open_price:.0f} 割れ後に回復！ 現在値 {last_price:.0f}",
            )
            logger.info(f"[始値割れ後の回復] {code} {last_price:.0f} > 始値{open_price:.0f}")
            return

        # ── 始値接近アラート（始値の98%以上に来た）
        if not state["approach"] and last_price >= open_price * 0.98:
            state["approach"] = True
            self._alert_popup.show(
                symbol      = code,
                symbol_name = symbol_name,
                price       = last_price,
                pattern     = "open_approach",
                detail      = f"始値 {open_price:.0f} まであと {open_price - last_price:.0f}円",
            )
            logger.info(f"[始値接近] {code} {last_price:.0f} / 始値{open_price:.0f}")

    def _check_ou_alert(self, code: str, board_data: dict):
        """OVER/UNDER 逆転アラートを発報する

        「OVERが多い状態」→「UNDERが多い状態」に切り替わった瞬間に発報（買いシグナル）
        「UNDERが多い状態」→「OVERが多い状態」に切り替わった瞬間に発報（売りシグナル）
        5%以上の差がある場合のみ優勢判定。拮抗中は前回の状態を維持（リセットしない）。
        """
        # 現在値が0（寄り前）はスキップ
        if not board_data.get("last_price"):
            return

        over_qty  = int(board_data.get("over_qty")  or 0)
        under_qty = int(board_data.get("under_qty") or 0)
        total     = over_qty + under_qty
        if total == 0:
            return

        # 5%以上の差がある場合のみ優勢判定
        ratio = (over_qty - under_qty) / total  # 正 → OVER優勢, 負 → UNDER優勢
        if abs(ratio) < 0.05:
            return  # 拮抗中 → 前回の状態を維持（リセットしない）

        current_side = "OVER" if ratio > 0 else "UNDER"
        prev_side    = self._ou_state.get(code, "")

        # 前回と同じサイドなら何もしない
        if current_side == prev_side:
            return

        # 優勢サイドが逆転した → アラート発報
        self._ou_state[code] = current_side
        symbol_name = board_data.get("symbol_name", code)
        last_price  = board_data.get("last_price", 0)

        if current_side == "UNDER":
            pattern = "ou_under"
            detail  = (f"UNDER {under_qty:,} > OVER {over_qty:,}  "
                       f"買い圧力が売り圧力を上回った")
            logger.info(f"[O/U逆転→UNDER優勢] {code} "
                        f"UNDER={under_qty} OVER={over_qty}")
        else:
            pattern = "ou_over"
            detail  = (f"OVER {over_qty:,} > UNDER {under_qty:,}  "
                       f"売り圧力が買い圧力を上回った")
            logger.info(f"[O/U逆転→OVER優勢] {code} "
                        f"OVER={over_qty} UNDER={under_qty}")

        self._alert_popup.show(
            symbol      = code,
            symbol_name = symbol_name,
            price       = last_price,
            pattern     = pattern,
            detail      = detail,
        )

    def _update_candle_and_detect(self, code: str, board_data: dict):
        """5分足を更新し、ペナントブレイクを検知してアラートを発報する"""
        last_price = board_data.get("last_price", 0)
        volume     = int(board_data.get("volume") or 0)
        time_str   = board_data.get("time", "")

        if not last_price or last_price <= 0:
            return
        if not time_str or time_str == "--:--:--":
            return

        # "HH:MM:SS" → datetime（今日の日付で補完）
        try:
            today = date.today()
            t     = datetime.strptime(time_str, "%H:%M:%S")
            timestamp = datetime(today.year, today.month, today.day,
                                 t.hour, t.minute, t.second)
        except Exception:
            return

        # ── 足更新（足が確定したときだけ None 以外が返る）
        completed = self._candle_builder.update(code, last_price, volume, timestamp)
        if completed is None:
            return

        # ── 確定足が出たのでペナント検知
        candles = self._candle_builder.get_candles(
            code, count=self._pennant_detector.max_candles)
        result = self._pennant_detector.detect(candles, last_price)
        if result is None:
            return

        # ── クールダウン（同一銘柄で足3本以内の連続発火を防ぐ）
        candle_idx = self._candle_builder.candle_count(code)
        last_idx   = self._last_alert.get(code, -999)
        if candle_idx - last_idx < 3:
            logger.debug(f"[ALERT クールダウン中] {code} "
                         f"({candle_idx - last_idx}/3本 経過)")
            return

        self._last_alert[code] = candle_idx

        # ── ポップアップ表示（すでにメインスレッド上）
        symbol_name = board_data.get("symbol_name", "")
        detail = (
            f"抵抗線={result['resist_price']:.0f}  "
            f"R²(H={result['r2_high']:.2f}/L={result['r2_low']:.2f})  "
            f"収束率={result['width_ratio']:.0%}"
        )
        self._alert_popup.show(
            symbol      = code,
            symbol_name = symbol_name,
            price       = last_price,
            pattern     = result["pattern"],
            detail      = detail,
        )

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

        # ── 内部状態をクリア（起動時の残存データ防止）
        self._candle_builder.clear_all()
        self._last_alert.clear()
        self._ou_state.clear()
        self._open_alerts.clear()

        # ── AlertPopup をクリア
        for popup in self._alert_popup._active[:]:
            try:
                popup.destroy()
            except:
                pass
        self._alert_popup._active.clear()

        logger.info("[MainWindow] シャットダウン処理完了：すべての内部状態をクリアしました")
