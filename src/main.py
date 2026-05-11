"""
前日検討システム メインスクリプト

毎日大引け後にこれを1コマンド実行するだけで:
  1. 銘柄リストを読み込み
  2. 各銘柄の日足を J-Quants から取得
  3. 5項目スコアリング
  4. ランキング表示(rich)
  5. 結果を CSV に保存

使い方:
    python -m src.main           # 全銘柄、ランキング表示
    python -m src.main --top 10  # 上位10件のみ
    python -m src.main --detail 8035  # 8035 の詳細
    python -m src.main --no-fetch  # キャッシュから読込(API呼ばない)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Windows cp932 で Unicode 出力エラーを防ぐ
os.environ.setdefault("PYTHONUTF8", "1")

import pandas as pd
from rich.console import Console

from .consensus_fetcher import ConsensusFetcher
from .data_fetcher import DataFetcher
from .display import render_detail, render_ranking
from .scoring import StockScore, score_all
from .watchlist import load_watchlist

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_DIR = PROJECT_ROOT / "data" / "quotes_cache"


def _load_quotes_from_cache(codes: list[str], cache_tag: str | None = None) -> dict[str, pd.DataFrame]:
    """キャッシュから日足データを読込む。

    cache_tag: YYYYMMDD のフォルダ名。省略時は最新のフォルダを自動選択。
    """
    if cache_tag is None:
        # 最新のフォルダを探す
        candidates = [d for d in CACHE_DIR.iterdir() if d.is_dir()]
        if not candidates:
            raise FileNotFoundError(
                f"キャッシュが見つかりません: {CACHE_DIR}"
            )
        latest = max(candidates, key=lambda d: d.name)
        cache_tag = latest.name

    quotes: dict[str, pd.DataFrame] = {}
    cache_dir = CACHE_DIR / cache_tag
    for code in codes:
        path = cache_dir / f"{code}.csv"
        if path.exists():
            df = pd.read_csv(path, dtype={"Code": str})
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            quotes[code] = df
        else:
            quotes[code] = pd.DataFrame()
    return quotes


def _save_results_csv(results: list[StockScore]) -> Path:
    """ランキング結果を CSV として output/ に保存。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    path = OUTPUT_DIR / f"ranking_{today}.csv"

    rows = []
    for i, s in enumerate(results, 1):
        rows.append({
            "順位": i,
            "らいおん順位": s.lion_rank if s.lion_rank else "",
            "順位差": (s.lion_rank - i) if s.lion_rank else "",
            "コード": s.code,
            "銘柄名": s.name,
            "セクター": s.sector,
            "合計": s.total,
            "下駄": s.geta,
            "出来高": s.volume,
            "トレンド": s.trend,
            "信用": s.margin,
            "パターン": s.island,
            "セクター加点": s.sector_bonus,
            "主パターン": s.main_pattern,
            "BB位置": s.bb_position,
            "決算": s.settlement_alert,
            "自社株買い": s.buyback_alert,
            "コンセンサス": s.consensus_comparison,
            "コメント": s.comment,
            "下駄詳細": s.geta_note,
            "出来高詳細": s.volume_note,
            "トレンド詳細": s.trend_note,
            "信用詳細": s.margin_note,
            "パターン詳細": s.island_note,
        })

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="日本株 前日検討システム")
    parser.add_argument(
        "--top", type=int, default=None,
        help="上位N件のみ表示(省略時は全件)"
    )
    parser.add_argument(
        "--detail", type=str, default=None,
        help="指定コードの詳細を表示"
    )
    parser.add_argument(
        "--no-fetch", action="store_true",
        help="API呼出せずキャッシュから読込む"
    )
    parser.add_argument(
        "--days", type=int, default=120,
        help="過去何日分を取得するか(デフォルト120)"
    )
    args = parser.parse_args()

    console = Console()
    console.rule("[bold cyan]日本株 前日検討システム[/bold cyan]")

    # 1. 銘柄リスト読込
    watchlist = load_watchlist()
    codes = watchlist["code"].tolist()
    console.print(f"[green]○[/green] 銘柄リスト読込: {len(codes)} 銘柄")

    # 2. 日足データ取得
    if args.no_fetch:
        console.print("[yellow]→[/yellow] キャッシュから読込中...")
        quotes = _load_quotes_from_cache(codes)
    else:
        console.print(f"[yellow]→[/yellow] 日足データ取得中(過去{args.days}日)...")
        fetcher = DataFetcher()
        quotes = fetcher.fetch_multi(codes, days=args.days, sleep_sec=0.2, verbose=False)
        # キャッシュ保存
        save_dir = fetcher.save_cache(quotes)
        console.print(f"[green]○[/green] 取得完了 → キャッシュ: {save_dir}")

    success = sum(1 for df in quotes.values() if not df.empty)
    console.print(f"[green]○[/green] データ取得成功: {success}/{len(codes)} 銘柄")

    # 2.5 コンセンサスデータ取得(オプション)
    consensus_data = {}
    try:
        console.print("[yellow]→[/yellow] コンセンサスデータ取得中(IFIS)...")
        with ConsensusFetcher(headless=True) as fetcher:
            consensus_data = fetcher.fetch_multi(codes, verbose=False)
        console.print(f"[green]○[/green] コンセンサス取得成功: {len(consensus_data)}/{len(codes)} 銘柄")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] コンセンサス取得失敗: {e}")
        console.print("[dim]→ コンセンサス比較なしで続行します[/dim]")

    # 3. スコアリング
    console.print("[yellow]→[/yellow] スコアリング中...")
    results = score_all(quotes, watchlist)
    console.print(f"[green]○[/green] スコアリング完了")

    # 4. 表示
    if args.detail:
        target = next((s for s in results if s.code == args.detail), None)
        if target:
            render_detail(target)
        else:
            console.print(f"[red]×[/red] 銘柄 {args.detail} が見つかりません")
            return 1
    else:
        render_ranking(results, top_n=args.top)

    # 5. 結果CSV保存
    csv_path = _save_results_csv(results)
    console.print(f"[green]○[/green] 結果CSV保存: {csv_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
