"""
J-Quants API v2 クライアント

v2 (2025-12-22 以降) の正式仕様:
  - Base URL: https://api.jquants.com/v2
  - Auth   : x-api-key ヘッダーに APIキーをそのまま入れる
  - idToken は不要

使い方:
    from src.jquants_client import JQuantsClient
    client = JQuantsClient()
    quotes = client.get_daily_quotes(code="7203", date="20260430")
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


# プロジェクトルート(srcの一つ上)から .env を読む
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

JQUANTS_BASE_URL = "https://api.jquants.com/v2"


class JQuantsAuthError(Exception):
    """認証関連のエラー"""


class JQuantsAPIError(Exception):
    """API アクセス関連のエラー(認証以外)"""


class JQuantsClient:
    """J-Quants API v2 クライアント。

    APIキーを `x-api-key` ヘッダに付けて各エンドポイントを呼ぶ。
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("JQUANTSKEY")
        if not self.api_key:
            raise JQuantsAuthError(
                "JQUANTSKEY が見つかりません。"
                ".env ファイルに JQUANTSKEY=<キー> を記載してください。"
            )

    # ---------- 認証ヘッダ ----------

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key}

    # ---------- 汎用 GET ----------

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{JQUANTS_BASE_URL}{endpoint}"
        try:
            resp = requests.get(
                url, headers=self._auth_headers, params=params, timeout=30
            )
        except requests.RequestException as e:
            raise JQuantsAPIError(
                f"APIリクエスト失敗(ネットワーク): {e}"
            ) from e

        if resp.status_code in (401, 403):
            raise JQuantsAuthError(
                f"認証エラー status={resp.status_code} "
                f"body={resp.text[:300]}"
            )
        if resp.status_code != 200:
            raise JQuantsAPIError(
                f"APIエラー endpoint={endpoint} "
                f"status={resp.status_code} body={resp.text[:300]}"
            )
        return resp.json()

    # ---------- 各エンドポイントのラッパ ----------
    # v2 では一部のパスが変わっている可能性があるが、
    # ここでは公式クイックスタートで動作確認済みの /equities/bars/daily を中心に整備。

    def get_daily_quotes(
        self,
        code: str | None = None,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict:
        """日足株価(四本値+出来高)を取得。

        v2 エンドポイント: /equities/bars/daily

        Args:
            code: 銘柄コード(例 "7203")
            date: 単日取得 YYYYMMDD(例 "20260430")
            from_date: 期間取得 開始日 YYYYMMDD
            to_date:  期間取得 終了日 YYYYMMDD
        """
        params: dict[str, Any] = {}
        if code:
            params["code"] = code
        if date:
            params["date"] = date
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._get("/equities/bars/daily", params=params or None)

    def get_listed_info(
        self, code: str | None = None, date: str | None = None
    ) -> dict:
        """上場銘柄一覧 / 個別銘柄情報を取得。

        v2 エンドポイント候補(順に試行): /listed/info → /equities/listed/info
        """
        params: dict[str, Any] = {}
        if code:
            params["code"] = code
        if date:
            params["date"] = date
        # v1 と同じパスを優先、ダメなら別パスを試す
        try:
            return self._get("/listed/info", params=params or None)
        except JQuantsAPIError:
            return self._get("/equities/listed/info", params=params or None)

    def get_margin_weekly(self, code: str | None = None) -> dict:
        """信用取引週末残高(信用残)を取得。Standard プラン以上。

        v2 エンドポイント候補: /markets/weekly_margin_interest
        """
        params = {"code": code} if code else None
        return self._get("/markets/weekly_margin_interest", params=params)


# ---------- 動作確認用エントリポイント ----------


def _smoke_test() -> None:
    """`python src/jquants_client.py` で実行する簡易テスト。"""
    print("=" * 60)
    print("J-Quants 認証テスト (API v2 / x-api-key 方式)")
    print("=" * 60)

    client = JQuantsClient()
    print("[1/2] APIキー読込: OK (***隠匿***)")

    # 公式クイックスタートで確認済みの /equities/bars/daily でテスト
    # 直近の営業日として 2026-04-30 を使用(日付がない場合API側がエラーで返す)
    print("[2/2] 日足取得テスト (トヨタ自動車 7203 / 2026-04-30)...")
    try:
        quotes = client.get_daily_quotes(code="7203", date="20260430")
        bars = quotes.get("daily_quotes") or quotes.get("equities", {}).get(
            "bars"
        ) or quotes.get("bars") or []
        if bars:
            sample = bars[0] if isinstance(bars, list) else bars
            print(f"      OK 取得成功: {sample}")
        else:
            print(f"      レスポンス内容: {quotes}")
    except JQuantsAPIError as e:
        # 日付が休日などで取れない場合は別の日付を試す
        print(f"      ⚠️ 2026-04-30 取得失敗 ({e}). 2026-04-28 で再試行...")
        quotes = client.get_daily_quotes(code="7203", date="20260428")
        print(f"      レスポンス: {quotes}")

    print("=" * 60)
    print("認証テスト 完了")
    print("=" * 60)


if __name__ == "__main__":
    _smoke_test()
