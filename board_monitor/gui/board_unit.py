"""
Board Unit v13

フォントサイズ大型化 + 情報パネル充実化:
  ┌─────────────────────────────────────────────────┐
  │ [1:6920][2:9984][3:7013][4:5016][5:5803]  タブ │
  ├──────────────┬──────────────────────────────────┤
  │ 6920         │ 売数量  |  値段   | 買数量        │
  │ レーザーテック │  成行                            │
  │ 22,000       │  OVER  4,000                     │
  │ ▲4.8%       │        22,010   ...sell           │
  │ ──────────  │  ...                              │
  │ 出来高        │  22,000  ← 現値                  │
  │  2,000,000   │  21,999   ...bid                  │
  │ VWAP         │  ...                              │
  │  21,750      │  UNDER 3,000                      │
  │ ──────────  │                                   │
  │ 始 21,500    │                                   │
  │ 高 22,050    │                                   │
  │ 安 21,800    │                                   │
  │ 終 21,000    │                                   │
  │ 14:59:59     │                                   │
  └──────────────┴──────────────────────────────────┘
"""
import tkinter as tk
from tkinter import simpledialog
from typing import Optional, Dict, Callable, List

# ── 銘柄名辞書（主要日本株） ──────────────────────────────────
STOCK_NAMES: Dict[str, str] = {
    "1301": "極洋",         "1332": "日水",         "1605": "INPEX",
    "1808": "長谷工",       "1925": "大和ハウス",    "1928": "積水ハウス",
    "2002": "日清粉G",      "2269": "明治HD",        "2282": "日本ハム",
    "2413": "エムスリー",   "2502": "アサヒG",       "2503": "キリンHD",
    "2651": "ローソン",     "2802": "味の素",        "2914": "JT",
    "3003": "ヒューリック", "3086": "J.フロント",    "3099": "三越伊勢丹",
    "3382": "セブン&アイ",  "3436": "SUMCO",         "3563": "FOOD&LIFE",
    "3659": "ネクソン",     "4063": "信越化学",      "4183": "三井化学",
    "4188": "三菱ケミカル", "4502": "武田薬品",      "4503": "アステラス",
    "4507": "塩野義製薬",   "4519": "中外製薬",      "4523": "エーザイ",
    "4543": "テルモ",       "4568": "第一三共",      "4578": "大塚HD",
    "4661": "OLC",          "4689": "Zホールディング","4755": "楽天G",
    "5016": "JX金属",       "5019": "出光興産",      "5020": "ENEOS",
    "5108": "ブリヂストン", "5401": "日本製鉄",      "5411": "JFE",
    "5713": "住友金属鉱山", "5715": "古河機金",      "5801": "古河電工",
    "5803": "フジクラ",     "6098": "リクルートHD",  "6146": "ディスコ",
    "6273": "SMC",          "6301": "コマツ",        "6326": "クボタ",
    "6367": "ダイキン",     "6471": "日本精工",      "6501": "日立製作所",
    "6503": "三菱電機",     "6506": "安川電機",      "6532": "ベイカレント",
    "6594": "ニデック",     "6645": "オムロン",      "6701": "NEC",
    "6702": "富士通",       "6723": "ルネサス",      "6752": "パナソニック",
    "6758": "ソニーG",      "6762": "TDK",           "6857": "アドバンテスト",
    "6861": "キーエンス",   "6869": "シスメックス",  "6920": "レーザーテック",
    "6954": "ファナック",   "6971": "京セラ",        "6976": "太陽誘電",
    "6981": "村田製作所",   "7011": "三菱重工",      "7013": "IHI",
    "7182": "ゆうちょ銀行", "7201": "日産自動車",    "7203": "トヨタ自動車",
    "7267": "ホンダ",       "7269": "スズキ",        "7270": "SUBARU",
    "7272": "ヤマハ発動機", "7741": "HOYA",          "7751": "キヤノン",
    "7832": "バンナムHD",   "7974": "任天堂",        "8001": "伊藤忠",
    "8002": "丸紅",         "8031": "三井物産",      "8035": "東京エレク",
    "8053": "住友商事",     "8058": "三菱商事",      "8113": "ユニ・チャーム",
    "8267": "イオン",       "8306": "三菱UFJ",       "8309": "三井住友T",
    "8316": "三井住友FG",   "8411": "みずほFG",      "8591": "オリックス",
    "8601": "大和証券G",    "8604": "野村HD",        "8697": "JPX",
    "8725": "MS&AD",        "8750": "第一生命HD",    "8766": "東京海上HD",
    "8801": "三井不動産",   "8802": "三菱地所",      "8804": "東京建物",
    "9001": "東武鉄道",     "9005": "東急",          "9020": "JR東日本",
    "9021": "JR西日本",     "9022": "JR東海",        "9064": "ヤマトHD",
    "9101": "日本郵船",     "9104": "商船三井",      "9107": "川崎汽船",
    "9201": "JAL",          "9202": "ANA",           "9432": "NTT",
    "9433": "KDDI",         "9434": "ソフトバンク",  "9735": "セコム",
    "9766": "コナミG",      "9983": "ファストリ",    "9984": "ソフトバンクG",
}

