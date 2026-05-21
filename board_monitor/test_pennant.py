"""
ペナントブレイク検知 単体テスト

UIを起動して3パターンのダミーローソク足を送り込み、
AlertPopup が正しく発火するか確認します。

実行:
    python -m board_monitor.test_pennant
"""
import tkinter as tk
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from board_monitor.monitors.pennant_detector import PennantDetector
from board_monitor.monitors.alert_popup import AlertPopup


def make_candles_ascending_triangle(n: int = 20) -> list:
    """① 上昇三角形ダミーローソク足
    上値: ほぼフラット（9,990 → 10,000 ±小）
    下値: 急に切り上がり（9,700 → 9,980）
    """
    candles = []
    base_high = 9990.0
    base_low  = 9700.0
    high_step = 0.5    # ほぼフラット（わずかに上昇）
    low_step  = 14.0   # 急に切り上がり

    for i in range(n):
        h = base_high + high_step * i
        l = base_low  + low_step  * i
        mid = (h + l) / 2
        candles.append({
            "open":   mid - 5,
            "high":   h,
            "low":    l,
            "close":  mid + 5,
            "volume": 100000,
        })
    return candles


def make_candles_ascending_wedge(n: int = 45) -> list:
    """③ 上昇ウェッジ（スクエニ型）ダミーローソク足
    上値: 緩やかに切り上がり（slope > 0 だが小）
    下値: 急に切り上がり（slope が大）
    共通条件 h_slope < l_slope を満たす
    """
    candles = []
    base_high = 2700.0
    base_low  = 2550.0
    high_step = 1.0    # 緩やかに上昇
    low_step  = 5.0    # 急に上昇（ウェッジで収束）

    for i in range(n):
        h = base_high + high_step * i
        l = base_low  + low_step  * i
        mid = (h + l) / 2
        candles.append({
            "open":   mid - 2,
            "high":   h,
            "low":    l,
            "close":  mid + 2,
            "volume": 80000,
        })
    return candles


def make_candles_symmetric_pennant(n: int = 25) -> list:
    """② 対称ペナントダミーローソク足
    上値: 切り下がり（slope < 0）
    下値: 切り上がり（slope > 0）
    """
    candles = []
    base_high = 5100.0
    base_low  = 4900.0
    high_step = -3.0   # 切り下がり
    low_step  = 3.0    # 切り上がり

    for i in range(n):
        h = base_high + high_step * i
        l = base_low  + low_step  * i
        mid = (h + l) / 2
        candles.append({
            "open":   mid - 3,
            "high":   h,
            "low":    l,
            "close":  mid + 3,
            "volume": 60000,
        })
    return candles


def run_test():
    """3パターンをPennantDetectorで検知テスト"""
    detector = PennantDetector(
        max_candles  = 50,
        r2_threshold = 0.25,
        width_shrink = 0.35,
    )

    tests = [
        ("① 上昇三角形", "9984",  make_candles_ascending_triangle(),  10010.0),
        ("② 対称ペナント", "7011", make_candles_symmetric_pennant(),    5035.0),
        ("③ 上昇ウェッジ", "9684", make_candles_ascending_wedge(),      2750.0),
    ]

    print("=" * 60)
    print("PennantDetector 単体テスト")
    print("=" * 60)

    root = tk.Tk()
    root.title("ペナント検知テスト")
    root.configure(bg="black")
    root.geometry("400x300")

    popup = AlertPopup(root)

    results = []
    for name, code, candles, breakout_price in tests:
        result = detector.detect(candles, breakout_price)
        status = "✅ 検知成功" if result else "❌ 検知なし"
        results.append((name, status, result))
        print(f"{name}: {status}")
        if result:
            print(f"  high_slope={result['high_slope']:.3f}  "
                  f"low_slope={result['low_slope']:.3f}  "
                  f"resist={result['resist_price']:.1f}  "
                  f"R²(H={result['r2_high']:.2f}/L={result['r2_low']:.2f})  "
                  f"収束率={result['width_ratio']:.0%}")

    print("=" * 60)

    # 結果をラベル表示
    for i, (name, status, result) in enumerate(results):
        color = "#00ff00" if "✅" in status else "#ff4444"
        tk.Label(root, text=f"{name}: {status}",
                 bg="black", fg=color,
                 font=("Courier", 12, "bold")).pack(pady=5)

    # 成功したものはアラートポップアップも出す
    def show_alerts():
        for name, status, result in results:
            if result:
                popup.show(
                    symbol      = name[:6],
                    symbol_name = name,
                    price       = result["resist_price"] + 10,
                    pattern     = result["pattern"],
                    detail      = f"R²(H={result['r2_high']:.2f}/L={result['r2_low']:.2f})  収束率={result['width_ratio']:.0%}",
                )

    root.after(1000, show_alerts)
    root.mainloop()


if __name__ == "__main__":
    run_test()
