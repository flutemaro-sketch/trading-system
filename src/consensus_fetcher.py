"""
IFISからアナリストコンセンサス予想データを取得するモジュール（Selenium版）。

IFIS株予報から各銘柄のコンセンサス予想(営業利益、純利益等)を取得して、
実績との比較でスコア化する。JavaScriptレンダリング後にHTMLをパースするため、
動的読み込みコンテンツにも対応。

使い方:
    from src.consensus_fetcher import ConsensusFetcher
    fetcher = ConsensusFetcher()
    consensus = fetcher.fetch_consensus(code='7013')
    fetcher.close()
"""
from __future__ import annotations

import re
import time
from typing import Any

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager


class ConsensusFetcher:
    """IFIS株予報からコンセンサスデータをSeleniumで取得。"""

    BASE_URL = "https://kabuyoho.ifis.co.jp/index.php"
    SLEEP_SEC = 1.0  # リクエスト間隔(秒)

    def __init__(self, headless: bool = True):
        """Seleniumブラウザを初期化。

        Args:
            headless: ヘッドレスモード(画面を表示しない)
        """
        self.headless = headless
        self.driver = None
        self._init_driver()

    def _init_driver(self):
        """Microsoft Edge WebDriverを初期化。"""
        edge_options = Options()
        if self.headless:
            edge_options.add_argument("--headless")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--window-size=1280,1024")
        edge_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        try:
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=edge_options)
        except Exception as e:
            # webdriver_manager がオフラインの場合は、Edge を直接起動してみる
            print(f"[WARNING] WebDriver download failed: {e}")
            print("[INFO] Attempting to use Edge directly...")
            self.driver = webdriver.Edge(options=edge_options)

    def fetch_consensus(self, code: str, wait_time: int = 10) -> dict[str, Any] | None:
        """1銘柄のコンセンサス予想をSeleniumで取得。

        Args:
            code: 銘柄コード(例: "7013")
            wait_time: ページロード待機時間(秒)

        Returns:
            {
                "code": "7013",
                "operating_profit": 200000,
                "ordinary_profit": 185000,
                "net_income": 171000,
                "eps": 123.45,
                ...
            }
            または取得失敗時は None
        """
        try:
            # ページを開く
            params = {
                "action": "tp1",
                "sa": "report",
                "bcode": code,
            }
            url = f"{self.BASE_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            print(f"[DEBUG] {code}: アクセス中 {url}", flush=True)
            self.driver.get(url)

            # ページロード待機（テーブルが出現するまで）
            print(f"[DEBUG] {code}: テーブル待機中({wait_time}秒)...", flush=True)
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
            )
            print(f"[DEBUG] {code}: テーブル検出OK", flush=True)

            # ページソースを取得してBeautifulSoupでパース
            page_source = self.driver.page_source
            print(f"[DEBUG] {code}: ページソース取得OK({len(page_source)}bytes)", flush=True)
            soup = BeautifulSoup(page_source, "html.parser")

            consensus = {
                "code": code,
                "operating_profit": None,
                "ordinary_profit": None,
                "net_income": None,
                "eps": None,
            }

            # テキスト全体を取得
            text = soup.get_text()
            print(f"[DEBUG] {code}: テキスト抽出OK({len(text)}chars)", flush=True)

            # 正規表現で数値を抽出
            patterns = {
                "operating_profit": [
                    r"営業利益\s*\(コンセンサス\)[^\d]*([\d,]+)",
                    r"営業利益予想[^\d]*([\d,]+)\s*百万円",
                ],
                "ordinary_profit": [
                    r"経常利益\s*\(コンセンサス\)[^\d]*([\d,]+)",
                    r"経常利益予想[^\d]*([\d,]+)\s*百万円",
                ],
                "net_income": [
                    r"(?:純利益|当期利益)\s*\(コンセンサス\)[^\d]*([\d,]+)",
                    r"(?:純利益|当期利益)予想[^\d]*([\d,]+)\s*百万円",
                ],
                "eps": [
                    r"EPS\s*\(コンセンサス\)[^\d]*([\d.]+)",
                    r"EPS予想[^\d]*([\d.]+)\s*円",
                ],
            }

            match_count = 0
            for key, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, text)
                    if match:
                        val_str = match.group(1).replace(",", "")
                        try:
                            if key == "eps":
                                consensus[key] = float(val_str)
                            else:
                                consensus[key] = int(float(val_str))
                            match_count += 1
                            print(f"[DEBUG] {code}: {key}={consensus[key]}", flush=True)
                            break
                        except ValueError:
                            pass

            print(f"[DEBUG] {code}: マッチ数={match_count}", flush=True)

            # 有効なデータが1つ以上あれば返す
            if any(v is not None for k, v in consensus.items() if k != "code"):
                print(f"[INFO] {code}: 取得成功 {consensus}", flush=True)
                return consensus

            print(f"[WARNING] {code}: データなし", flush=True)
            return None

        except Exception as e:
            import traceback
            print(f"[ERROR] {code} consensus fetch failed: {e}", flush=True)
            print(f"[ERROR] トレースバック:\n{traceback.format_exc()}", flush=True)
            return None

        finally:
            # 次のリクエストの前に待機
            time.sleep(self.SLEEP_SEC)

    def fetch_multi(
        self, codes: list[str], verbose: bool = False
    ) -> dict[str, dict[str, Any]]:
        """複数銘柄のコンセンサスをSeleniumで取得。

        Args:
            codes: 銘柄コード一覧
            verbose: 進捗表示

        Returns:
            {code: consensus_dict, ...}
        """
        results = {}

        for i, code in enumerate(codes, 1):
            if verbose:
                print(f"[{i}/{len(codes)}] {code}...", end=" ", flush=True)

            result = self.fetch_consensus(code)
            if result:
                results[code] = result
                if verbose:
                    print("OK")
            else:
                if verbose:
                    print("SKIP")

        return results

    def close(self):
        """ブラウザを閉じる。"""
        if self.driver:
            self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ---------- 動作確認 ----------

def _smoke_test() -> None:
    """簡易テスト: IHI(7013)のコンセンサスを取得。"""
    print("=" * 60)
    print("IFISコンセンサス取得 テスト (Selenium版)")
    print("=" * 60)

    with ConsensusFetcher(headless=True) as fetcher:
        result = fetcher.fetch_consensus("7013")

        if result:
            print(f"\nコード: {result['code']}")
            if result['operating_profit']:
                print(f"営業利益予想: {result['operating_profit']}百万円")
            if result['net_income']:
                print(f"純利益予想: {result['net_income']}百万円")
            if result['eps']:
                print(f"EPS予想: {result['eps']}円")
        else:
            print("取得失敗")

    print("=" * 60)


if __name__ == "__main__":
    _smoke_test()