# ── 色定数（ライトテーマ）────────────────────────────────────
UNIT_BG      = "#d0d0d0"   # ユニット外枠
ROW_BG       = "white"     # 値段列・空セルの背景
HDR_BG       = "#aaaaaa"   # ヘッダー行背景
HDR_FG       = "#111111"   # ヘッダーテキスト
INFO_BG      = "#e8e8e8"   # 情報パネル背景

ASK_CELL_BG  = "#ddeeff"   # 売数量セル背景（薄水色）
ASK_FG       = "#0033cc"   # 売数量テキスト（濃い青）
PRICE_ASK_FG = "#0033cc"   # 売側の値段テキスト（青）

BID_CELL_BG  = "#fff0f0"   # 買数量セル背景（薄ピンク）
BID_FG       = "#cc0000"   # 買数量テキスト（赤）
PRICE_BID_FG = "#cc0000"   # 買側の値段テキスト（赤）

OVER_FG      = "#0033cc"   # OVER テキスト
UNDER_FG     = "#cc0000"   # UNDER テキスト

# ── フォント（大型化）────────────────────────────────────────
FONT_BOARD  = ("Courier New", 13)            # 板の数値
FONT_HDR    = ("Courier New", 12, "bold")    # 板のヘッダー
FONT_TAB    = ("Courier New", 9)             # タブ
FONT_INFO_S = ("Courier New", 9)             # 情報パネル 小
FONT_INFO_M = ("Courier New", 10)            # 情報パネル 中
FONT_PRICE  = ("Courier New", 15, "bold")    # 現在値（大）

# ── フラッシュ色 ─────────────────────────────────────────────
ASK_FLASH = "#ffff44"   # 売フラッシュ（黄色 ← 注文変化時にピカピカ）
BID_FLASH = "#ff8888"   # 買フラッシュ（明るい赤）

# ── 情報パネル幅（px）──────────────────────────────────────
LEFT_W = 125

# ── 行識別子 ─────────────────────────────────────────────────
# _ASK[0] = 表示最上段 = 最悪値（最高値の売気配）
# _ASK[9] = 表示最下段 = 最良値（買い板に近い側）
_NARINARI = "narinari"  # 成行行（市場注文・両側）
_OVER     = "over"      # OVER行（売板10段より奥・売側のみ）
_UNDER    = "under"
_ASK      = [f"ask_{i}" for i in range(10)]
_BID      = [f"bid_{i}" for i in range(10)]
# _CURRENT 行は廃止: 現在値は ask/bid 板の中でハイライト表示
_ALL_ROWS = [_NARINARI, _OVER] + _ASK + _BID + [_UNDER]


