"""
銘柄リスト読込モジュール

data/watchlist.csv (code, name, sector, memo) を pandas DataFrame として読む。
将来エクセル(.xlsx)やDBに切り替えやすいようにここに分離。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WATCHLIST = PROJECT_ROOT / "data" / "watchlist.csv"


def load_watchlist(csv_path: str | Path | None = None) -> pd.DataFrame:
    """銘柄リスト CSV を読み込む。

    必須列: code(銘柄コード)
    任意列: name, sector, memo

    Args:
        csv_path: CSVのパス。省略時は data/watchlist.csv

    Returns:
        DataFrame(code, name, sector, memo の列を持つ)
    """
    path = Path(csv_path) if csv_path else DEFAULT_WATCHLIST
    if not path.exists():
        raise FileNotFoundError(f"銘柄リストが見つかりません: {path}")

    df = pd.read_csv(path, dtype={"code": str})

    if "code" not in df.columns:
        raise ValueError(
            f"watchlist.csv に 'code' 列が必要です: 現在の列={df.columns.tolist()}"
        )

    # 整形: 前後の空白除去、空行とダミー行(0000)を除外
    df["code"] = df["code"].astype(str).str.strip()
    df = df[df["code"].notna() & (df["code"] != "") & (df["code"] != "0000")]
    df = df.reset_index(drop=True)

    # 任意列の補完
    for col in ("name", "sector", "memo"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")

    # lion_rank 列(らいおんまる順位)を任意列として保持
    if "lion_rank" in df.columns:
        df["lion_rank"] = pd.to_numeric(df["lion_rank"], errors="coerce")

    # settlement_month: 決算月(3/6/9/12)
    if "settlement_month" not in df.columns:
        df["settlement_month"] = None
    df["settlement_month"] = pd.to_numeric(df["settlement_month"], errors="coerce")

    # next_settlement: 次回決算予定日(YYYY-MM-DD)、空欄OK
    if "next_settlement" not in df.columns:
        df["next_settlement"] = None
    df["next_settlement"] = pd.to_datetime(df["next_settlement"], errors="coerce")

    # 自社株買い情報
    for col in ("buyback_pct", "buyback_start", "buyback_end", "buyback_method"):
        if col not in df.columns:
            df[col] = None

    df["buyback_pct"] = pd.to_numeric(df["buyback_pct"], errors="coerce")
    df["buyback_start"] = pd.to_datetime(df["buyback_start"], errors="coerce")
    df["buyback_end"] = pd.to_datetime(df["buyback_end"], errors="coerce")
    df["buyback_method"] = df["buyback_method"].fillna("")

    cols = ["code", "name", "sector", "memo"]
    if "lion_rank" in df.columns:
        cols.append("lion_rank")
    cols += [
        "settlement_month", "next_settlement",
        "buyback_pct", "buyback_start", "buyback_end", "buyback_method",
    ]

    return df[cols]


# ---------- 動作確認 ----------

def _smoke_test() -> None:
    print("=" * 60)
    print("銘柄リスト読込テスト")
    print("=" * 60)
    df = load_watchlist()
    print(f"読込銘柄数: {len(df)}")
    print()
    print(df.to_string(index=False))
    print("=" * 60)


if __name__ == "__main__":
    _smoke_test()
