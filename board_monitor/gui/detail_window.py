"""
詳細ウィンドウ
板をクリックした時に表示
- 左パネル: 銘柄情報（銘柄名、始値、高値、安値、前日値、VWAP、出来高）
- 右パネル: 板（売り・買い）
"""
import tkinter as tk
from tkinter import simpledialog
from typing import Optional, Dict

class DetailWindow:
    """板の詳細情報を表示するウィンドウ"""

    def __init__(self, parent_root: tk.Tk, stock_code: str, board_data: Optional[dict]):
        """
        Args:
            parent_root: 親 root ウィンドウ
            stock_code: 銘柄コード（例: "9984"）
            board_data: 板データ
        """
        self.stock_code = stock_code
        self.board_data = board_data

        # 新しいウィンドウを作成
        self.window = tk.Toplevel(parent_root)
        self.window.title(f"詳細 - {stock_code}")
        self.window.geometry("800x600")
        self.window.configure(bg="black")

        self._create_layout()

    def _create_layout(self):
        """レイアウトを作成"""
        # 左パネル: 銘柄情報
        left_frame = tk.Frame(self.window, bg="black", width=300)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        left_frame.pack_propagate(False)

        self._create_stock_info_panel(left_frame)

        # 区切り線
        sep = tk.Frame(self.window, bg="gray20", width=2)
        sep.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        # 右パネル: 板
        right_frame = tk.Frame(self.window, bg="black")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._create_board_panel(right_frame)

    def _create_stock_info_panel(self, parent: tk.Frame):
        """銘柄情報パネルを作成

        Args:
            parent: 親フレーム
        """
        # タイトル
        title_label = tk.Label(
            parent,
            text=f"銘柄: {self.stock_code}",
            bg="navy",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5
        )
        title_label.pack(fill=tk.X, expand=False)

        # 情報項目
        info_items = [
            ("始値", "----"),
            ("高値", "----"),
            ("安値", "----"),
            ("前日終値", "----"),
            ("VWAP", "----"),
            ("出来高", "----"),
        ]

        for label_text, default_value in info_items:
            info_frame = tk.Frame(parent, bg="black", height=30)
            info_frame.pack(fill=tk.X, expand=False)
            info_frame.pack_propagate(False)

            label = tk.Label(
                info_frame,
                text=label_text,
                bg="black",
                fg="white",
                font=("Arial", 9),
                width=10,
                anchor="w",
                padx=10
            )
            label.pack(side=tk.LEFT, fill=tk.X, expand=False)

            value = tk.Label(
                info_frame,
                text=default_value,
                bg="black",
                fg="yellow",
                font=("Courier New", 10, "bold"),
                anchor="e",
                padx=10
            )
            value.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def _create_board_panel(self, parent: tk.Frame):
        """板パネルを作成

        Args:
            parent: 親フレーム
        """
        # タイトル
        title_label = tk.Label(
            parent,
            text="オーダーブック",
            bg="navy",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5
        )
        title_label.pack(fill=tk.X, expand=False)

        # 板の詳細表示（売り）
        board_frame = tk.Frame(parent, bg="black")
        board_frame.pack(fill=tk.BOTH, expand=True)

        # ダミー実装：実際の板データを表示
        for i in range(10):
            row = tk.Frame(board_frame, bg="maroon", height=20)
            row.pack(fill=tk.X, expand=False)
            row.pack_propagate(False)

            label = tk.Label(
                row,
                text=f"売 {i+1}",
                bg="maroon",
                fg="white",
                font=("Courier New", 8),
                width=10
            )
            label.pack(side=tk.LEFT, padx=5)

            volume = tk.Label(
                row,
                text="0",
                bg="maroon",
                fg="yellow",
                font=("Courier New", 8),
                width=10
            )
            volume.pack(side=tk.LEFT, padx=5)

    def show(self):
        """ウィンドウを表示"""
        self.window.focus()
        self.window.grab_set()

    def close(self):
        """ウィンドウを閉鎖"""
        self.window.destroy()
