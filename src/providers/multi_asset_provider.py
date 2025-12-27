#!/usr/bin/env python3
"""
Enhanced Multi-Asset Data Provider
Extends S&P 500 stocks to include sector ETFs, crypto, and international markets

This is Phase 1 of performance enhancement - adding sector ETF trading
Expected boost: +2-3% annual return with moderate risk increase
"""

import time
import logging
import threading
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
from src.data.datasource import DataSource

class MultiAssetProvider(DataSource):
    """
    Enhanced data provider supporting multiple asset classes:
    1. S&P 500 individual stocks (existing)
    2. Sector ETFs (XLK, XLF, XLV, etc.)
    3. Cryptocurrency ETFs (GBTC, ETHE, BITO)
    4. International ETFs (EFA, EEM, VWO)
    5. Factor ETFs (MTUM, QUAL, VLUE)
    """

    def __init__(self, min_daily_volume: float = 10_000_000, min_market_cap: float = 1_000_000_000):
        self.logger = logging.getLogger("MultiAssetProvider")
        self.rate_limiter = self._create_rate_limiter(rate=10, per=60)
        self.rate_limiter_lock = threading.Lock()  # Thread-safe rate limiting
        
        # Volume and quality filters for mid/long-term trading
        self.min_daily_volume = min_daily_volume  # $10M minimum daily volume
        self.min_market_cap = min_market_cap  # $1B minimum market cap
        
        # Cache for symbol metadata to reduce API calls
        self._symbol_cache = {}
        self._cache_ttl = 86400  # 24 hours cache TTL

        # Define asset universes
        self.sector_etfs = {
            'XLK': 'Technology',
            'XLF': 'Financials',
            'XLV': 'Healthcare',
            'XLE': 'Energy',
            'XLI': 'Industrials',
            'XLU': 'Utilities',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLP': 'Consumer Staples',
            'XLY': 'Consumer Discretionary',
            'XLC': 'Communication Services'
        }

        self.crypto_etfs = {
            'GBTC': 'Bitcoin Trust',
            'ETHE': 'Ethereum Trust',
            'BITO': 'Bitcoin Strategy ETF',
            'BITI': 'Short Bitcoin Strategy ETF'
        }

        self.international_etfs = {
            'EFA': 'EAFE Developed Markets',
            'EEM': 'Emerging Markets',
            'VWO': 'Emerging Markets',
            'FXI': 'China Large-Cap',
            'EWJ': 'Japan',
            'EWZ': 'Brazil'
        }

        self.factor_etfs = {
            'MTUM': 'Momentum Factor',
            'QUAL': 'Quality Factor',
            'SIZE': 'Small Cap Factor',
            'USMV': 'Minimum Volatility',
            'VLUE': 'Value Factor'
        }

        self.logger.info("Multi-Asset Provider initialized with enhanced universe:")
        self.logger.info(f"  Sector ETFs: {len(self.sector_etfs)}")
        self.logger.info(f"  Crypto ETFs: {len(self.crypto_etfs)}")
        self.logger.info(f"  International ETFs: {len(self.international_etfs)}")
        self.logger.info(f"  Factor ETFs: {len(self.factor_etfs)}")

    def _create_rate_limiter(self, rate: int, per: int):
        """Create a simple rate limiter"""
        return {
            'rate': rate,
            'per': per,
            'tokens': rate,
            'last': time.time()
        }

    def _acquire_rate_limit(self):
        """Acquire rate limit token (thread-safe)"""
        with self.rate_limiter_lock:
            now = time.time()
            elapsed = now - self.rate_limiter['last']
            self.rate_limiter['tokens'] = min(
                self.rate_limiter['rate'],
                self.rate_limiter['tokens'] + elapsed * (self.rate_limiter['rate'] / self.rate_limiter['per'])
            )

            if self.rate_limiter['tokens'] >= 1:
                self.rate_limiter['tokens'] -= 1
                self.rate_limiter['last'] = now
            else:
                sleep_time = (1 - self.rate_limiter['tokens']) * (self.rate_limiter['per'] / self.rate_limiter['rate'])
                # Release lock before sleeping to allow other threads to proceed
                self.rate_limiter['last'] = time.time()
        
        # Sleep outside the lock to avoid blocking other threads
        if self.rate_limiter['tokens'] < 1:
            time.sleep(sleep_time)
            with self.rate_limiter_lock:
                self.rate_limiter['tokens'] = 0

    def list_symbols(self) -> List[str]:
        """Get comprehensive symbol list including all asset classes"""

        # Start with S&P 500 stocks
        sp500_symbols = self._get_sp500_symbols()

        # Add ETF symbols
        all_symbols = sp500_symbols.copy()
        all_symbols.extend(list(self.sector_etfs.keys()))
        all_symbols.extend(list(self.crypto_etfs.keys()))
        all_symbols.extend(list(self.international_etfs.keys()))
        all_symbols.extend(list(self.factor_etfs.keys()))

        # Remove duplicates while preserving order
        unique_symbols = list(dict.fromkeys(all_symbols))

        self.logger.info(f"Multi-asset universe: {len(unique_symbols)} total symbols")
        self.logger.info(f"  S&P 500 stocks: {len(sp500_symbols)}")
        self.logger.info(f"  Total ETFs: {len(unique_symbols) - len(sp500_symbols)}")

        return unique_symbols

    def _get_sp500_symbols(self) -> List[str]:
        """Get S&P 500 symbols from Wikipedia"""
        self.logger.info("Fetching S&P 500 symbols...")
        self._acquire_rate_limit()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        try:
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
                # Fallback to basic list
                symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK.B", "UNH", "JNJ"]

            return symbols

        except Exception as e:
            self.logger.error(f"Error fetching S&P 500 symbols: {e}")
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]  # Minimal fallback

    def get_symbol_metadata(self, symbol: str) -> Dict[str, Any]:
        """Get metadata for any symbol including asset class and sector"""

        if symbol in self.sector_etfs:
            return {
                'symbol': symbol,
                'asset_class': 'sector_etf',
                'sector': self.sector_etfs[symbol],
                'description': f"Sector ETF - {self.sector_etfs[symbol]}",
                'type': 'ETF'
            }
        elif symbol in self.crypto_etfs:
            return {
                'symbol': symbol,
                'asset_class': 'crypto_etf',
                'sector': 'Cryptocurrency',
                'description': f"Crypto ETF - {self.crypto_etfs[symbol]}",
                'type': 'ETF'
            }
        elif symbol in self.international_etfs:
            return {
                'symbol': symbol,
                'asset_class': 'international_etf',
                'sector': 'International',
                'description': f"International ETF - {self.international_etfs[symbol]}",
                'type': 'ETF'
            }
        elif symbol in self.factor_etfs:
            return {
                'symbol': symbol,
                'asset_class': 'factor_etf',
                'sector': 'Factor',
                'description': f"Factor ETF - {self.factor_etfs[symbol]}",
                'type': 'ETF'
            }
        else:
            return {
                'symbol': symbol,
                'asset_class': 'equity',
                'sector': 'Unknown',  # Would need to lookup from S&P 500 data
                'description': f"S&P 500 Stock - {symbol}",
                'type': 'Stock'
            }

    def get_bars(self, ticker: str, timeframe: str, start, end) -> List[Dict[str, Any]]:
        """Get price bars for any asset class with fallback and quality validation"""
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
        import os
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
        """Yahoo Finance method - supports single symbol or list of symbols for batch downloads"""
        self.logger.debug(f"Fetching bars for {ticker} [{timeframe}] from {start} to {end} via Yahoo Finance")
        self._acquire_rate_limit()

        # Support both single symbol and list of symbols for batch downloads
        data = yf.download(ticker, start=start, end=end, interval="1d" if timeframe=="1d" else "1m", progress=False, auto_adjust=True)

        if data.empty:
            raise ValueError(f"No data returned from Yahoo Finance for {ticker}")

        bars = []
        # Handle both single symbol and batch downloads (multi-index columns)
        if isinstance(ticker, list):
            # Batch download - data has multi-index columns (symbol, OHLCV)
            for sym in ticker:
                metadata = self.get_symbol_metadata(sym)
                if (sym, 'Open') in data.columns:
                    for idx, row in data.iterrows():
                        bars.append({
                            "t": idx,
                            "o": float(row[(sym, 'Open')]),
                            "h": float(row[(sym, 'High')]),
                            "l": float(row[(sym, 'Low')]),
                            "c": float(row[(sym, 'Close')]),
                            "v": int(row[(sym, 'Volume')]),
                            "vendor": "yahoo",
                            "asset_class": metadata.get("asset_class", "unknown"),
                            "symbol": sym  # Include symbol for batch processing
                        })
        else:
            # Single symbol download
            metadata = self.get_symbol_metadata(ticker)
            for idx, row in data.iterrows():
                bars.append({
                    "t": idx,
                    "o": float(row["Open"]),
                    "h": float(row["High"]),
                    "l": float(row["Low"]),
                    "c": float(row["Close"]),
                    "v": int(row["Volume"]),
                    "vendor": "yahoo",
                    "asset_class": metadata.get("asset_class", "unknown")
                })
        return bars
    
    def _get_bars_alpha_vantage(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        """Alpha Vantage fallback"""
        import os
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
        metadata = self.get_symbol_metadata(ticker)
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
                    "vendor": "alpha_vantage",
                    "asset_class": metadata.get("asset_class", "unknown")
                })
        
        return sorted(bars, key=lambda x: x['t'])
    
    def _get_bars_polygon(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        """Polygon.io fallback"""
        import os
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
        metadata = self.get_symbol_metadata(ticker)
        for result in data.get('results', []):
            bars.append({
                "t": pd.to_datetime(result['t'], unit='ms'),
                "o": float(result['o']),
                "h": float(result['h']),
                "l": float(result['l']),
                "c": float(result['c']),
                "v": int(result['v']),
                "vendor": "polygon",
                "asset_class": metadata.get("asset_class", "unknown")
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
        """Get corporate actions - primarily for stocks, limited for ETFs"""
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
        """Get fundamental data - enhanced for different asset classes"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            metadata = self.get_symbol_metadata(ticker)

            base_fundamentals = {
                'symbol': ticker,
                'asset_class': metadata['asset_class'],
                'market_cap': info.get('totalAssets') if metadata['type'] == 'ETF' else info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'price_to_book': info.get('priceToBook'),
                'expense_ratio': info.get('annualReportExpenseRatio'),  # Important for ETFs
                'beta': info.get('beta'),
                'source': 'yahoo_enhanced'
            }

            # Add asset-class specific metrics
            if metadata['asset_class'] == 'sector_etf':
                base_fundamentals.update({
                    'sector': metadata['sector'],
                    'fund_family': info.get('fundFamily'),
                    'yield': info.get('yield'),
                    'category': info.get('category')
                })
            elif metadata['asset_class'] == 'crypto_etf':
                base_fundamentals.update({
                    'crypto_exposure': True,
                    'yield': info.get('yield'),
                    'category': info.get('category')
                })
            elif metadata['asset_class'] == 'equity':
                base_fundamentals.update({
                    'revenue': info.get('totalRevenue'),
                    'profit_margins': info.get('profitMargins'),
                    'debt_to_equity': info.get('debtToEquity'),
                    'return_on_equity': info.get('returnOnEquity')
                })

            return base_fundamentals

        except Exception as e:
            self.logger.warning(f"Could not fetch fundamentals for {ticker}: {e}")
            return {'symbol': ticker, 'asset_class': 'unknown'}

    def get_earnings(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        """Get earnings data - mainly applicable to individual stocks"""
        metadata = self.get_symbol_metadata(ticker)

        # Only fetch earnings for individual stocks, not ETFs
        if metadata['asset_class'] == 'equity':
            # TODO: Implement earnings fetching logic
            return []
        else:
            return []  # ETFs don't have earnings

    def get_news(self, ticker: str, start, end) -> List[Dict[str, Any]]:
        """Get news data - applicable to all asset classes"""
        # TODO: Implement news fetching from various sources
        return []

    def get_sector_strength(self) -> Dict[str, float]:
        """
        Calculate relative strength of different sectors
        This helps with sector rotation strategies
        """
        sector_performance = {}

        try:
            # Calculate 20-day momentum for each sector ETF
            for etf, sector in self.sector_etfs.items():
                try:
                    data = yf.download(etf, period="3mo", interval="1d", progress=False)
                    if not data.empty and len(data) >= 20:
                        # Calculate 20-day momentum
                        current_price = data['Close'].iloc[-1]
                        price_20d_ago = data['Close'].iloc[-20]
                        momentum = (current_price - price_20d_ago) / price_20d_ago
                        sector_performance[sector] = float(momentum)
                except Exception as e:
                    self.logger.warning(f"Could not calculate momentum for {etf}: {e}")
                    sector_performance[sector] = 0.0

        except Exception as e:
            self.logger.error(f"Error calculating sector strength: {e}")

        return sector_performance

    def get_etf_recommendations(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get top ETF recommendations based on momentum and technical analysis
        This is the core of the sector rotation strategy
        """
        recommendations = []

        # Get sector strength
        sector_strength = self.get_sector_strength()

        # Sort sectors by performance
        sorted_sectors = sorted(sector_strength.items(), key=lambda x: x[1], reverse=True)

        # Generate recommendations for top sectors
        for i, (sector, momentum) in enumerate(sorted_sectors[:top_n]):
            # Find the ETF for this sector
            etf_symbol = None
            for etf, etf_sector in self.sector_etfs.items():
                if etf_sector == sector:
                    etf_symbol = etf
                    break

            if etf_symbol:
                # Calculate position size based on momentum strength
                if momentum > 0.10:  # >10% momentum
                    signal = "STRONG_BUY"
                    position_size = 4.0
                elif momentum > 0.05:  # >5% momentum
                    signal = "BUY"
                    position_size = 3.0
                elif momentum > 0:  # Positive momentum
                    signal = "WEAK_BUY"
                    position_size = 2.0
                else:
                    signal = "HOLD"
                    position_size = 0.0

                # Get current price
                try:
                    current_data = yf.download(etf_symbol, period="1d", progress=False)
                    current_price = float(current_data['Close'].iloc[-1]) if not current_data.empty else 0.0
                except:
                    current_price = 0.0

                recommendations.append({
                    'symbol': etf_symbol,
                    'sector': sector,
                    'signal': signal,
                    'momentum': momentum,
                    'position_size': position_size,
                    'price': current_price,
                    'asset_class': 'sector_etf',
                    'rationale': f"Sector momentum: {momentum:.1%} over 20 days"
                })

        return recommendations
