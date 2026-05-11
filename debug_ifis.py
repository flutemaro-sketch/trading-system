from src.consensus_fetcher import ConsensusFetcher
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

with ConsensusFetcher(headless=True) as f:
    params = {"action": "tp1", "sa": "report", "bcode": "7013"}
    url = f"https://kabuyoho.ifis.co.jp/index.php?" + "&".join(f"{k}={v}" for k, v in params.items())
    print(f"[INFO] アクセス中...")
    f.driver.get(url)
    
    WebDriverWait(f.driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))
    time.sleep(2)
    
    soup = BeautifulSoup(f.driver.page_source, "html.parser")
    text = soup.get_text()
    
    print("\n=== 最初の3000文字 ===")
    print(text[:3000])
    print("\n=== 営業利益関連 ===")
    for i, line in enumerate(text.split('\n')):
        if "営業" in line:
            print(f"Line {i}: {line}")
