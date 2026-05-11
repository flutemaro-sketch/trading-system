"""
データ取得抽象化レイヤー

複数銘柄の日足を一括取得する。
将来 kabuStation など別データソースに差し替え可能なよう、
JQuantsClient への依存をこのレイヤーに閉じ込める。
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

from .jquants_client import JQuantsAPIError, JQuantsClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "quotes_cache"


def _bars_to_dataframe(response: dict | list) -> pd.DataFrame:
    """J-Quants v2 の日足レスポンスを標準カラムの DataFrame 化する。

    v2 は短縮列名(O/H/L/C/Vo, AdjO/.../AdjVo)を使うため、
    ここで Open/High/Low/Close/Volume などに正規化する。
    """
    # bars リストを取り出す(複数の構造に対応)
    if isinstance(response, list):
        bars = response
    elif isinstance(response, dict):
        bars = (
            response.get("daily_quotes")
            or response.get("bars")
            or response.get("data")
            or response.get("equities", {}).get("bars")
            or response.get("equities", {}).get("daily_quotes")
        )
        if not bars:
            # 最後の手段: トップレベルで最初の list[dict] を探す
            for v in response.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    bars = v
                    break
            else:
                bars = []
    else:
        bars = []

    df = pd.DataFrame(bars)
    if df.empty:
        return df

    # v2 の短縮カラムを標準名にリネーム
    rename_map = {
        "O": "Open",
        "H": "High",
        "L": "Low",
        "C": "Close",
        "Vo": "Volume",
        "Va": "TurnoverValue",
        "UL": "UpperLimit",
        "LL": "LowerLimit",
        "AdjO": "AdjustmentOpen",
        "AdjH": "AdjustmentHigh",
        "AdjL": "AdjustmentLow",
        "AdjC": "AdjustmentClose",
        "AdjVo": "AdjustmentVolume",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Date 列を日付型にしてソート
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date").reset_index(drop=True)

    return df


class DataFetcher:
    """データ取得レイヤー。

    日足データを取得して銘柄ごとの DataFrame を返す。
    取得は J-Quants API。将来 kabuStation など差し替えるならここを継承する。
    """

    def __init__(self, client: JQuantsClient | None = None) -> None:
        self.client = client or JQuantsClient()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- 単一銘柄 ----------

    def fetch_daily_bars(
        self,
        code: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> pd.DataFrame:
        """1銘柄の日足を取得して DataFrame で返す。

        Args:
            code: 銘柄コード(例 "7203")
            from_date: YYYYMMDD
            to_date: YYYYMMDD
        """
        resp = self.client.get_daily_quotes(
            code=code, from_date=from_date, to_date=to_date
        )
        return _bars_to_dataframe(resp)

    # ---------- 複数銘柄 ----------

    def fetch_multi(
        self,
        codes: Iterable[str],
        days: int = 120,
        sleep_sec: float = 0.2,
        verbose: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """複数銘柄の日足を一括取得。

        Args:
            codes: 銘柄コードのリスト
            days: 過去何日分を取得するか(デフォルト120日 = 75日線+α)
            sleep_sec: API 連続呼出時のスリープ(レート制限対策)
            verbose: 進捗表示

        Returns:
            銘柄コード → DataFrame の辞書
        """
        today = date.today()
        from_date = (today - timedelta(days=days)).strftime("%Y%m%d")
        to_date = today.strftime("%Y%m%d")

        codes_list = list(codes)
        results: dict[str, pd.DataFrame] = {}
        n = len(codes_list)

        for i, code in enumerate(codes_list, 1):
            if verbose:
                print(f"  [{i:>3}/{n}] {code} 取得中...", end=" ")
            try:
                df = self.fetch_daily_bars(
                    code=code, from_date=from_date, to_date=to_date
                )
                results[code] = df
                if verbose:
                    print(f"OK ({len(df)} 行)")
            except JQuantsAPIError as e:
                if verbose:
                    print(f"NG: {e}")
                results[code] = pd.DataFrame()
            time.sleep(sleep_sec)

        return results

    # ---------- キャッシュ ----------

    def save_cache(
        self, results: dict[str, pd.DataFrame], tag: str | None = None
    ) -> Path:
        """取得結果を CSV として data/quotes_cache/ に保存。

        Args:
            results: fetch_multi の戻り値
            tag: ファイル名に付けるタグ(省略時は今日の日付)

        Returns:
            保存ディレクトリのパス
        """
        tag = tag or date.today().strftime("%Y%m%d")
        save_dir = CACHE_DIR / tag
        save_dir.mkdir(parents=True, exist_ok=True)

        for code, df in results.items():
            if df.empty:
                continue
            df.to_csv(save_dir / f"{code}.csv", index=False, encoding="utf-8-sig")

        return save_dir


# ---------- 動作確認 ----------


def _smoke_test() -> None:
    print("=" * 60)
    print("データ取得レイヤー 動作確認")
    print("=" * 60)

    from .watchlist import load_watchlist

    watchlist = load_watchlist()
    codes = watchlist["code"].tolist()
    print(f"対象銘柄: {len(codes)} 銘柄 → {codes}")
    print()

    fetcher = DataFetcher()
    print(f"日足取得開始(過去120日)...")
    results = fetcher.fetch_multi(codes, days=120, sleep_sec=0.2)
    print()

    # 集計
    success = sum(1 for df in results.values() if not df.empty)
    print(f"取得成功: {success}/{len(codes)} 銘柄")

    # サンプル表示
    sample_code = next(
        (c for c, df in results.items() if not df.empty), None
    )
    if sample_code:
        sample = results[sample_code].tail(5)
        print(f"\nサンプル({sample_code} 直近5日):")
        print(sample.to_string(index=False))

    # キャッシュ保存
    save_dir = fetcher.save_cache(results)
    print(f"\nキャッシュ保存先: {save_dir}")

    print("=" * 60)
    print("動作確認 完了")
    print("=" * 60)


if __name__ == "__main__":
    _smoke_test()
