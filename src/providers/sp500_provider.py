import time
import logging
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd  # Add missing pandas import
from typing import List, Dict, Any
from src.data.datasource import DataSource

# Import the enhanced provider
try:
    from src.providers.enhanced_data_provider import EnhancedDataProvider
    from src.config.data_sources import DataSourceConfig
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

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

        # Skip enhanced provider for now - focus on trading
        self.enhanced_provider = None
        self.logger.info("Using basic Yahoo Finance provider (optimized for daily trading)")

    def list_symbols(self) -> List[str]:
        """Get S&P 500 symbols - keep simple for daily operation"""
        return self._get_symbols_basic()

    def _get_symbols_basic(self) -> List[str]:
        """Wikipedia scraping method - reliable for S&P 500"""
        self.logger.info("Fetching S&P 500 symbols...")
        self.rate_limiter.acquire()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
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
            # Fallback to a static list for testing
            self.logger.info("Using fallback symbol list...")
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B", "UNH", "JNJ"]

        return symbols

    def get_bars(self, ticker: str, timeframe: str, start, end) -> List[Dict[str, Any]]:
        """Get price bars - focus on reliability for daily trading"""
        return self._get_bars_basic(ticker, timeframe, start, end)

    def _get_bars_basic(self, ticker: str, timeframe: str, start, end) -> List[Dict[str, Any]]:
        """Yahoo Finance method - reliable enough for daily trading"""
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
        """Get corporate actions with proper pandas import"""
        try:
            stock = yf.Ticker(ticker)
            actions = stock.actions

            if not actions.empty:
                corporate_actions = []
                for date, row in actions.iterrows():
                    action = {}
                    if pd.notna(row.get('Dividends', 0)) and row['Dividends'] > 0:
                        action = {
                            'date': date.strftime('%Y-%m-%d'),
                            'type': 'dividend',
                            'amount': float(row['Dividends']),
                            'symbol': ticker
                        }
                    elif pd.notna(row.get('Stock Splits', 0)) and row['Stock Splits'] != 1:
                        action = {
                            'date': date.strftime('%Y-%m-%d'),
                            'type': 'split',
                            'ratio': float(row['Stock Splits']),
                            'symbol': ticker
                        }

                    if action:
                        corporate_actions.append(action)

                return corporate_actions
        except Exception as e:
            self.logger.warning(f"Could not fetch corporate actions for {ticker}: {e}")

        return []

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Get basic fundamental data for trading decisions"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                'symbol': ticker,
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'price_to_book': info.get('priceToBook'),
                'revenue': info.get('totalRevenue'),
                'profit_margins': info.get('profitMargins'),
                'debt_to_equity': info.get('debtToEquity'),
                'return_on_equity': info.get('returnOnEquity'),
                'beta': info.get('beta'),
                'source': 'yahoo_basic'
            }
        except Exception as e:
            self.logger.warning(f"Could not fetch fundamentals for {ticker}: {e}")
            return {}

    def get_earnings(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        """Placeholder for earnings data"""
        return []

    def get_news(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        """Placeholder for news data"""
        return []
