import time
import logging
import os
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
    def __init__(self, min_daily_volume: float = 10_000_000, min_market_cap: float = 1_000_000_000, min_days_listed: int = 90):
        self.logger = logging.getLogger("SP500Provider")
        self.rate_limiter = RateLimiter(rate=10, per=60)  # 10 requests per minute
        
        # Volume and quality filters for mid/long-term trading
        self.min_daily_volume = min_daily_volume  # $10M minimum daily volume
        self.min_market_cap = min_market_cap  # $1B minimum market cap
        self.min_days_listed = min_days_listed  # At least 90 days of trading history
        
        # Cache for symbol metadata to reduce API calls
        self._symbol_cache = {}
        self._cache_ttl = 86400  # 24 hours cache TTL

        # Skip enhanced provider for now - focus on trading
        self.enhanced_provider = None
        self.logger.info("Using basic Yahoo Finance provider (optimized for daily trading)")
        self.logger.info(f"Filters: min_volume=${min_daily_volume:,.0f}, min_mcap=${min_market_cap:,.0f}, min_days={min_days_listed}")

    def list_symbols(self) -> List[str]:
        """Get S&P 500 symbols with volume filtering for mid/long-term trading"""
        all_symbols = self._get_symbols_basic()
        filtered_symbols = self._filter_by_volume_and_quality(all_symbols)
        self.logger.info(f"Filtered {len(all_symbols)} symbols to {len(filtered_symbols)} after volume/quality filters")
        return filtered_symbols
    
    def _filter_by_volume_and_quality(self, symbols: List[str]) -> List[str]:
        """Filter symbols by daily volume, market cap, and trading history"""
        filtered = []
        failed_count = 0
        
        for symbol in symbols:
            try:
                # Check cache first
                cache_key = f"{symbol}_metadata"
                if cache_key in self._symbol_cache:
                    cached_data = self._symbol_cache[cache_key]
                    if time.time() - cached_data['timestamp'] < self._cache_ttl:
                        metadata = cached_data['data']
                    else:
                        metadata = self._get_symbol_metadata(symbol)
                        self._symbol_cache[cache_key] = {'data': metadata, 'timestamp': time.time()}
                else:
                    metadata = self._get_symbol_metadata(symbol)
                    self._symbol_cache[cache_key] = {'data': metadata, 'timestamp': time.time()}
                
                # Apply filters
                avg_volume = metadata.get('avg_daily_volume', 0)
                market_cap = metadata.get('market_cap', 0)
                days_listed = metadata.get('days_listed', 0)
                
                if (avg_volume >= self.min_daily_volume and 
                    market_cap >= self.min_market_cap and 
                    days_listed >= self.min_days_listed):
                    filtered.append(symbol)
                else:
                    self.logger.debug(f"Filtered out {symbol}: vol=${avg_volume:,.0f}, mcap=${market_cap:,.0f}, days={days_listed}")
                    
            except Exception as e:
                failed_count += 1
                self.logger.warning(f"Could not get metadata for {symbol}: {e}")
                # Include symbol if we can't verify (fail open for reliability)
                filtered.append(symbol)
        
        if failed_count > 0:
            self.logger.warning(f"Failed to get metadata for {failed_count} symbols, included them anyway")
        
        return filtered
    
    def _get_symbol_metadata(self, symbol: str) -> Dict[str, Any]:
        """Get symbol metadata including volume, market cap, and listing history"""
        try:
            self.rate_limiter.acquire()
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get recent price data to calculate average daily volume
            hist = ticker.history(period="3mo")
            avg_volume = 0
            avg_price = 0
            days_listed = 0
            
            if not hist.empty:
                # Calculate average daily volume in dollars
                avg_volume_shares = hist['Volume'].mean()
                avg_price = hist['Close'].mean()
                avg_volume = avg_volume_shares * avg_price if avg_price > 0 else 0
                days_listed = len(hist)
            
            return {
                'symbol': symbol,
                'market_cap': info.get('marketCap', 0) or info.get('totalAssets', 0) or 0,
                'avg_daily_volume': avg_volume,
                'avg_price': avg_price,
                'days_listed': days_listed,
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown')
            }
        except Exception as e:
            self.logger.warning(f"Error getting metadata for {symbol}: {e}")
            return {
                'symbol': symbol,
                'market_cap': 0,
                'avg_daily_volume': 0,
                'avg_price': 0,
                'days_listed': 0,
                'sector': 'Unknown',
                'industry': 'Unknown'
            }

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
        """Get price bars with fallback mechanism and data quality validation"""
        bars = self._get_bars_with_fallback(ticker, timeframe, start, end)
        
        # Validate data quality
        if bars:
            quality_report = self._validate_data_quality(ticker, bars)
            if quality_report.get('quality_score', 100) < 70:
                self.logger.warning(f"Data quality issues for {ticker}: {quality_report.get('issues', [])}")
        
        return bars

    def _get_bars_with_fallback(self, ticker: str, timeframe: str, start, end) -> List[Dict[str, Any]]:
        """Get bars with fallback: Yahoo Finance → Alpha Vantage → Polygon"""
        # Primary: Yahoo Finance
        try:
            return self._get_bars_yahoo(ticker, timeframe, start, end)
        except Exception as e:
            self.logger.warning(f"Yahoo Finance failed for {ticker}: {e}")
        
        # Fallback 1: Alpha Vantage (if API key available)
        alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if alpha_vantage_key:
            try:
                return self._get_bars_alpha_vantage(ticker, start, end)
            except Exception as e:
                self.logger.warning(f"Alpha Vantage failed for {ticker}: {e}")
        
        # Fallback 2: Polygon.io (if API key available)
        polygon_key = os.getenv('POLYGON_API_KEY')
        if polygon_key:
            try:
                return self._get_bars_polygon(ticker, start, end)
            except Exception as e:
                self.logger.warning(f"Polygon.io failed for {ticker}: {e}")
        
        self.logger.error(f"All data sources failed for {ticker}")
        return []

    def _get_bars_yahoo(self, ticker: str, timeframe: str, start, end) -> List[Dict[str, Any]]:
        """Yahoo Finance method - reliable enough for daily trading"""
        self.logger.debug(f"Fetching bars for {ticker} [{timeframe}] from {start} to {end} via Yahoo Finance")
        self.rate_limiter.acquire()
        data = yf.download(ticker, start=start, end=end, interval="1d" if timeframe=="1d" else "1m", progress=False)
        
        if data.empty:
            raise ValueError(f"No data returned from Yahoo Finance for {ticker}")
        
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
    
    def _get_bars_alpha_vantage(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        """Alpha Vantage fallback (free tier: 25 calls/day)"""
        alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not alpha_vantage_key:
            raise ValueError("Alpha Vantage API key not configured")
        
        self.logger.debug(f"Fetching bars for {ticker} via Alpha Vantage")
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': ticker,
            'outputsize': 'full',
            'apikey': alpha_vantage_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'Error Message' in data or 'Note' in data:
            raise ValueError(f"Alpha Vantage error: {data.get('Error Message', data.get('Note', 'Unknown error'))}")
        
        if 'Time Series (Daily)' not in data:
            raise ValueError(f"No time series data in Alpha Vantage response for {ticker}")
        
        bars = []
        time_series = data['Time Series (Daily)']
        for date_str, values in time_series.items():
            if start <= date_str <= end:
                bars.append({
                    "t": pd.to_datetime(date_str),
                    "o": float(values['1. open']),
                    "h": float(values['2. high']),
                    "l": float(values['3. low']),
                    "c": float(values['4. close']),
                    "v": int(values['6. volume']),
                    "vendor": "alpha_vantage"
                })
        
        return sorted(bars, key=lambda x: x['t'])
    
    def _get_bars_polygon(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        """Polygon.io fallback (free tier: 5 calls/minute)"""
        polygon_key = os.getenv('POLYGON_API_KEY')
        if not polygon_key:
            raise ValueError("Polygon.io API key not configured")
        
        self.logger.debug(f"Fetching bars for {ticker} via Polygon.io")
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 5000,
            'apiKey': polygon_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') != 'OK':
            raise ValueError(f"Polygon.io error: {data.get('status', 'Unknown error')}")
        
        bars = []
        for result in data.get('results', []):
            bars.append({
                "t": pd.to_datetime(result['t'], unit='ms'),
                "o": float(result['o']),
                "h": float(result['h']),
                "l": float(result['l']),
                "c": float(result['c']),
                "v": int(result['v']),
                "vendor": "polygon"
            })
        
        return bars
    
    def _validate_data_quality(self, ticker: str, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data quality: detect gaps, outliers, and anomalies"""
        if not bars:
            return {"status": "error", "issue": "no_data", "quality_score": 0}
        
        issues = []
        dates = [bar['t'] for bar in bars]
        dates_sorted = sorted(dates)
        
        # Check for date gaps (more than 4 days = potential data issue)
        for i in range(1, len(dates_sorted)):
            if isinstance(dates_sorted[i], pd.Timestamp) and isinstance(dates_sorted[i-1], pd.Timestamp):
                gap = (dates_sorted[i] - dates_sorted[i-1]).days
                if gap > 4:  # More than weekend gap
                    issues.append(f"Data gap: {gap} days between {dates_sorted[i-1]} and {dates_sorted[i]}")
        
        # Check for extreme price movements (potential data errors)
        for i in range(1, len(bars)):
            prev_close = bars[i-1]['c']
            curr_open = bars[i]['o']
            if prev_close > 0:
                gap_pct = abs(curr_open - prev_close) / prev_close
                if gap_pct > 0.5:  # 50% gap (likely split or error)
                    # Check if it's a reasonable split (2:1, 3:1, etc.)
                    ratio = curr_open / prev_close if prev_close > 0 else 1
                    if not (0.3 <= ratio <= 3.0):  # Allow 3:1 splits but flag extreme
                        issues.append(f"Extreme price gap: {gap_pct:.1%} on {bars[i]['t']}")
        
        # Check for zero or negative prices
        for bar in bars:
            if bar['c'] <= 0 or bar['o'] <= 0 or bar['h'] <= 0 or bar['l'] <= 0:
                issues.append(f"Invalid price data on {bar['t']}")
        
        # Check volume anomalies (spikes > 10x average)
        volumes = [bar['v'] for bar in bars if bar['v'] > 0]
        if volumes:
            avg_volume = sum(volumes) / len(volumes)
            for bar in bars:
                if bar['v'] > avg_volume * 10 and avg_volume > 0:
                    issues.append(f"Volume spike: {bar['v']/avg_volume:.1f}x average on {bar['t']}")
        
        quality_score = max(0, 100 - len(issues) * 10)
        
        return {
            "status": "validated",
            "symbol": ticker,
            "total_bars": len(bars),
            "date_range": f"{dates_sorted[0]} to {dates_sorted[-1]}" if dates_sorted else "none",
            "issues": issues,
            "quality_score": quality_score
        }

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