class BoardUnit(tk.Frame):
    def __init__(self, parent, unit_key: str,
                 on_subscribe: Optional[Callable] = None,
                 on_unsubscribe: Optional[Callable] = None,
                 on_slot_change: Optional[Callable] = None):
        super().__init__(parent, bg=UNIT_BG,
                         highlightbackground="gray50", highlightthickness=1)
        self.pack_propagate(False)

        self.unit_key       = unit_key
        self.on_subscribe   = on_subscribe
        self.on_unsubscribe = on_unsubscribe
        self.on_slot_change = on_slot_change   # (unit_key, slot_idx, code)

        self.a_codes: List[str]           = [""] * 5
        self.a_names: List[str]           = [""] * 5
        self.current_idx: int             = -1
        self.current_code: Optional[str]  = None

        self.board_cache: Dict[str, dict]    = {}
        self.last_ask_vols: Dict[float, int] = {}
        self.last_bid_vols: Dict[float, int] = {}

        self._last_price_status: str = ""   # 音アラート用（直前の特気配状態）

        self._create_layout()

    # ─────────────────────────────────────────────────────────
    #  レイアウト構築
    # ─────────────────────────────────────────────────────────

    def _create_layout(self):
        """上部タブ → 下部（左情報パネル ＋ 右板テーブル）"""
        self._build_tabs()
        tk.Frame(self, bg="gray60", height=1).pack(fill=tk.X)
        self._build_content()

    def _build_tabs(self):
        """5つの水平タブ（銘柄切替ボタン）"""
        self.tab_frame = tk.Frame(self, bg="#bbbbbb")
        self.tab_frame.pack(fill=tk.X, expand=False)
        for i in range(5):
            self.tab_frame.columnconfigure(i, weight=1)

        self.a_buttons: List[tk.Button] = []
        for i in range(5):
            btn = tk.Button(
                self.tab_frame,
                text=str(i + 1),
                bg="#cccccc", fg="#555555",
                font=FONT_TAB,
                padx=2, pady=1,
                relief=tk.FLAT, bd=0,
                activebackground="#999999", activeforeground="black",
                command=lambda idx=i: self._on_a_click(idx),
            )
            btn.grid(row=0, column=i, sticky="ew", padx=1, pady=1)
            btn.bind("<Double-Button-1>",
                     lambda e, idx=i: self._on_tab_dblclick(idx))
            self.a_buttons.append(btn)

    def _build_content(self):
        """左情報パネル（固定幅）＋ 右板テーブル（伸縮）"""
        content = tk.Frame(self, bg=UNIT_BG)
        content.pack(fill=tk.BOTH, expand=True)

        # 左パネル（固定幅）
        left = tk.Frame(content, bg=INFO_BG, width=LEFT_W)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        self._build_info_panel(left)

        # 縦セパレータ
        tk.Frame(content, bg="gray60", width=1).pack(side=tk.LEFT, fill=tk.Y)

        # 右パネル（板テーブル）
        right = tk.Frame(content, bg=ROW_BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_board_table(right)

    def _build_info_panel(self, parent: tk.Frame):
        """左情報パネル
        コード・銘柄名 / 現値 / 前日比% / 出来高 / VWAP
        始値 / 高値(時刻) / 安値(時刻) / 前日終値 / 時刻
        """
        # ── 銘柄コード+名（ヘッダー色帯）
        self.code_label = tk.Label(
            parent, text="----",
            bg="#3355aa", fg="white",
            font=("Courier New", 10, "bold"),
            anchor="center",
            wraplength=LEFT_W - 6,
            pady=2,
        )
        self.code_label.pack(fill=tk.X)

        # ── 現在値（大きめ）
        self.price_label = tk.Label(
            parent, text="---",
            bg=INFO_BG, fg="#333333",
            font=FONT_PRICE,
            anchor="center",
        )
        self.price_label.pack(fill=tk.X)

        # ── 前日比（絶対値）例: +1,000 / -500
        self.diff_label = tk.Label(
            parent, text="---",
            bg=INFO_BG, fg="#333333",
            font=("Courier New", 12, "bold"),
            anchor="center",
        )
        self.diff_label.pack(fill=tk.X)

        # ── 前日比%
        self.change_label = tk.Label(
            parent, text="0.0%",
            bg=INFO_BG, fg="#333333",
            font=FONT_INFO_M,
            anchor="center",
        )
        self.change_label.pack(fill=tk.X)

        tk.Frame(parent, bg="gray70", height=1).pack(fill=tk.X, pady=2)

        # ── 出来高
        tk.Label(parent, text="出来高", bg=INFO_BG, fg="#666666",
                 font=FONT_INFO_S, anchor="w", padx=4).pack(fill=tk.X)
        self.volume_label = tk.Label(
            parent, text="----",
            bg=INFO_BG, fg="#333333",
            font=FONT_INFO_S, anchor="e", padx=4,
        )
        self.volume_label.pack(fill=tk.X)

        # ── VWAP
        tk.Label(parent, text="VWAP", bg=INFO_BG, fg="#666666",
                 font=FONT_INFO_S, anchor="w", padx=4).pack(fill=tk.X)
        self.vwap_label = tk.Label(
            parent, text="----",
            bg=INFO_BG, fg="#333333",
            font=FONT_INFO_S, anchor="e", padx=4,
        )
        self.vwap_label.pack(fill=tk.X)

        tk.Frame(parent, bg="gray70", height=1).pack(fill=tk.X, pady=2)

        # ── 前日終値（始値の上に配置）
        self.prev_label = tk.Label(
            parent, text="前終 ----",
            bg=INFO_BG, fg="#555555",
            font=FONT_INFO_S, anchor="w", padx=4,
        )
        self.prev_label.pack(fill=tk.X)

        # ── 始値
        self.open_label = tk.Label(
            parent, text="始  ----",
            bg=INFO_BG, fg="#333333",
            font=FONT_INFO_S, anchor="w", padx=4,
        )
        self.open_label.pack(fill=tk.X)

        # ── 高値
        self.high_label = tk.Label(
            parent, text="高  ----",
            bg=INFO_BG, fg="#cc0000",
            font=FONT_INFO_S, anchor="w", padx=4,
        )
        self.high_label.pack(fill=tk.X)

        # ── 安値
        self.low_label = tk.Label(
            parent, text="安  ----",
            bg=INFO_BG, fg="#0033cc",
            font=FONT_INFO_S, anchor="w", padx=4,
        )
        self.low_label.pack(fill=tk.X)

        tk.Frame(parent, bg="gray70", height=1).pack(fill=tk.X, pady=2)

        # ── 時刻
        self.time_label = tk.Label(
            parent, text="--:--:--",
            bg=INFO_BG, fg="#555555",
            font=FONT_INFO_S, anchor="center",
        )
        self.time_label.pack(fill=tk.X)

        # ── 今日のロウソク足（Canvas）
        tk.Frame(parent, bg="gray70", height=1).pack(fill=tk.X, pady=2)
        self.candle_canvas = tk.Canvas(
            parent, bg="white",
            height=90, highlightthickness=1,
            highlightbackground="gray70",
        )
        self.candle_canvas.pack(fill=tk.X, padx=4, pady=2)

    def _build_board_table(self, parent: tk.Frame):
        """
        3列グリッドレイアウト:
          列0: 売数量（薄水色背景・青テキスト）
          列1: 値段  （白背景・青or赤テキスト）
          列2: 買数量（薄ピンク背景・赤テキスト）
        """
        board = tk.Frame(parent, bg=ROW_BG)
        board.pack(fill=tk.BOTH, expand=True)

        board.columnconfigure(0, weight=1)
        board.columnconfigure(1, weight=1)
        board.columnconfigure(2, weight=1)

        # ── ヘッダー行
        tk.Label(board, text="売数量", bg=HDR_BG, fg=HDR_FG,
                 font=FONT_HDR, anchor="e", padx=4,
                 ).grid(row=0, column=0, sticky="ew")
        tk.Label(board, text="", bg=HDR_BG,
                 ).grid(row=0, column=1, sticky="ew")
        tk.Label(board, text="買数量", bg=HDR_BG, fg=HDR_FG,
                 font=FONT_HDR, anchor="w", padx=4,
                 ).grid(row=0, column=2, sticky="ew")

        # ── データ行
        self._ask_lbl:   Dict[str, tk.Label] = {}
        self._price_lbl: Dict[str, tk.Label] = {}
        self._bid_lbl:   Dict[str, tk.Label] = {}

        for r_idx, row_id in enumerate(_ALL_ROWS, start=1):

            if row_id == _NARINARI:
                a_bg = ASK_CELL_BG; a_fg = ASK_FG
                p_text = "成行";    p_fg = OVER_FG;        p_font = FONT_HDR
                b_bg = BID_CELL_BG; b_fg = BID_FG

            elif row_id == _OVER:
                a_bg = ASK_CELL_BG; a_fg = ASK_FG
                p_text = "OVER";    p_fg = OVER_FG;        p_font = FONT_HDR
                b_bg = ROW_BG;      b_fg = ROW_BG

            elif row_id in _ASK:
                a_bg = ASK_CELL_BG; a_fg = ASK_FG
                p_text = "";         p_fg = PRICE_ASK_FG; p_font = FONT_BOARD
                b_bg = ROW_BG;      b_fg = ROW_BG

            elif row_id in _BID:
                a_bg = ROW_BG;      a_fg = ROW_BG
                p_text = "";         p_fg = PRICE_BID_FG; p_font = FONT_BOARD
                b_bg = BID_CELL_BG; b_fg = BID_FG

            else:  # _UNDER
                a_bg = ROW_BG;      a_fg = ROW_BG
                p_text = "UNDER";   p_fg = UNDER_FG;      p_font = FONT_HDR
                b_bg = BID_CELL_BG; b_fg = BID_FG

            a_lbl = tk.Label(board, text="", bg=a_bg, fg=a_fg,
                             font=FONT_BOARD, anchor="e", padx=4)
            a_lbl.grid(row=r_idx, column=0, sticky="ew")

            p_lbl = tk.Label(board, text=p_text, bg=ROW_BG, fg=p_fg,
                             font=p_font, anchor="center", padx=2)
            p_lbl.grid(row=r_idx, column=1, sticky="ew")

            b_lbl = tk.Label(board, text="", bg=b_bg, fg=b_fg,
                             font=FONT_BOARD, anchor="w", padx=4)
            b_lbl.grid(row=r_idx, column=2, sticky="ew")

            self._ask_lbl[row_id]   = a_lbl
            self._price_lbl[row_id] = p_lbl
            self._bid_lbl[row_id]   = b_lbl

        # 全行に均等ウェイト → 板がエリア全体を隙間なく埋める
        for r_i in range(len(_ALL_ROWS) + 2):
            board.rowconfigure(r_i, weight=1)

    # ─────────────────────────────────────────────────────────
    #  Aリスト管理
    # ─────────────────────────────────────────────────────────

    def set_a_slot(self, idx: int, code: str, name: str = ""):
        """タブ idx に銘柄を設定"""
        if not (0 <= idx < 5):
            return
        self.a_codes[idx] = code
        self.a_names[idx] = name
        # タブ表示: 銘柄名があれば銘柄名、なければコード、空なら番号
        if name:
            disp = name
        elif code:
            disp = code
        else:
            disp = str(idx + 1)
        self.a_buttons[idx].config(
            text=disp,
            fg="#111111" if code else "#888888",
        )
        if idx == 0 and self.current_idx == -1 and code:
            self._on_a_click(0)

        # 設定保存コールバック
        if self.on_slot_change and code:
            self.on_slot_change(self.unit_key, idx, code)

    def _on_tab_dblclick(self, idx: int):
        """タブダブルクリック: 証券コード入力ダイアログ
        空欄のまま OK → スロットを削除
        """
        current = self.a_codes[idx] if self.a_codes[idx] else ""
        code = simpledialog.askstring(
            "銘柄入力",
            f"スロット {idx + 1}  証券コードを入力：\n（空欄のままOKで削除）",
            initialvalue=current,
            parent=self.winfo_toplevel(),
        )
        if code is None:   # キャンセル
            return
        code = code.strip()

        # 空欄 → スロット削除
        if not code:
            old_code = self.a_codes[idx]
            if old_code:
                if self.on_unsubscribe:
                    self.on_unsubscribe(self.unit_key, old_code)
                if self.on_slot_change:
                    self.on_slot_change(self.unit_key, idx, "")
            self.set_a_slot(idx, "", "")
            if self.current_idx == idx:
                self._clear_b()
                self.current_idx = -1
            return

        # 銘柄名を辞書から取得（未登録ならコードのまま）
        name = STOCK_NAMES.get(code, "")
        self.set_a_slot(idx, code, name)

    def _on_a_click(self, idx: int):
        """タブクリック: 銘柄切替"""
        code = self.a_codes[idx]
        if not code:
            return

        if self.current_idx >= 0:
            self.a_buttons[self.current_idx].config(bg="#cccccc", fg="#555555")
        self.current_idx = idx
        self.a_buttons[idx].config(bg="#446688", fg="white")

        old_code = self.current_code
        if self.on_unsubscribe and old_code and old_code != code:
            self.on_unsubscribe(self.unit_key, old_code)
        if self.on_subscribe:
            self.on_subscribe(self.unit_key, code)

        self.current_code = code
        name = self.a_names[idx]
        self.code_label.config(text=f"{code}\n{name}" if name else code)

        if code in self.board_cache:
            self._apply_board_data(self.board_cache[code])
        else:
            self._clear_b()

    # ─────────────────────────────────────────────────────────
    #  データ更新
    # ─────────────────────────────────────────────────────────

    def push_board_data(self, code: str, board_data: dict):
        """受信データをキャッシュし、表示中の銘柄なら即時反映"""
        self.board_cache[code] = board_data

        # APIから銘柄名が取得できたらスロットに保存・タブ更新
        api_name = board_data.get("symbol_name", "")
        if api_name:
            try:
                idx = self.a_codes.index(code)
                if not self.a_names[idx]:           # まだ名前が未設定なら
                    self.a_names[idx] = api_name
                    self.a_buttons[idx].config(text=api_name)
                    if idx == self.current_idx:
                        self.code_label.config(
                            text=f"{code}\n{api_name}"
                        )
            except ValueError:
                pass

        if code == self.current_code:
            self._apply_board_data(board_data)

    def _apply_board_data(self, data: dict):
        last         = data.get("last_price", 0)
        chg          = data.get("change_pct", 0)
        prev         = data.get("previous_close", 0)
        is_calc      = data.get("is_calc_price", False)   # 均衡価格フラグ
        price_status = data.get("price_status", "")       # 特買い/特売り/連買い/連売り

        # ── 特気配 / 連気配 → 音アラート（現在オフ・鳴らすタイミング決定後に有効化）
        # if price_status and price_status != self._last_price_status:
        #     self._play_alert(price_status)
        self._last_price_status = price_status
        vol  = data.get("volume", 0)
        vwap = data.get("vwap", 0)
        tstr = data.get("time", "--:--:--")
        opn  = data.get("open", 0)
        high = data.get("high", 0)
        low  = data.get("low", 0)
        t_op = data.get("time_open", "")
        t_hi = data.get("time_high", "")
        t_lo = data.get("time_low", "")

        # 小数点価格の検出（データ実測 + TSE呼値ルール の OR）
        _chk = [p for p in [last, opn, high, low, prev] if p]
        _chk += [q.get("price", 0) for q in data.get("asks", []) + data.get("bids", [])
                 if q.get("price", 0) > 0]
        _has_frac   = any(abs(p - round(p)) > 0.001 for p in _chk)
        _ref        = last or (_chk[0] if _chk else 0)
        _tse_dec    = (self._get_tick(_ref) < 1) if _ref else False
        self._decimal_price = _has_frac or _tse_dec

        # 上昇/下落でカラーを決定
        if prev > 0 and last > prev:
            price_fg  = "#cc0000"   # 赤
            header_bg = "#663333"   # 暗赤
        elif prev > 0 and last < prev:
            price_fg  = "#0033cc"   # 青
            header_bg = "#333366"   # 暗青
        else:
            price_fg  = "#333333"
            header_bg = "#3355aa"

        # ── 左パネル更新
        self.code_label.config(bg=header_bg)

        # 現在値表示（0は未確定なので「----」）
        # 特別気配・連続気配のラベル色設定
        _STATUS_COLOR = {
            "特買い": "#cc0000",
            "特売り": "#0033cc",
            "連買い": "#990000",
            "連売り": "#000099",
        }
        if last:
            price_text = self._fmt_p(last)
            if is_calc:
                price_text += " 均"
            self.price_label.config(text=price_text, fg=price_fg)
        else:
            self.price_label.config(text="----", fg="#888888")

        # 前日比（last=0 のときは表示しない）
        if last and prev:
            diff = last - prev
            if diff > 0:
                self.diff_label.config(text=f"+{self._fmt_p(diff)}", fg="#cc0000")
            elif diff < 0:
                self.diff_label.config(text=f"-{self._fmt_p(abs(diff))}", fg="#0033cc")
            else:
                self.diff_label.config(text="±0", fg="#333333")
        else:
            self.diff_label.config(text="----", fg="#888888")

        if last and chg:
            if chg > 0:
                self.change_label.config(text=f"▲{chg:.2f}%", fg="#cc0000")
            elif chg < 0:
                self.change_label.config(text=f"▼{abs(chg):.2f}%", fg="#0033cc")
            else:
                self.change_label.config(text="±0.00%", fg="#333333")
        else:
            self.change_label.config(text="----", fg="#888888")

        self.volume_label.config(text=f"{vol:,}" if vol else "----")
        self.vwap_label.config(  text=f"V {self._fmt_p(vwap)}" if vwap else "V ----")

        # 始値・高値・安値・前日終値
        # HH:MM:SS → HH:MM に短縮
        hm_op = t_op[:5] if t_op else ""
        hm_hi = t_hi[:5] if t_hi else ""
        hm_lo = t_lo[:5] if t_lo else ""

        self.prev_label.config( text=f"前終 {self._fmt_p(prev)}"                          if prev else "前終 ----")
        self.open_label.config( text=f"始 {self._fmt_p(opn)} {hm_op}".strip()             if opn  else "始 ----")
        self.high_label.config( text=f"高 {self._fmt_p(high)} {hm_hi}".strip()           if high else "高 ----")
        self.low_label.config(  text=f"安 {self._fmt_p(low)} {hm_lo}".strip()            if low  else "安 ----")
        self.time_label.config( text=tstr)

        # _update_board / _price_text で参照できるよう先に保存
        self._prev_close  = prev
        self._open_price  = opn
        self._vwap_price  = vwap

        self._update_board(data)
        self._draw_candle(opn, high, low, last, prev)

    def _draw_candle(self, opn: float, high: float, low: float,
                     last: float, prev: float):
        """今日の日足ロウソク足を candle_canvas に描画する。
        ・本体  : 始値〜現値（赤=陽線 / 青=陰線）
        ・ヒゲ  : 高値・安値
        ・前終値: 灰色の点線横ライン
        """
        c = self.candle_canvas
        c.delete("all")

        if not opn or not high or not low or not last:
            return

        # キャンバス実寸（初回は1が返ることがあるのでフォールバック）
        c.update_idletasks()
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20:
            w = LEFT_W - 10
        if h < 20:
            h = 90

        # 価格レンジ（前終値も含めて全体を表示）
        all_prices = [opn, high, low, last]
        if prev:
            all_prices.append(prev)
        lo_all = min(all_prices)
        hi_all = max(all_prices)
        span   = hi_all - lo_all
        if span <= 0:
            span = max(hi_all * 0.005, 1.0)

        # 余白
        pad_x = 16
        pad_y = 8
        dh    = h - 2 * pad_y

        def pty(p: float) -> float:
            """価格 → Canvas y座標（上が高値）"""
            return pad_y + dh * (1.0 - (p - lo_all) / span)

        cx      = w / 2.0
        body_hw = max(3, int(w * 0.18))   # 本体の半幅

        # ── 前日終値の点線横ライン
        if prev:
            py = pty(prev)
            c.create_line(pad_x, py, w - pad_x, py,
                          fill="#aaaaaa", width=1, dash=(3, 3))

        # ── ヒゲ（上下）
        y_top_body = pty(max(opn, last))
        y_bot_body = pty(min(opn, last))
        y_high     = pty(high)
        y_low      = pty(low)

        c.create_line(cx, y_high, cx, y_top_body, fill="#444444", width=1)
        c.create_line(cx, y_bot_body, cx, y_low,  fill="#444444", width=1)

        # ── 本体（陽線=赤 / 陰線=青）
        body_color  = "#cc0000" if last >= opn else "#0033cc"
        body_top    = y_top_body
        body_bottom = y_bot_body

        if abs(body_bottom - body_top) < 2:
            # 同値ドージ: 横線で表現
            c.create_line(cx - body_hw, body_top, cx + body_hw, body_top,
                          fill=body_color, width=2)
        else:
            c.create_rectangle(
                cx - body_hw, body_top,
                cx + body_hw, body_bottom,
                fill=body_color, outline="#333333", width=1,
            )

    @staticmethod
    def _get_tick(price: float) -> float:
        """東証 現物市場の呼値単位を返す（2024年ルール）
        参考: JPX 株券等の取引値段に関する規則
        """
        if   price <   1_000: return 0.1
        elif price <   3_000: return 0.5
        elif price <   5_000: return 1
        elif price <  10_000: return 5
        elif price <  30_000: return 10
        elif price <  50_000: return 50
        elif price < 100_000: return 100
        elif price < 500_000: return 500
        else:                 return 1_000

    @staticmethod
    def _vwap_tick_round(vwap: float) -> float:
        """東証の呼値単位に VWAP を丸めた目標価格を返す。
        例: VWAP=151.73 → 呼値0.1円 → 151.7
            VWAP=1,624.8 → 呼値0.5円 → 1,625.0
            VWAP=12,194  → 呼値10円  → 12,190
        """
        if   vwap <   1_000: tick = 0.1
        elif vwap <   3_000: tick = 0.5
        elif vwap <   5_000: tick = 1
        elif vwap <  10_000: tick = 5
        elif vwap <  30_000: tick = 10
        elif vwap <  50_000: tick = 50
        elif vwap < 100_000: tick = 100
        elif vwap < 500_000: tick = 500
        else:                tick = 1_000
        result = round(vwap / tick) * tick
        # 浮動小数点誤差を除去（0.1・0.5刻み時）
        return round(result, 2) if tick < 1 else result

    def _price_color(self, price: float) -> str:
        """前日終値との比較で価格テキスト色を返す"""
        prev = getattr(self, '_prev_close', 0)
        if prev <= 0:
            return "#333333"
        if price > prev:
            return "#cc0000"   # 赤（前日比プラス）
        if price < prev:
            return "#0033cc"   # 青（前日比マイナス）
        return "#555555"       # グレー（同値）

    def _price_marker(self, price: float) -> str:
        """始値(O) / VWAP(V) と一致する価格にマーカーを返す（最大3文字 "O V"）
        ・O: 始値と一致（0.1円刻みは±0.05、それ以外は±0.5）
        ・V: 板の中でVWAPに最も近い価格（_vwap_nearest に保存済み）
        """
        opn          = getattr(self, '_open_price',   0)
        vwap_nearest = getattr(self, '_vwap_nearest', 0)
        tol = 0.05 if getattr(self, '_decimal_price', False) else 0.5
        markers = []
        if opn          and abs(price - opn)          < tol:
            markers.append("O")
        if vwap_nearest and abs(price - vwap_nearest) < tol:
            markers.append("V")
        return " ".join(markers)

    def _fmt_p(self, price: float) -> str:
        """価格フォーマット（0.1円刻み銘柄は小数1桁、それ以外は整数）"""
        if getattr(self, '_decimal_price', False):
            return f"{price:,.1f}"
        return f"{price:,.0f}"

    def _price_text(self, price: float) -> str:
        """価格テキストを固定幅で返す（O/V マーカー有無でずれない）"""
        marker = self._price_marker(price)
        # マーカー部分は常に4文字分を確保（" V  " / " O  " / " O V" / "    "）
        suffix = f" {marker:<3}" if marker else "    "
        return f"{self._fmt_p(price)}{suffix}"

    def _update_board(self, data: dict):
        asks      = data.get("asks", [])
        bids      = data.get("bids", [])
        asks_sign = data.get("asks_sign", [])
        bids_sign = data.get("bids_sign", [])
        last      = data.get("last_price", 0)  # 現在値（ハイライト判定用）

        # ── VWAP を呼値単位に丸めた価格が板に存在すれば V を付ける
        vwap = getattr(self, '_vwap_price', 0)
        if vwap:
            target = self._vwap_tick_round(vwap)   # 呼値単位に丸めた目標価格
            all_prices = [q.get("price", 0) for q in asks + bids if q.get("price", 0) > 0]
            # 目標価格が今の板に存在するときだけ V を立てる
            self._vwap_nearest = target if any(abs(p - target) < 0.5 for p in all_prices) else 0
        else:
            self._vwap_nearest = 0

        # ── 成行（市場注文・両側）
        market_ask = data.get("market_ask_qty", 0)
        market_bid = data.get("market_bid_qty", 0)
        self._ask_lbl[_NARINARI].config(text=f"{market_ask:,}" if market_ask else "")
        self._bid_lbl[_NARINARI].config(text=f"{market_bid:,}" if market_bid else "")

        # ── OVER（売板10段より奥の注文合計・売側のみ）
        over_qty = data.get("over_qty", 0)
        if not over_qty:
            for i, s in enumerate(asks_sign):
                if s == "OVER" and i < len(asks):
                    over_qty = asks[i].get("volume", 0)
                    break
        self._ask_lbl[_OVER].config(text=f"{over_qty:,}" if over_qty else "")

        # ── UNDER（買板10段より奥の注文合計）
        under_qty = data.get("under_qty", 0)
        # フォールバック: 旧形式 bids_sign に "UNDER" があれば使用
        if not under_qty:
            for i, s in enumerate(bids_sign):
                if s == "UNDER" and i < len(bids):
                    under_qty = bids[i].get("volume", 0)
                    break
        self._bid_lbl[_UNDER].config(text=f"{under_qty:,}" if under_qty else "")

        # ── 売り気配（通常10段）
        # サイン情報を保持しながらフィルタ
        normal_asks = [
            (a, asks_sign[i] if i < len(asks_sign) else "")
            for i, a in enumerate(asks)
            if i >= len(asks_sign) or asks_sign[i] not in ("OVER", "成行")
        ]
        display_asks = list(reversed(normal_asks[:10]))

        # 浮動小数点誤差のみ許容（事実上の完全一致）
        tol = 0.001

        # 現在値が ask/bid 板に含まれているか事前チェック
        last_in_ask = last and any(
            abs(a.get("price", 0) - last) < tol
            for a, _ in normal_asks[:10]
        )
        last_in_bid = last and any(
            abs(b.get("price", 0) - last) < tol
            for b, _ in [
                (b, bids_sign[i] if i < len(bids_sign) else "")
                for i, b in enumerate(bids)
                if i >= len(bids_sign) or bids_sign[i] not in ("UNDER", "成行")
            ]
        )
        current_inserted = False  # スプレッド中間の現在値を空行に挿入済みか

        for idx, row_id in enumerate(_ASK):
            if idx < len(display_asks):
                a, sign    = display_asks[idx]
                price      = a.get("price", 0)
                vol        = a.get("volume", 0)
                p_text     = self._price_text(price)
                prefix     = f"{sign} " if sign in ("特", "連") else ""
                is_current = last and (abs(price - last) < tol)

                if is_current:
                    # 現在値行: 赤背景ハイライト
                    self._price_lbl[row_id].config(
                        text=p_text, bg="#cc0000", fg="white",
                        font=("Courier New", 13, "bold"))
                    self._ask_lbl[row_id].config(
                        text=f"{prefix}{vol:,}", bg=ASK_CELL_BG)
                    self._bid_lbl[row_id].config(text="", bg=ROW_BG)
                else:
                    self._price_lbl[row_id].config(
                        text=p_text, bg=ROW_BG,
                        fg=self._price_color(price), font=FONT_BOARD)
                    self._ask_lbl[row_id].config(
                        text=f"{prefix}{vol:,}", bg=ASK_CELL_BG)
                    self._bid_lbl[row_id].config(text="", bg=ROW_BG)

                if vol != self.last_ask_vols.get(price, -1):
                    if not is_current:
                        self._flash(self._ask_lbl[row_id], ASK_FLASH, ASK_CELL_BG, 700)
                    self.last_ask_vols[price] = vol

            elif (not last_in_ask and not last_in_bid
                  and not current_inserted and last):
                # スプレッド中間の現在値 → ask板の最初の空行に赤ハイライトで挿入
                p_text = self._price_text(last)
                self._price_lbl[row_id].config(
                    text=p_text, bg="#cc0000", fg="white",
                    font=("Courier New", 13, "bold"))
                self._ask_lbl[row_id].config(text="", bg=ROW_BG)
                self._bid_lbl[row_id].config(text="", bg=ROW_BG)
                current_inserted = True
            else:
                self._price_lbl[row_id].config(
                    text="--", fg="#aaaaaa", bg=ROW_BG, font=FONT_BOARD)
                self._ask_lbl[row_id].config(text="", bg=ROW_BG)
                self._bid_lbl[row_id].config(text="", bg=ROW_BG)

        # ── 買い気配（通常10段）
        normal_bids = [
            (b, bids_sign[i] if i < len(bids_sign) else "")
            for i, b in enumerate(bids)
            if i >= len(bids_sign) or bids_sign[i] not in ("UNDER", "成行")
        ]
        # ask板が満杯でスプレッド中間の場合、bid板先頭に現在値行を挿入
        if not current_inserted and not last_in_ask and not last_in_bid and last:
            bid_display = [({"price": last, "volume": -1}, "__CURRENT__")] + normal_bids
        else:
            bid_display = normal_bids

        for idx, row_id in enumerate(_BID):
            if idx < len(bid_display):
                b, sign    = bid_display[idx]
                price      = b.get("price", 0)
                vol        = b.get("volume", 0)
                is_current = (sign == "__CURRENT__") or (
                    last and (abs(price - last) < tol))

                if is_current:
                    # 現在値行: 赤背景ハイライト（数量なし or bid数量）
                    p_text = self._price_text(last if sign == "__CURRENT__" else price)
                    self._price_lbl[row_id].config(
                        text=p_text, bg="#cc0000", fg="white",
                        font=("Courier New", 13, "bold"))
                    self._ask_lbl[row_id].config(text="", bg=ROW_BG)
                    if sign == "__CURRENT__":
                        # スプレッド中間挿入行：bid数量なし
                        self._bid_lbl[row_id].config(text="", bg=ROW_BG)
                    else:
                        prefix = f"{sign} " if sign in ("特", "連") else ""
                        self._bid_lbl[row_id].config(
                            text=f"{prefix}{vol:,}", bg=BID_CELL_BG)
                    current_inserted = True
                else:
                    p_text = self._price_text(price)
                    prefix = f"{sign} " if sign in ("特", "連") else ""
                    self._price_lbl[row_id].config(
                        text=p_text, bg=ROW_BG,
                        fg=self._price_color(price), font=FONT_BOARD)
                    self._ask_lbl[row_id].config(text="", bg=ROW_BG)
                    self._bid_lbl[row_id].config(
                        text=f"{prefix}{vol:,}", bg=BID_CELL_BG)

                if not is_current and vol != self.last_bid_vols.get(price, -1):
                    self._flash(self._bid_lbl[row_id], BID_FLASH, BID_CELL_BG, 700)
                if not is_current:
                    self.last_bid_vols[price] = vol
            else:
                self._price_lbl[row_id].config(
                    text="--", fg="#aaaaaa", bg=ROW_BG, font=FONT_BOARD)
                self._ask_lbl[row_id].config(text="", bg=ROW_BG)
                self._bid_lbl[row_id].config(text="", bg=ROW_BG)

    @staticmethod
    def _play_alert(status: str):
        """特気配・連気配のアラート音（Windows winsound）
        特買い/連買い → 高音（買い圧力）
        特売り/連売り → 低音（売り圧力）
        """
        try:
            import winsound
            import threading
            def _beep():
                if status in ("特買い", "連買い"):
                    winsound.Beep(1400, 350)
                elif status in ("特売り", "連売り"):
                    winsound.Beep(500, 350)
            threading.Thread(target=_beep, daemon=True).start()
        except Exception:
            pass   # 非Windows環境などでエラーになっても無視

    def _flash(self, widget: tk.Label, flash_bg: str, orig_bg: str, ms: int):
        widget.config(bg=flash_bg)
        self.after(ms, lambda: widget.config(bg=orig_bg))

    def _clear_b(self):
        """Bエリアをリセット"""
        self.price_label.config(text="---", fg="#333333")
        self.diff_label.config(text="---", fg="#333333")
        self.change_label.config(text="0.0%", fg="#333333")
        self.code_label.config(bg="#3355aa")
        self.volume_label.config(text="----")
        self.vwap_label.config(text="V ----")
        self.open_label.config(text="始 ----")
        self.high_label.config(text="高 ----")
        self.low_label.config(text="安 ----")
        self.prev_label.config(text="終 ----")
        self.time_label.config(text="--:--:--")
        self.candle_canvas.delete("all")
        for row_id in _ALL_ROWS:
            self._ask_lbl[row_id].config(text="")
            self._bid_lbl[row_id].config(text="")
            if row_id not in (_OVER, _UNDER):
                self._price_lbl[row_id].config(
                    text="", bg=ROW_BG, font=FONT_BOARD)
