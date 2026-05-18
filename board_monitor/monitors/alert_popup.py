"""
アラートポップアップ

パターン検知時に画面右上に Tkinter のポップアップを表示する。
  - 8秒後に自動消滅
  - 複数同時表示時は縦にスタック
  - Windows winsound で上昇アラート音
"""
import tkinter as tk
from typing import List
import logging

logger = logging.getLogger(__name__)

# パターン → 表示ラベル
PATTERN_LABELS = {
    "pennant_break_up": "▲ ペナントブレイク（上抜け）",
}

# ポップアップの色設定
POPUP_BG   = "#cc2200"   # 背景（濃い赤）
POPUP_FG   = "#ffffff"   # 文字（白）
POPUP_W    = 340         # 幅(px)
POPUP_H    = 90          # 高さ(px)
POPUP_GAP  = 8           # ポップアップ間の隙間


class AlertPopup:
    """パターン検知アラートを画面右上にポップアップ表示"""

    def __init__(self, root: tk.Tk):
        self.root    = root
        self._active: List[tk.Toplevel] = []

    # ─────────────────────────────────────────────────────────

    def show(
        self,
        symbol:        str,
        symbol_name:   str,
        price:         float,
        pattern:       str,
        detail:        str = "",
        auto_close_ms: int = 8000,
    ):
        """アラートポップアップを表示する（メインスレッドから呼ぶこと）。

        Args:
            symbol       : 銘柄コード
            symbol_name  : 銘柄名
            price        : 現在値
            pattern      : パターン識別子（"pennant_break_up" 等）
            detail       : 補足テキスト（省略可）
            auto_close_ms: 自動消滅までのミリ秒
        """
        self._play_sound(pattern)

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)    # タイトルバーなし
        popup.attributes("-topmost", True)
        popup.configure(bg=POPUP_BG)

        # ── 位置: 画面右上・スタック
        sw  = self.root.winfo_screenwidth()
        idx = len(self._active)
        px  = sw - POPUP_W - 20
        py  = 20 + idx * (POPUP_H + POPUP_GAP)
        popup.geometry(f"{POPUP_W}x{POPUP_H}+{px}+{py}")

        # ── ラベル
        label_text = PATTERN_LABELS.get(pattern, pattern)
        tk.Label(
            popup, text=label_text,
            bg=POPUP_BG, fg=POPUP_FG,
            font=("Courier New", 13, "bold"),
            anchor="center",
        ).pack(fill=tk.X, pady=(10, 2))

        name_str = f"{symbol_name}" if symbol_name else ""
        tk.Label(
            popup,
            text=f"{symbol}  {name_str}  {price:,.1f}円",
            bg=POPUP_BG, fg=POPUP_FG,
            font=("Courier New", 11),
            anchor="center",
        ).pack(fill=tk.X)

        if detail:
            tk.Label(
                popup, text=detail,
                bg=POPUP_BG, fg="#ffcccc",
                font=("Courier New", 9),
                anchor="center",
            ).pack(fill=tk.X)

        # ── クリックで即閉じ
        popup.bind("<Button-1>", lambda e: self._close(popup))

        # ── 自動消滅
        self._active.append(popup)
        popup.after(auto_close_ms, lambda: self._close(popup))

        logger.info(f"[ALERT] {pattern} {symbol} {symbol_name} "
                    f"{price:,.1f}円")

    # ─────────────────────────────────────────────────────────

    def _close(self, popup: tk.Toplevel):
        try:
            popup.destroy()
        except Exception:
            pass
        if popup in self._active:
            self._active.remove(popup)

    @staticmethod
    def _play_sound(pattern: str):
        """Windows winsound でアラート音を鳴らす"""
        try:
            import winsound
            import threading
            def _beep():
                # 上昇系: 高めの2音
                winsound.Beep(1400, 150)
                winsound.Beep(1800, 250)
            threading.Thread(target=_beep, daemon=True).start()
        except Exception:
            pass
