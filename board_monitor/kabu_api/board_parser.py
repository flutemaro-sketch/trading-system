"""
kabuStation API の板データを内部形式に変換するパーサ

kabuStation の WebSocket / PushAPI が送ってくる板スナップショットを
BoardPanel が消費できる辞書形式に整形する。

kabuStation のフィールド定義 (PUSH/BoardResponse):
  Symbol, SymbolName, CurrentPrice, PreviousClose,
  ChangePreviousClose, ChangePreviousClosePer,
  OpeningPrice, HighPrice, LowPrice,
  TradingVolume, VWAP,
  Sell1..Sell10 = {Price, Qty, Sign},
  Buy1..Buy10  = {Price, Qty, Sign},
  CurrentPriceTime, ...
"""
from datetime import datetime
from typing import Optional


def _detect_price_status(raw: dict) -> str:
    """特別気配・連続気配のステータスを判定して返す。

    Sign コード:
      0102 → 特別気配（Sell側ならば特買い / Buy側ならば特売り）
      0119 → 連続比例配分（買）= 連買い
      0120 → 連続比例配分（売）= 連売り
    """
    # 連続 を先にチェック（優先度高）
    for i in range(1, 11):
        for key in [f"Sell{i}", f"Buy{i}"]:
            q = raw.get(key) or {}
            sign = str(q.get("Sign", ""))
            if sign == "0119":
                return "連買い"
            if sign == "0120":
                return "連売り"

    # 特別気配チェック
    # Buy1 が特別 → 買いが積み上がっている → 特別買い気配
    buy1 = raw.get("Buy1") or {}
    if str(buy1.get("Sign", "")) == "0102":
        return "特買い"

    # Sell1 が特別 → 売りが積み上がっている → 特別売り気配
    sell1 = raw.get("Sell1") or {}
    if str(sell1.get("Sign", "")) == "0102":
        return "特売り"

    return ""


def _normalize_sign(sign: str) -> str:
    """kabuStation の Sign フィールドを表示用に正規化。

    Args:
        sign: kabuStation の Sign フィールド値

    Returns:
        表示用の文字列（成行, OVER, UNDER, または ""）
    """
    if not sign:
        return ""

    # kabuStation の Sign 値の可能性
    # "SignoverSelling" → "OVER"
    # "SignUnderBuying" → "UNDER"
    # "Negotiated" → "成行"
    # "" or None → ""

    sign_str = str(sign)
    sign_lower = sign_str.lower()

    if "over" in sign_lower:
        return "OVER"
    elif "under" in sign_lower:
        return "UNDER"
    elif "negotiated" in sign_lower or sign_lower == "成行":
        return "成行"
    elif sign_str == "0102":
        return "特"
    elif sign_str in ("0119", "0120"):
        return "連"
    else:
        return ""


def _parse_quote(quote: Optional[dict]) -> Optional[dict]:
    """Sell1/Buy1 等のオブジェクトを {"price", "volume"} に整形。
    特別気配で Price が None のことがあるので除外する。"""
    if not quote:
        return None
    price = quote.get("Price")
    qty = quote.get("Qty", 0)
    if price is None or price == 0:
        return None
    return {"price": float(price), "volume": int(qty or 0)}


def parse_kabu_board(raw: dict) -> Optional[dict]:
    """kabuStation 板スナップショットを内部形式へ変換。

    Args:
        raw: kabuStation の Board レスポンス（JSONをdict化済み）

    Returns:
        BoardPanel.update_data() に渡せる dict、または None（パース不可時）
    """
    if not raw:
        return None

    symbol = raw.get("Symbol")
    if not symbol:
        return None

    def _parse_time(ts: str, fmt: str = "%H:%M:%S") -> str:
        """ISO8601文字列 → 時刻文字列。失敗時は空文字を返す"""
        if not ts:
            return ""
        try:
            return datetime.fromisoformat(
                ts.replace("Z", "+00:00")
            ).strftime(fmt)
        except (ValueError, AttributeError):
            return ""

    def _dedup_quotes(raw_list: list) -> tuple:
        """同一価格のエントリを合算して (quotes, signs) を返す。
        kabuStation が Sell1..Sell10 に同価格を複数送ることへの対処。
        """
        seen: dict = {}   # price -> index in result
        quotes: list = []
        signs: list  = []
        for price, vol, sign in raw_list:
            if price in seen:
                quotes[seen[price]]["volume"] += vol
            else:
                seen[price] = len(quotes)
                quotes.append({"price": price, "volume": vol})
                signs.append(sign)
        return quotes, signs

    # 売り気配（Sell1 が最良 = 最安値）
    asks_raw = []
    for i in range(1, 11):
        q = raw.get(f"Sell{i}") or {}
        price = q.get("Price")
        qty   = q.get("Qty", 0)
        sign  = _normalize_sign(str(q.get("Sign", "")))
        if price and float(price) > 0:
            asks_raw.append((float(price), int(qty or 0), sign))
    asks, asks_sign = _dedup_quotes(asks_raw)

    # 買い気配（Buy1 が最良 = 最高値）
    bids_raw = []
    for i in range(1, 11):
        q = raw.get(f"Buy{i}") or {}
        price = q.get("Price")
        qty   = q.get("Qty", 0)
        sign  = _normalize_sign(str(q.get("Sign", "")))
        if price and float(price) > 0:
            bids_raw.append((float(price), int(qty or 0), sign))
    bids, bids_sign = _dedup_quotes(bids_raw)

    # 騰落率（kabuStation が ChangePreviousClosePer を返す場合はそれを優先）
    change_pct = raw.get("ChangePreviousClosePer")
    if change_pct is None:
        prev_close = raw.get("PreviousClose")
        cur = raw.get("CurrentPrice")
        if prev_close and cur:
            change_pct = (cur - prev_close) / prev_close * 100.0
        else:
            change_pct = 0.0

    # 現在値時刻
    ts_str = raw.get("CurrentPriceTime") or raw.get("TradingVolumeTime")
    time_label = _parse_time(ts_str) or "--:--:--"

    # 始値・高値・安値の時刻
    time_open = _parse_time(raw.get("OpeningPriceTime"),  "%H:%M")
    time_high = _parse_time(raw.get("HighPriceTime"),     "%H:%M")
    time_low  = _parse_time(raw.get("LowPriceTime"),      "%H:%M")

    # 現在値: CurrentPrice が 0 または None の場合は均衡価格(CalcPrice)を使用
    current_price = raw.get("CurrentPrice")
    if not current_price:
        current_price = raw.get("CalcPrice") or 0
    is_calc = bool(raw.get("CalcPrice") and not raw.get("CurrentPrice"))

    # 特別気配・連続気配の判定
    price_status = _detect_price_status(raw)

    return {
        "symbol": symbol,
        "symbol_name": raw.get("SymbolName", ""),   # 銘柄名
        "is_calc_price": is_calc,                   # True=均衡価格
        "price_status": price_status,               # 特買い/特売り/連買い/連売り/""
        "time": time_label,
        "last_price": float(current_price),
        "change_pct": float(change_pct or 0),
        "previous_close": float(raw.get("PreviousClose") or 0),
        "open": float(raw.get("OpeningPrice") or 0),
        "high": float(raw.get("HighPrice") or 0),
        "low": float(raw.get("LowPrice") or 0),
        "volume": int(raw.get("TradingVolume") or 0),
        "vwap": float(raw.get("VWAP") or 0),
        "time_open": time_open,
        "time_high": time_high,
        "time_low":  time_low,
        "asks": asks,
        "asks_sign": asks_sign,
        "bids": bids,
        "bids_sign": bids_sign,
    }
