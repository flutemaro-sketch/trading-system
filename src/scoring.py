"""
スコアリングモジュール

仕様書のとおり、5項目 × 20点 = 合計100点満点でスコアリング:
  ① 下駄パターン
  ② 出来高条件
  ③ 753トレンド
  ④ 信用残
  ⑤ アイランド・パターン

各関数は1銘柄分の DataFrame(日足、Date昇順)を受け取り、
(score: int, note: str) を返す。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

# ---------- 重要セクター(加点対象) ----------
IMPORTANT_SECTOR_KEYWORDS = [
    "AI", "ai", "デジタル", "データセンター",
    "軍事", "防衛", "造船", "船舶",
    "宇宙", "ドローン",
    "半導体", "仮想通貨",
]


# ---------- スコア結果のコンテナ ----------

@dataclass
class StockScore:
    code: str
    name: str = ""
    sector: str = ""
    geta: int = 0
    volume: int = 0
    trend: int = 0
    margin: int = 0
    island: int = 0
    sector_bonus: int = 0
    geta_note: str = ""
    volume_note: str = ""
    trend_note: str = ""
    margin_note: str = ""
    island_note: str = ""
    main_pattern: str = ""
    comment: str = ""
    lion_rank: int | None = None  # らいおんまる氏の元順位(参考表示用)
    bb_position: str = ""           # ボリンジャーバンド位置(上限超/バンド内/下限超)
    settlement_alert: str = ""      # 決算日フラグ(当日/3日以内/7日以内/空欄)
    consensus_comparison: str = ""  # コンセンサス比較(期待超過/期待通り/期待未達/比較不可)
    buyback_alert: str = ""         # 自社株買いフラグ(底値スイング候補/実施期間中/期間前/空欄)

    @property
    def total(self) -> int:
        return (
            self.geta + self.volume + self.trend
            + self.margin + self.island + self.sector_bonus
        )


# ---------- ① 下駄パターン (20点) ----------

def score_geta(df: pd.DataFrame) -> tuple[int, str]:
    """下駄パターン: 上髭4倍以上 + 寄引同値±0.3% + 出来高前日比150%以上。

    各条件 7/7/6 点で配点(合計20)。
    """
    if len(df) < 2:
        return 0, "データ不足"

    last = df.iloc[-1]
    prev = df.iloc[-2]
    o, h, l, c, v = (
        last["Open"], last["High"], last["Low"], last["Close"], last["Volume"]
    )
    prev_v = prev["Volume"]

    # NaN ガード
    if pd.isna(o) or pd.isna(c) or pd.isna(h) or pd.isna(v):
        return 0, "値欠損"

    score = 0
    notes: list[str] = []

    # 1. 上髭が実体の4倍以上
    body = abs(c - o)
    upper_shadow = h - max(o, c)
    if body > 0 and upper_shadow / body >= 4:
        score += 7
        notes.append("上髭4倍")
    elif body == 0 and upper_shadow > 0:
        # 寄引同値で上髭ある = 強烈なシグナル
        score += 7
        notes.append("十字線+上髭")

    # 2. 寄引同値(±0.3%)
    if o > 0 and abs(c - o) / o <= 0.003:
        score += 7
        notes.append("寄引同値")

    # 3. 出来高が前日比150%以上
    if prev_v > 0 and v / prev_v >= 1.5:
        score += 6
        notes.append(f"出来高{v/prev_v:.1f}倍")

    return score, " / ".join(notes) if notes else "-"


# ---------- ② 出来高条件 (20点) ----------

def score_volume(df: pd.DataFrame) -> tuple[int, str]:
    """出来高: 5日平均比2倍 + 500万株 + 出来高だまり形成。"""
    if len(df) < 5:
        return 0, "データ不足"

    last_v = df["Volume"].iloc[-1]
    if pd.isna(last_v):
        return 0, "値欠損"

    score = 0
    notes: list[str] = []

    # 1. 5日平均(前日まで)比 - 2倍で10点、1.5倍で5点
    avg5 = df["Volume"].iloc[-6:-1].mean() if len(df) >= 6 else df["Volume"].iloc[:-1].mean()
    if avg5 > 0:
        ratio = last_v / avg5
        if ratio >= 2.0:
            score += 10
            notes.append(f"5日平均{ratio:.1f}倍")
        elif ratio >= 1.5:
            score += 5
            notes.append(f"5日平均{ratio:.1f}倍")

    # 2. 500万株以上
    if last_v >= 5_000_000:
        score += 5
        notes.append(f"{last_v/1e6:.1f}M株")

    # 3. 出来高だまり: 直近3日平均 vs 過去10日平均
    if len(df) >= 13:
        avg3 = df["Volume"].iloc[-3:].mean()
        avg10 = df["Volume"].iloc[-13:-3].mean()
        if avg10 > 0 and avg3 / avg10 >= 1.3:
            score += 5
            notes.append("出来高だまり")

    return min(score, 20), " / ".join(notes) if notes else "-"


# ---------- ③ 753 トレンドスコア (20点) ----------

def score_trend_753(df: pd.DataFrame) -> tuple[int, str]:
    """753スコア: 7日×15 + 5日×21 + 3日×35 を陽線(+)/陰線(-)で集計、20点正規化。

    + 5/25/75日移動平均が全部上向きなら追加加点。
    """
    if len(df) < 7:
        return 0, "データ不足"

    def yang_minus_yin(d: pd.DataFrame) -> int:
        body = d["Close"] - d["Open"]
        yang = (body > 0).sum()
        yin = (body < 0).sum()
        return int(yang - yin)

    last_7 = df.iloc[-7:]
    last_5 = df.iloc[-5:]
    last_3 = df.iloc[-3:]

    raw = (
        yang_minus_yin(last_7) * 15
        + yang_minus_yin(last_5) * 21
        + yang_minus_yin(last_3) * 35
    )
    # 最大値: 7*15 + 5*21 + 3*35 = 315
    base_score = max(0, min(15, int(raw / 315 * 15)))

    notes = [f"753={raw}"]

    # 移動平均整列ボーナス(最大5点)
    ma_bonus = 0
    if len(df) >= 75:
        ma5 = df["Close"].rolling(5).mean()
        ma25 = df["Close"].rolling(25).mean()
        ma75 = df["Close"].rolling(75).mean()
        # 直近2点の比較で上向き判定
        if (
            ma5.iloc[-1] > ma5.iloc[-2]
            and ma25.iloc[-1] > ma25.iloc[-2]
            and ma75.iloc[-1] > ma75.iloc[-2]
        ):
            ma_bonus = 5
            notes.append("MA5/25/75↑")
        elif ma5.iloc[-1] > ma25.iloc[-1] > ma75.iloc[-1]:
            # パーフェクトオーダー
            ma_bonus = 3
            notes.append("MA順序◎")

    return base_score + ma_bonus, " / ".join(notes)


# ---------- ④ 信用残 (20点) - 簡易版 ----------

def score_margin(
    df: pd.DataFrame, margin_data: dict | None = None
) -> tuple[int, str]:
    """信用残スコア。

    現状は信用残データの取得を後回しにしているため、
    価格動向から「踏み上げ余地」を簡易推定する仮実装。
    """
    if len(df) < 25:
        return 0, "データ不足"

    score = 0
    notes: list[str] = []

    # 高値圏接近度: 直近25日高値に対する終値の位置
    high25 = df["High"].iloc[-25:].max()
    low25 = df["Low"].iloc[-25:].min()
    last_close = df["Close"].iloc[-1]
    if high25 > low25:
        position = (last_close - low25) / (high25 - low25)
        # 安値圏(<0.3) は加点(信用買残少なめ想定)、高値圏(>0.8)は減点
        if position < 0.3:
            score += 8
            notes.append("安値圏")
        elif position > 0.8:
            score += 0
            notes.append("高値圏(注意)")
        else:
            score += 4
            notes.append("中位")

    # 出来高の安定的増加 = 新陳代謝進行 と仮定
    if len(df) >= 13:
        v_recent = df["Volume"].iloc[-3:].mean()
        v_past = df["Volume"].iloc[-13:-3].mean()
        if v_past > 0 and v_recent / v_past >= 1.2:
            score += 6
            notes.append("出来高漸増")

    # 信用残データが渡されていれば本格判定(将来)
    if margin_data:
        notes.append("[信用残データあり-未実装]")

    return min(score, 20), " / ".join(notes) if notes else "-"


# ---------- ⑤ アイランド・パターン (20点) ----------

def score_island(df: pd.DataFrame) -> tuple[int, str]:
    """アイランド: GU + 続き足 + 高値更新 + GU後の出来高こなし。"""
    if len(df) < 5:
        return 0, "データ不足"

    last = df.iloc[-1]
    prev = df.iloc[-2]
    o, h, c = last["Open"], last["High"], last["Close"]
    prev_h, prev_c = prev["High"], prev["Close"]

    score = 0
    notes: list[str] = []

    # 1. GU(ギャップアップ): 当日寄値 > 前日高値
    if o > prev_h:
        gap_pct = (o - prev_c) / prev_c * 100
        score += 8
        notes.append(f"GU({gap_pct:+.1f}%)")
        # 小GU(1%前後)は理想とのこと
        if 0.5 <= gap_pct <= 1.5:
            score += 2
            notes.append("小GU理想")

    # 2. 続き足: 前日終値からほぼ同値で寄付(±0.5%)
    if prev_c > 0 and abs(o - prev_c) / prev_c <= 0.005:
        score += 5
        notes.append("続き足")

    # 3. 高値更新: 直近5日の高値を当日が更新
    last5 = df.iloc[-5:]
    if h > last5["High"].iloc[:-1].max():
        score += 3
        notes.append("5日高値更新")

    # 4. GU後の出来高こなし: 直近5日内にGUがあって、その後も出来高維持
    last5 = df.iloc[-5:].copy()
    last5_prev_close = last5["Close"].shift(1)
    last5_prev_high = last5["High"].shift(1)
    gu_days = (last5["Open"] > last5_prev_high).fillna(False)
    if gu_days.any() and len(last5) >= 3:
        post_gu_v = last5.loc[gu_days.idxmax():, "Volume"].mean()
        before_gu_v = df["Volume"].iloc[-30:-5].mean() if len(df) >= 30 else last5["Volume"].mean()
        if before_gu_v > 0 and post_gu_v / before_gu_v >= 1.2:
            score += 2
            notes.append("GU後出来高維持")

    return min(score, 20), " / ".join(notes) if notes else "-"


# ---------- ボリンジャーバンド位置判定 ----------

def score_bollinger_position(df: pd.DataFrame, window: int = 25, sigma: float = 2.0) -> str:
    """直近終値がボリンジャーバンド(±2σ)のどこにあるか判定。

    今日学んだ教訓：
    - ボリンジャーバンド上限より上で始まっている = 売られやすい環境
    - バンド内での動きが正常。上限超えはだましパターンのリスク高。

    Returns:
        "[BB上限超]" / "BB上位" / "BB中位" / "BB下位" / "[BB下限超]" / "データ不足"
    """
    if len(df) < window:
        return "データ不足"

    close = df["Close"]
    ma = close.rolling(window).mean()
    std = close.rolling(window).std()

    upper2 = ma + sigma * std
    lower2 = ma - sigma * std

    last_close = close.iloc[-1]
    last_upper = upper2.iloc[-1]
    last_lower = lower2.iloc[-1]
    last_ma = ma.iloc[-1]

    if pd.isna(last_upper) or pd.isna(last_lower):
        return "データ不足"

    if last_close > last_upper:
        return "[BB上限超]"
    elif last_close > last_ma + (last_upper - last_ma) * 0.5:
        return "BB上位"
    elif last_close < last_lower:
        return "[BB下限超]"
    elif last_close < last_ma - (last_ma - last_lower) * 0.5:
        return "BB下位"
    else:
        return "BB中位"


# ---------- コンセンサス比較 ----------

def score_consensus_comparison(
    actual_profit: int | None,
    consensus_profit: int | None,
    profit_type: str = "operating"  # "operating" or "net"
) -> str:
    """実績 vs コンセンサスの差分を判定。

    今日学んだ教訓：
    - 実績 > コンセンサス = 期待超過 → 買われる
    - 実績 ≈ コンセンサス = 期待通り → 翌日利確売り（材料出尽くし）
    - 実績 < コンセンサス = 期待未達 → 売られる

    Returns:
        "✅期待超過" / "◎期待通り" / "❌期待未達" / "比較不可"
    """
    if actual_profit is None or consensus_profit is None or consensus_profit == 0:
        return "比較不可"

    diff_pct = ((actual_profit - consensus_profit) / consensus_profit) * 100

    if diff_pct >= 5:  # 5%以上超過
        return "✅期待超過"
    elif -2 <= diff_pct < 5:  # ±2%以内 = 期待通り
        return "◎期待通り"
    else:  # -2%未満 = 期待未達
        return "❌期待未達"


# ---------- 自社株買いフラグ ----------

def check_buyback_alert(
    df: pd.DataFrame,
    buyback_pct: float | None,
    buyback_start,
    buyback_end,
    buyback_method: str = "",
) -> str:
    """自社株買い情報から底値スイング判定を行う。

    今日学んだ教訓：
    - 市場買い付けのみ有効（OTC・TOBは無効）
    - 実施期間開始までに株価が自社株買い比率以上下落 → 底値サポートあり
    - 翌日開始の場合、翌日に比率以上下落したらすぐスイング可能

    判定ルール：
    1. buyback_method == "market" のみ有効
    2. 現在日が実施期間中かチェック
    3. 株価が buyback_pct 以上下落しているかチェック

    Returns:
        "🟢底値スイング候補" / "🔵自社株買い実施期間中" / "⏳実施開始待ち" / ""
    """
    # 市場買い付け以外は無効
    if not buyback_method or buyback_method.lower() != "market":
        return ""

    if buyback_pct is None or pd.isna(buyback_pct):
        return ""
    if buyback_start is None or pd.isna(buyback_start):
        return ""

    today = date.today()
    start_date = pd.Timestamp(buyback_start).date()
    end_date = pd.Timestamp(buyback_end).date() if buyback_end is not None and not pd.isna(buyback_end) else None

    # 実施期間終了済みは対象外
    if end_date and today > end_date:
        return ""

    # 現在値と実施期間開始前の価格を比較して下落率を計算
    if len(df) < 2:
        return ""

    current_close = df["Close"].iloc[-1]

    # 実施開始日前の最高値 or 決算直後の価格(直近高値)を基準にする
    # 直近20日の高値を基準とする
    lookback = min(20, len(df))
    ref_high = df["High"].iloc[-lookback:].max()

    if ref_high > 0:
        drop_pct = (ref_high - current_close) / ref_high * 100
    else:
        return ""

    # 実施期間中
    if today >= start_date:
        if drop_pct >= buyback_pct:
            return f"[底値スイング]下落{drop_pct:.1f}%>={buyback_pct}%"
        else:
            return f"[自社株買い実施中]下落{drop_pct:.1f}%/{buyback_pct}%"

    # 実施期間前: 下落率が既に達している場合は開始日から有効
    else:
        if drop_pct >= buyback_pct:
            return f"[{start_date}から底値SW]下落{drop_pct:.1f}%"
        else:
            remaining = buyback_pct - drop_pct
            return f"[実施待ち:{start_date}]あと{remaining:.1f}%下落で底値"


# ---------- 決算日フラグ ----------

def check_settlement_alert(next_settlement) -> str:
    """次回決算予定日までの日数でフラグを生成。

    今日学んだ教訓：
    - 場中決算は荒い値動き(急騰→急落)を引き起こす
    - 決算日3日前から大口の買い集め(BOXパターン)が始まる可能性がある
    - 決算フラグがあれば前場のBOXパターンに注目する

    Returns:
        "🔴決算当日" / "🟠決算3日以内" / "🟡決算7日以内" / ""
    """
    if next_settlement is None or pd.isna(next_settlement):
        return ""

    today = date.today()
    try:
        settlement_date = pd.Timestamp(next_settlement).date()
    except Exception:
        return ""

    diff = (settlement_date - today).days

    if diff == 0:
        return "🔴決算当日"
    elif 1 <= diff <= 3:
        return "🟠決算3日以内"
    elif 4 <= diff <= 7:
        return "🟡決算7日以内"
    else:
        return ""


# ---------- セクターボーナス ----------

def sector_bonus(sector: str, memo: str = "") -> tuple[int, str]:
    """重要セクター加点(最大10点)。"""
    text = f"{sector} {memo}".lower()
    hits = [kw for kw in IMPORTANT_SECTOR_KEYWORDS if kw.lower() in text]
    if not hits:
        return 0, ""
    # 最大10点(キーワード1つで5点、複数で10点)
    score = min(10, 5 * len(hits))
    return score, "/".join(hits)


# ---------- 主パターン判定 ----------

def determine_main_pattern(s: StockScore) -> str:
    scores = {
        "下駄": s.geta,
        "出来高急増": s.volume,
        "トレンド強": s.trend,
        "アイランド": s.island,
    }
    top = max(scores, key=scores.get)
    return top if scores[top] >= 12 else "なし"


# ---------- コメント生成 ----------

def generate_comment(s: StockScore) -> str:
    parts: list[str] = []

    if "GU" in s.island_note:
        parts.append("翌日続き足候補")
    if "寄引同値" in s.geta_note:
        parts.append("高確率(80%)")
    if "5日平均2.0倍" in s.volume_note or "5日平均3" in s.volume_note:
        parts.append("出来高急増")
    if "出来高だまり" in s.volume_note:
        parts.append("出来高だまり形成")
    if "MA5/25/75↑" in s.trend_note:
        parts.append("強トレンド")
    if "高値圏" in s.margin_note:
        parts.append("⚠️高値圏で買残注意")
    if s.total >= 70:
        parts.append("AIスコア注目")

    return " / ".join(parts) if parts else "-"


# ---------- 1銘柄スコアリング ----------

def score_stock(
    code: str,
    df: pd.DataFrame,
    name: str = "",
    sector: str = "",
    memo: str = "",
    margin_data: dict | None = None,
    next_settlement=None,
    buyback_pct: float | None = None,
    buyback_start=None,
    buyback_end=None,
    buyback_method: str = "",
) -> StockScore:
    """1銘柄を5項目+セクター+BB位置+決算フラグ+自社株買いでスコアリングする。"""
    s = StockScore(code=code, name=name, sector=sector)

    if df is None or df.empty:
        s.comment = "データなし"
        return s

    s.geta, s.geta_note = score_geta(df)
    s.volume, s.volume_note = score_volume(df)
    s.trend, s.trend_note = score_trend_753(df)
    s.margin, s.margin_note = score_margin(df, margin_data)
    s.island, s.island_note = score_island(df)
    s.sector_bonus, sector_kw = sector_bonus(sector, memo)
    if sector_kw:
        s.sector += f" [+{sector_kw}]"

    # ボリンジャーバンド位置判定
    s.bb_position = score_bollinger_position(df)

    # 決算日フラグ
    s.settlement_alert = check_settlement_alert(next_settlement)

    # 自社株買いフラグ
    s.buyback_alert = check_buyback_alert(
        df, buyback_pct, buyback_start, buyback_end, buyback_method
    )

    s.main_pattern = determine_main_pattern(s)
    s.comment = generate_comment(s)
    return s


# ---------- 複数銘柄スコアリング ----------

def score_all(
    quotes: dict[str, pd.DataFrame],
    watchlist: pd.DataFrame,
    margin_data: dict[str, dict] | None = None,
) -> list[StockScore]:
    """全銘柄をスコアリングして StockScore のリストを返す(降順ソート)。"""
    margin_data = margin_data or {}
    info_map = {
        row["code"]: row for _, row in watchlist.iterrows()
    }

    results: list[StockScore] = []
    for code, df in quotes.items():
        info = info_map.get(code, {})
        s = score_stock(
            code=code,
            df=df,
            name=info.get("name", ""),
            sector=info.get("sector", ""),
            memo=info.get("memo", ""),
            margin_data=margin_data.get(code),
            next_settlement=info.get("next_settlement"),
            buyback_pct=info.get("buyback_pct"),
            buyback_start=info.get("buyback_start"),
            buyback_end=info.get("buyback_end"),
            buyback_method=info.get("buyback_method", ""),
        )
        # らいおんまる順位を引き継ぐ(数値化済み or NaN)
        lion = info.get("lion_rank")
        if lion is not None and pd.notna(lion):
            try:
                s.lion_rank = int(lion)
            except (ValueError, TypeError):
                s.lion_rank = None
        results.append(s)

    results.sort(key=lambda x: x.total, reverse=True)
    return results


# ---------- 動作確認 ----------

def _smoke_test() -> None:
    print("=" * 60)
    print("スコアリング 動作確認")
    print("=" * 60)

    from .data_fetcher import DataFetcher
    from .watchlist import load_watchlist

    watchlist = load_watchlist()
    codes = watchlist["code"].tolist()

    fetcher = DataFetcher()
    print(f"対象 {len(codes)} 銘柄の日足取得中...")
    quotes = fetcher.fetch_multi(codes, days=120, sleep_sec=0.2, verbose=True)
    print("取得完了\n")

    # デバッグ: 1銘柄目の中身を覗く
    first_code = codes[0] if codes else None
    if first_code and not quotes.get(first_code, pd.DataFrame()).empty:
        print(f"--- DEBUG: {first_code} 列名 ---")
        print(quotes[first_code].columns.tolist())
        print(f"--- DEBUG: {first_code} 直近1行 ---")
        print(quotes[first_code].tail(1).to_string())
        print()
    elif first_code:
        print(f"⚠️ {first_code} のデータが空です。レスポンス確認:")
        # 生レスポンス確認のため client を直接叩く
        from datetime import date, timedelta
        today = date.today()
        from_d = (today - timedelta(days=120)).strftime("%Y%m%d")
        to_d = today.strftime("%Y%m%d")
        raw = fetcher.client.get_daily_quotes(
            code=first_code, from_date=from_d, to_date=to_d
        )
        print(f"生レスポンス: {raw}")
        print()

    print("スコアリング中...")
    results = score_all(quotes, watchlist)
    print()

    # ランキング表示(簡易版、本格的な表示は Step 10 で rich を使う)
    print(f"{'順':>3} {'コード':<6} {'銘柄名':<20} {'合計':>4} "
          f"{'下駄':>4} {'出来高':>5} {'トレンド':>6} {'信用':>4} {'パターン':>5} {'セクター加点':>5}  主パターン  コメント")
    print("-" * 130)
    for i, s in enumerate(results, 1):
        print(f"{i:>3} {s.code:<6} {s.name[:18]:<20} {s.total:>4} "
              f"{s.geta:>4} {s.volume:>5} {s.trend:>6} {s.margin:>4} "
              f"{s.island:>5} {s.sector_bonus:>5}  {s.main_pattern:<8} {s.comment}")

    print("=" * 60)


if __name__ == "__main__":
    _smoke_test()
