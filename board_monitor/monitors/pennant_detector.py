"""
ペナントブレイク検知エンジン（上方向）

ペナントとは：
  価格が三角収束（高値切り下がり + 安値切り上がり）を形成した後、
  上側にブレイクアウトするパターン。

判定アルゴリズム:
  1. 直近 min_candles〜max_candles 本のローソク足を使用
  2. 高値ライン: 線形回帰の傾き < 0（切り下がり）かつ R² > 閾値
  3. 安値ライン: 線形回帰の傾き > 0（切り上がり）かつ R² > 閾値
  4. 収束確認: 末尾のスプレッド幅が先頭より縮小している
  5. ブレイク: 現在値 > 高値トレンドラインの延長線

依存: numpy（pip install numpy）
"""
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False
    logger.warning("numpy 未インストール。ペナント検知は無効です。 pip install numpy")


class PennantDetector:
    """ペナントブレイク（上方向）を検知する"""

    def __init__(
        self,
        min_candles:  int   = 8,    # 最低使用本数
        max_candles:  int   = 25,   # 最大使用本数
        r2_threshold: float = 0.35, # 線形性の閾値（低めに設定・緩め）
        width_shrink: float = 0.15, # 収束率：末尾幅 ≦ 先頭幅 × (1 - この値)
    ):
        self.min_candles  = min_candles
        self.max_candles  = max_candles
        self.r2_threshold = r2_threshold
        self.width_shrink = width_shrink

    def detect(self, candles: List[dict],
               current_price: float) -> Optional[dict]:
        """ペナントブレイクを判定する。

        Args:
            candles       : 確定済みローソク足リスト（古い順）
            current_price : 現在の価格（未確定足の終値）

        Returns:
            検知時: {
                "pattern":      "pennant_break_up",
                "candle_count": int,
                "high_slope":   float,   # 高値ラインの傾き（負）
                "low_slope":    float,   # 安値ラインの傾き（正）
                "resist_price": float,   # 高値ラインの現在延長値
                "r2_high":      float,
                "r2_low":       float,
                "width_ratio":  float,   # 収束率（末尾/先頭 の幅比）
            }
            未検知: None
        """
        if not _HAS_NUMPY:
            return None
        if not current_price or current_price <= 0:
            return None

        # 使用本数を制限
        used = candles[-self.max_candles:]
        n = len(used)
        if n < self.min_candles:
            return None

        highs = np.array([c["high"] for c in used], dtype=float)
        lows  = np.array([c["low"]  for c in used], dtype=float)
        x     = np.arange(n, dtype=float)

        # ── 線形回帰
        h_slope, h_inter, h_r2 = self._linreg(x, highs)
        l_slope, l_inter, l_r2 = self._linreg(x, lows)

        # ── 条件1: 傾きの方向
        if h_slope >= 0:
            return None  # 高値が切り下がっていない
        if l_slope <= 0:
            return None  # 安値が切り上がっていない

        # ── 条件2: 線形性（R²）
        if h_r2 < self.r2_threshold or l_r2 < self.r2_threshold:
            return None

        # ── 条件3: 収束確認
        width_first = (h_inter) - (l_inter)                          # x=0 での幅
        width_last  = (h_slope * (n-1) + h_inter) - \
                      (l_slope * (n-1) + l_inter)                    # x=n-1 での幅
        if width_first <= 0:
            return None
        width_ratio = width_last / width_first
        if width_ratio > (1.0 - self.width_shrink):
            return None  # 収束が足りない

        # ── 条件4: ブレイクアウト確認
        # 高値ラインを x=n（次の足）に延長した抵抗ライン
        resist_price = h_slope * n + h_inter

        if current_price <= resist_price:
            return None  # まだブレイクしていない

        logger.info(
            f"[ペナントブレイク] {n}本 "
            f"high_slope={h_slope:.2f} low_slope={l_slope:.2f} "
            f"resist={resist_price:.1f} current={current_price:.1f} "
            f"R²(H={h_r2:.2f}/L={l_r2:.2f}) 収束率={width_ratio:.2f}"
        )

        return {
            "pattern":      "pennant_break_up",
            "candle_count": n,
            "high_slope":   float(h_slope),
            "low_slope":    float(l_slope),
            "resist_price": float(resist_price),
            "r2_high":      float(h_r2),
            "r2_low":       float(l_r2),
            "width_ratio":  float(width_ratio),
        }

    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _linreg(x: "np.ndarray",
                y: "np.ndarray") -> Tuple[float, float, float]:
        """最小二乗線形回帰 → (slope, intercept, R²)"""
        import numpy as np
        slope, intercept = np.polyfit(x, y, 1)
        y_pred = slope * x + intercept
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
        r2     = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0
        return float(slope), float(intercept), float(r2)
