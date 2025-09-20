import time
import logging
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from typing import List, Dict, Any
from src.data.datasource import DataSource

class RateLimiter:
    def __init__(self, rate: int, per: int):
        self.rate = rate
        self.per = per
        self.tokens = rate
        self.last = time.time()

    def acquire(self):
        now = time.time()
        elapsed = now - self.last
        self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.per))
        if self.tokens >= 1:
            self.tokens -= 1
            self.last = now
            return True
        else:
            sleep_time = (1 - self.tokens) * (self.per / self.rate)
            time.sleep(sleep_time)
            self.tokens = 0
            self.last = time.time()
            return True

class SP500Provider(DataSource):
    def __init__(self):
        self.logger = logging.getLogger("SP500Provider")
        self.rate_limiter = RateLimiter(rate=10, per=60)  # 10 requests per minute

    def list_symbols(self) -> List[str]:
        self.logger.info("Fetching S&P 500 symbols...")
        self.rate_limiter.acquire()

        # Add proper headers to avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        resp = requests.get(url, headers=headers)
        symbols = []

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table", {"id": "constituents"})
            if table:
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if cols:
                        symbol = cols[0].text.strip()
                        symbols.append(symbol)
        else:
            self.logger.error(f"Failed to fetch symbols from Wikipedia: {resp.status_code}")
            # Fallback to a static list of popular S&P 500 symbols for testing
            self.logger.info("Using fallback symbol list for testing...")
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B", "UNH", "JNJ"]

        return symbols

    def get_bars(self, ticker: str, timeframe: str, start, end) -> List[Dict[str, Any]]:
        self.logger.info(f"Fetching bars for {ticker} [{timeframe}] from {start} to {end}")
        self.rate_limiter.acquire()
        data = yf.download(ticker, start=start, end=end, interval="1d" if timeframe=="1d" else "1m")
        bars = []
        for idx, row in data.iterrows():
            bars.append({
                "t": idx,
                "o": float(row["Open"]),
                "h": float(row["High"]),
                "l": float(row["Low"]),
                "c": float(row["Close"]),
                "v": int(row["Volume"]),
                "vendor": "yahoo"
            })
        return bars

    def get_corporate_actions(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        # TODO: Implement actual fetch from vendor
        return []

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        # TODO: Implement actual fetch from vendor
        return {}

    def get_earnings(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        # TODO: Implement actual fetch from vendor
        return []

    def get_news(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        # TODO: Implement actual fetch from vendor
        return []
