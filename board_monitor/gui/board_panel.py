"""
個別の板パネル表示（v4: Excel レイアウト対応）
- ヘッダー情報の大幅拡張（8行）
- 売買段数：10段対応
- 時刻情報表示
- 注文変化時にフラッシュ

重要: expand=False で拡大を防ぐ
"""
import tkinter as tk
from tkinter import simpledialog
from typing import Optional, Dict, Callable

# UIパラメータ
PRICE_COL_W = 6  # 価格列の文字幅
VOLUME_COL_W = 5  # 数量列の文字幅
HEADER_ROW_H = 15   # ヘッダ行の高さ
INFO_ROW_H = 12    # 情報行の高さ
BOARD_ROW_H = 11   # 板行の高さ


class BoardPanel(tk.Frame):
    """1つの板を表示するパネル（Excel レイアウト対応）"""

    def __init__(self, parent, stock_code: Optional[str], slot_key: str,
                 font_small, font_board, row_height: int, width: int,
                 on_click: Optional[Callable] = None,
                 on_double_click: Optional[Callable] = None,
                 depth: int = 10):  # 板の深さ（10段対応）
        """
        Args:
            parent: 親フレーム
            stock_code: 銘柄コード（例: "9984"）
            slot_key: スロットキー（例: "slot_1"）
            font_small: 小さいフォント
            font_board: 板用フォント
            row_height: 行の高さ(px)
            width: パネル幅(px)
            on_click: 左クリック時のコールバック
            on_double_click: ダブルクリック時のコールバック
            depth: 板の深さ（10段）
        """
        super().__init__(parent, bg="black", width=width, height=600)
        self.pack_propagate(False)

        self.stock_code = stock_code
        self.slot_key = slot_key
        self.font_small = font_small
        self.font_board = font_board
        self.row_height = row_height
        self.width = width
        self.on_click = on_click
        self.on_double_click = on_double_click
        self.depth = depth  # 板の深さ

        # 内部状態
        self.board_data = None
        self.last_ask_volumes = {}
        self.last_bid_volumes = {}
        self.price_info = {}

        self._create_layout()
        self._bind_events()

    def _bind_events(self):
        """イベントバインディング"""
        self.bind("<Button-1>", self._on_click)
        self.bind("<Double-Button-1>", self._on_double_click)
        for child in self.winfo_children():
            child.bind("<Button-1>", self._on_click)
            child.bind("<Double-Button-1>", self._on_double_click)

    def _on_click(self, event):
        """左クリックイベント"""
        if self.on_click:
            self.on_click(self.slot_key, self.stock_code)

    def _on_double_click(self, event):
        """ダブルクリックイベント"""
        if self.on_double_click:
            self.on_double_click(self.slot_key)

    def _create_layout(self):
        """Excel レイアウト対応のレイアウトを作成"""

        # ========== ヘッダー（銘柄コード + 現在値 + 騰落率）==========
        self.header_frame = tk.Frame(self, bg="navy", height=HEADER_ROW_H)
        self.header_frame.pack(fill=tk.X, expand=False)
        self.header_frame.pack_propagate(False)

        # 左：銘柄コード
        self.code_label = tk.Label(
            self.header_frame,
            text=self.stock_code or "----",
            bg="navy",
            fg="white",
            font=("Courier New", 7, "bold"),
            width=6,
            anchor="w",
            padx=2
        )
        self.code_label.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        # 中央：現在値
        self.price_label = tk.Label(
            self.header_frame,
            text="0.00",
            bg="navy",
            fg="yellow",
            font=("Courier New", 7, "bold"),
            width=9,
            anchor="e",
            padx=2
        )
        self.price_label.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        # 右：騰落率
        self.change_label = tk.Label(
            self.header_frame,
            text="0%",
            bg="navy",
            fg="white",
            font=("Courier New", 6),
            width=4,
            anchor="e",
            padx=1
        )
        self.change_label.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        # ========== 詳細情報フレーム（8行拡張）==========
        self.detail_frame = tk.Frame(self, bg="gray10", height=96)
        self.detail_frame.pack(fill=tk.X, expand=False)
        self.detail_frame.pack_propagate(False)

        # 詳細情報ラベル（8行）
        self.detail_labels = {}
        detail_keys = [
            ("current_time", "現在値: ----"),
            ("vwap", "VWAP: ----"),
            ("volume", "出来高: ----"),
            ("prev_change", "前日比: --"),
            ("prev_close", "前日値: ----"),
            ("open_time", "始値: ----"),
            ("high_time", "高値: ----"),
            ("low_time", "安値: ----"),
        ]

        for key, text in detail_keys:
            label = tk.Label(
                self.detail_frame,
                text=text,
                bg="gray10",
                fg="gray70",
                font=("Courier New", 5),
                anchor="w",
                padx=1
            )
            label.pack(fill=tk.X, expand=False)
            self.detail_labels[key] = label

        # ========== 板エリア（10段対応）==========
        self.board_frame = tk.Frame(self, bg="black")
        self.board_frame.pack(fill=tk.BOTH, expand=True)
        self.board_frame.pack_propagate(False)

        # 売り気配（上から）
        self.ask_rows = []
        for i in range(self.depth):
            row = self._create_board_row(
                parent=self.board_frame,
                label=f"売{i+1}",
                bg_color="#330000",  # 暗い赤
                fg_color="#ff6666",  # 明るい赤
                row_key=f"ask_{i}"
            )
            self.ask_rows.append(row)

        # 買い気配（上から）
        self.bid_rows = []
        for i in range(self.depth):
            row = self._create_board_row(
                parent=self.board_frame,
                label=f"買{i+1}",
                bg_color="#003300",  # 暗い緑
                fg_color="#66ff66",  # 明るい緑
                row_key=f"bid_{i}"
            )
            self.bid_rows.append(row)

    def _create_board_row(self, parent, label: str, bg_color: str, fg_color: str, row_key: str) -> Dict:
        """板の1行を作成"""
        row_frame = tk.Frame(parent, bg=bg_color, height=BOARD_ROW_H)
        row_frame.pack(fill=tk.X, expand=False)
        row_frame.pack_propagate(False)

        # ラベル（売1、買1など）
        label_w = tk.Label(
            row_frame,
            text=label,
            bg=bg_color,
            fg=fg_color,
            font=("Courier New", 5),
            width=3,
            anchor="w",
            padx=1
        )
        label_w.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        # 価格
        price_w = tk.Label(
            row_frame,
            text="----",
            bg=bg_color,
            fg="white",
            font=("Courier New", 5),
            width=8,
            anchor="e",
            padx=1
        )
        price_w.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        # 数量
        volume_w = tk.Label(
            row_frame,
            text="0",
            bg=bg_color,
            fg=fg_color,
            font=("Courier New", 5),
            width=5,
            anchor="e",
            padx=1
        )
        volume_w.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        return {
            "frame": row_frame,
            "label": label_w,
            "price": price_w,
            "volume": volume_w,
            "row_key": row_key
        }

    def set_stock_code(self, stock_code: Optional[str]):
        """銘柄コードを設定（スロット変更時）"""
        self.stock_code = stock_code
        self.code_label.config(text=stock_code or "----")
        self.board_data = None
        self._clear_board()

    def _clear_board(self):
        """板をクリア"""
        self.price_label.config(text="0.00")
        self.change_label.config(text="0%")

        for key in self.detail_labels:
            if key == "current_time":
                self.detail_labels[key].config(text="現在値: ----")
            elif key == "vwap":
                self.detail_labels[key].config(text="VWAP: ----")
            elif key == "volume":
                self.detail_labels[key].config(text="出来高: ----")
            elif key == "prev_change":
                self.detail_labels[key].config(text="前日比: --")
            elif key == "prev_close":
                self.detail_labels[key].config(text="前日値: ----")
            elif key == "open_time":
                self.detail_labels[key].config(text="始値: ----")
            elif key == "high_time":
                self.detail_labels[key].config(text="高値: ----")
            elif key == "low_time":
                self.detail_labels[key].config(text="安値: ----")

        for row in self.ask_rows + self.bid_rows:
            row["price"].config(text="----")
            row["volume"].config(text="0")

    def update_data(self, board_data: dict):
        """板データを更新"""
        if not self.stock_code or not board_data:
            return

        self.board_data = board_data

        # ========== ヘッダー情報の更新 ==========
        last_price = board_data.get("last_price", 0)
        change_pct = board_data.get("change_pct", 0)
        previous_close = board_data.get("previous_close", 0)
        time_str = board_data.get("time", "--:--:--")

        self.price_label.config(text=f"{last_price:.2f}")

        # 騰落率の色分け
        if change_pct > 0:
            self.change_label.config(fg="red", text=f"+{change_pct:.1f}%")
        elif change_pct < 0:
            self.change_label.config(fg="blue", text=f"{change_pct:.1f}%")
        else:
            self.change_label.config(fg="white", text="0%")

        # ========== ヘッダー背景色：前日値との比較 ==========
        if previous_close > 0:
            if last_price > previous_close:
                self.header_frame.config(bg="#4d2626")  # 暗い赤
            elif last_price < previous_close:
                self.header_frame.config(bg="#26264d")  # 暗い青
            else:
                self.header_frame.config(bg="navy")
        else:
            self.header_frame.config(bg="navy")

        # ========== 詳細情報の更新（8行） ==========
        self.detail_labels["current_time"].config(
            text=f"現在値: {last_price:.2f} ({time_str})"
        )

        vwap = board_data.get("vwap", 0)
        self.detail_labels["vwap"].config(
            text=f"VWAP: {vwap:.2f}" if vwap > 0 else "VWAP: ----"
        )

        volume = board_data.get("volume", 0)
        self.detail_labels["volume"].config(
            text=f"出来高: {volume:,}" if volume > 0 else "出来高: ----"
        )

        if previous_close > 0:
            prev_diff = last_price - previous_close
            self.detail_labels["prev_change"].config(
                text=f"前日比: {prev_diff:+.2f}"
            )
        else:
            self.detail_labels["prev_change"].config(text="前日比: --")

        self.detail_labels["prev_close"].config(
            text=f"前日値: {previous_close:.2f}" if previous_close > 0 else "前日値: ----"
        )

        open_price = board_data.get("open", 0)
        time_open = board_data.get("time_open", "--:--")
        self.detail_labels["open_time"].config(
            text=f"始値: {open_price:.0f} ({time_open})" if open_price > 0 else "始値: ----"
        )

        high_price = board_data.get("high", 0)
        time_high = board_data.get("time_high", "--:--")
        self.detail_labels["high_time"].config(
            text=f"高値: {high_price:.0f} ({time_high})" if high_price > 0 else "高値: ----"
        )

        low_price = board_data.get("low", 0)
        time_low = board_data.get("time_low", "--:--")
        self.detail_labels["low_time"].config(
            text=f"安値: {low_price:.0f} ({time_low})" if low_price > 0 else "安値: ----"
        )

        # ========== 売り気配の更新（10段）==========
        asks = board_data.get("asks", [])
        for i, row in enumerate(self.ask_rows):
            if i < len(asks):
                ask = asks[i]
                price = ask.get("price", 0)
                volume = ask.get("volume", 0)

                row["price"].config(text=f"{price:.2f}")
                row["volume"].config(text=str(volume))

                # フラッシュ判定
                if volume != self.last_ask_volumes.get(price, 0):
                    self._apply_flash(row["frame"], "#ffb6c1")  # ピンク
                    self.last_ask_volumes[price] = volume
            else:
                row["price"].config(text="----")
                row["volume"].config(text="0")

        # ========== 買い気配の更新（10段）==========
        bids = board_data.get("bids", [])
        for i, row in enumerate(self.bid_rows):
            if i < len(bids):
                bid = bids[i]
                price = bid.get("price", 0)
                volume = bid.get("volume", 0)

                row["price"].config(text=f"{price:.2f}")
                row["volume"].config(text=str(volume))

                # フラッシュ判定
                if volume != self.last_bid_volumes.get(price, 0):
                    self._apply_flash(row["frame"], "#add8e6")  # 水色
                    self.last_bid_volumes[price] = volume
            else:
                row["price"].config(text="----")
                row["volume"].config(text="0")

    def _apply_flash(self, widget: tk.Frame, flash_color: str):
        """フラッシュ効果を適用（300ms）"""
        original_bg = widget.cget("bg")
        widget.config(bg=flash_color)
        self.after(300, lambda: widget.config(bg=original_bg))
