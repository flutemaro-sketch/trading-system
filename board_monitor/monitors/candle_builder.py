"""
分足組み立てエンジン（CandleBuilder）

WebSocketで受け取る現在値ティックから任意の時間足OHLCVを自動生成する。

使い方:
    builder = CandleBuilder(interval_minutes=5)
    completed = builder.update(symbol, price, volume, timestamp)
    if completed:
        # 5分足1本が確定した
        candles = builder.get_candles(symbol, count=20)
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CandleBuilder:
    """ティックデータからN分足OHLCVを組み立てる"""

    def __init__(self, interval_minutes: int = 5, max_candles: int = 60):
        """
        Args:
            interval_minutes : 時間足の間隔（分）デフォルト5分
            max_candles      : 銘柄ごとに保持する最大ローソク足本数
        """
        self.interval_min = interval_minutes
        self.interval_sec = interval_minutes * 60
        self.max_candles  = max_candles

        # symbol → 確定済みcandle リスト（古い順）
        self._candles:  Dict[str, List[dict]] = {}
        # symbol → 構築中のcandle（未確定）
        self._current:  Dict[str, Optional[dict]] = {}

    # ─────────────────────────────────────────────────────────
    #  公開 API
    # ─────────────────────────────────────────────────────────

    def update(self, symbol: str, price: float, volume: int,
               timestamp: datetime) -> Optional[dict]:
        """ティックを受け取り、足が確定したらその足を返す。

        Args:
            symbol    : 銘柄コード（例: "6920"）
            price     : 現在値
            volume    : 累積出来高（増分ではなく累積値）
            timestamp : ティックの時刻

        Returns:
            確定した candle dict（新しい足が始まったとき）、または None
        """
        if not price or price <= 0:
            return None

        bar_start = self._bar_start(timestamp)
        cur = self._current.get(symbol)

        if cur is None:
            # 初回受信
            self._current[symbol] = self._new_candle(
                symbol, price, volume, bar_start)
            return None

        if bar_start > cur["ts_open"]:
            # 足が変わった → 前の足を確定
            completed = {k: v for k, v in cur.items()
                         if not k.startswith("_")}
            completed["ts_close"] = timestamp
            self._push(symbol, completed)

            # 新しい足を開始
            self._current[symbol] = self._new_candle(
                symbol, price, volume, bar_start)
            logger.debug(f"[{symbol}] {self.interval_min}分足確定: "
                         f"O={completed['open']} H={completed['high']} "
                         f"L={completed['low']}  C={completed['close']} "
                         f"V={completed['volume']}")
            return completed

        # 同じ足の中でティック更新
        cur["high"]  = max(cur["high"], price)
        cur["low"]   = min(cur["low"],  price)
        cur["close"] = price
        # 出来高 = 累積値 - 足開始時の累積値
        if volume >= cur["_vol_start"]:
            cur["volume"] = volume - cur["_vol_start"]
        return None

    def get_candles(self, symbol: str, count: int = 20) -> List[dict]:
        """直近 count 本の確定済みローソク足を返す（古い順）"""
        return self._candles.get(symbol, [])[-count:]

    def get_current(self, symbol: str) -> Optional[dict]:
        """現在構築中（未確定）のローソク足を返す"""
        return self._current.get(symbol)

    def candle_count(self, symbol: str) -> int:
        """確定済み足の本数"""
        return len(self._candles.get(symbol, []))

    # ─────────────────────────────────────────────────────────
    #  内部ヘルパー
    # ─────────────────────────────────────────────────────────

    def _bar_start(self, ts: datetime) -> datetime:
        """タイムスタンプが属するバーの開始時刻を返す（9:00 基準）"""
        base = ts.replace(hour=9, minute=0, second=0, microsecond=0)
        elapsed = int((ts - base).total_seconds())
        if elapsed < 0:
            elapsed = 0
        bars = elapsed // self.interval_sec
        return base + timedelta(seconds=bars * self.interval_sec)

    @staticmethod
    def _new_candle(symbol: str, price: float, volume: int,
                    ts_open: datetime) -> dict:
        return {
            "symbol":     symbol,
            "open":       price,
            "high":       price,
            "low":        price,
            "close":      price,
            "volume":     0,
            "ts_open":    ts_open,
            "ts_close":   None,
            "_vol_start": volume,  # 内部用：足開始時の累積出来高
        }

    def _push(self, symbol: str, candle: dict):
        """確定足をリストに追加し max_candles を超えたら古いものを削除"""
        lst = self._candles.setdefault(symbol, [])
        lst.append(candle)
        if len(lst) > self.max_candles:
            del lst[0]
