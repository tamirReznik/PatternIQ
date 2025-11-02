import time
import logging
import requests
import yfinance as yf
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json

class EnhancedDataProvider:
    """
    Multi-source data provider combining the best free APIs for more reliable data

    Sources:
    1. Wikipedia - S&P 500 constituents with sector data
    2. Yahoo Finance - Price data, basic fundamentals
    3. Alpha Vantage - Alternative price data, news (free tier: 25 calls/day)
    4. FMP (Financial Modeling Prep) - Enhanced fundamentals (free tier: 250 calls/day)
    5. FRED (Federal Reserve) - Economic indicators
    6. SEC EDGAR - Official filings (via SEC API)
    """

    def __init__(self, alpha_vantage_key: str = None, fmp_key: str = None):
        self.logger = logging.getLogger("EnhancedDataProvider")
        self.alpha_vantage_key = alpha_vantage_key
        self.fmp_key = fmp_key

        # Rate limiters for different APIs
        self.yahoo_limiter = self._create_limiter(rate=10, per=60)  # 10/minute
        self.alpha_vantage_limiter = self._create_limiter(rate=5, per=60)  # 5/minute
        self.fmp_limiter = self._create_limiter(rate=300, per=86400)  # 300/day
        self.sec_limiter = self._create_limiter(rate=10, per=1)  # 10/second (SEC limit)

    def _create_limiter(self, rate: int, per: int):
        """Create a rate limiter"""
        return {
            'rate': rate,
            'per': per,
            'tokens': rate,
            'last': time.time()
        }

    def _acquire_token(self, limiter: dict) -> None:
        """Acquire a token from rate limiter"""
        now = time.time()
        elapsed = now - limiter['last']
        limiter['tokens'] = min(limiter['rate'],
                               limiter['tokens'] + elapsed * (limiter['rate'] / limiter['per']))

        if limiter['tokens'] >= 1:
            limiter['tokens'] -= 1
            limiter['last'] = now
        else:
            sleep_time = (1 - limiter['tokens']) * (limiter['per'] / limiter['rate'])
            time.sleep(sleep_time)
            limiter['tokens'] = 0
            limiter['last'] = time.time()

    def get_sp500_constituents_enhanced(self) -> List[Dict[str, Any]]:
        """
        Get S&P 500 constituents with enhanced data including sectors and market caps
        """
        self.logger.info("Fetching enhanced S&P 500 data...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        # Primary source: Wikipedia with sector data
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        constituents = []

        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                table = soup.find("table", {"id": "constituents"})

                if table:
                    for row in table.find_all("tr")[1:]:
                        cols = row.find_all("td")
                        if len(cols) >= 4:
                            symbol = cols[0].text.strip()
                            company_name = cols[1].text.strip()
                            sector = cols[2].text.strip()
                            industry = cols[3].text.strip()

                            constituents.append({
                                'symbol': symbol,
                                'company_name': company_name,
                                'sector': sector,
                                'industry': industry,
                                'source': 'wikipedia'
                            })

            self.logger.info(f"Fetched {len(constituents)} S&P 500 constituents from Wikipedia")

        except Exception as e:
            self.logger.error(f"Error fetching from Wikipedia: {e}")
            # Fallback to basic list
            fallback_stocks = [
                {'symbol': 'AAPL', 'sector': 'Technology', 'company_name': 'Apple Inc.'},
                {'symbol': 'MSFT', 'sector': 'Technology', 'company_name': 'Microsoft Corporation'},
                {'symbol': 'GOOGL', 'sector': 'Technology', 'company_name': 'Alphabet Inc.'},
                {'symbol': 'AMZN', 'sector': 'Consumer Discretionary', 'company_name': 'Amazon.com Inc.'},
                {'symbol': 'NVDA', 'sector': 'Technology', 'company_name': 'NVIDIA Corporation'},
            ]
            constituents = fallback_stocks

        return constituents

    def get_price_data_multi_source(self, ticker: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get price data with fallback between Yahoo Finance and Alpha Vantage
        """
        self.logger.info(f"Fetching price data for {ticker} from {start_date} to {end_date}")

        # Primary: Yahoo Finance
        try:
            self._acquire_token(self.yahoo_limiter)
            data = yf.download(ticker, start=start_date, end=end_date, interval="1d")

            if not data.empty:
                bars = []
                for idx, row in data.iterrows():
                    bars.append({
                        "date": idx.strftime('%Y-%m-%d'),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                        "adjusted_close": float(row["Adj Close"]),
                        "source": "yahoo"
                    })

                return {
                    "symbol": ticker,
                    "bars": bars,
                    "source": "yahoo",
                    "status": "success"
                }

        except Exception as e:
            self.logger.warning(f"Yahoo Finance failed for {ticker}: {e}")

        # Fallback: Alpha Vantage (if API key provided)
        if self.alpha_vantage_key:
            try:
                self._acquire_token(self.alpha_vantage_limiter)
                url = f"https://www.alphavantage.co/query"
                params = {
                    'function': 'TIME_SERIES_DAILY_ADJUSTED',
                    'symbol': ticker,
                    'outputsize': 'full',
                    'apikey': self.alpha_vantage_key
                }

                response = requests.get(url, params=params)
                data = response.json()

                if 'Time Series (Daily)' in data:
                    bars = []
                    time_series = data['Time Series (Daily)']

                    for date_str, values in time_series.items():
                        if start_date <= date_str <= end_date:
                            bars.append({
                                "date": date_str,
                                "open": float(values['1. open']),
                                "high": float(values['2. high']),
                                "low": float(values['3. low']),
                                "close": float(values['4. close']),
                                "volume": int(values['6. volume']),
                                "adjusted_close": float(values['5. adjusted close']),
                                "source": "alpha_vantage"
                            })

                    return {
                        "symbol": ticker,
                        "bars": sorted(bars, key=lambda x: x['date']),
                        "source": "alpha_vantage",
                        "status": "success"
                    }

            except Exception as e:
                self.logger.warning(f"Alpha Vantage failed for {ticker}: {e}")

        return {"symbol": ticker, "bars": [], "source": "none", "status": "failed"}

    def get_fundamentals_enhanced(self, ticker: str) -> Dict[str, Any]:
        """
        Get fundamental data from multiple sources
        """
        self.logger.info(f"Fetching fundamentals for {ticker}")
        fundamentals = {"symbol": ticker, "sources": []}

        # Source 1: Yahoo Finance basic fundamentals
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            yahoo_data = {
                "market_cap": info.get('marketCap'),
                "enterprise_value": info.get('enterpriseValue'),
                "trailing_pe": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "peg_ratio": info.get('pegRatio'),
                "price_to_book": info.get('priceToBook'),
                "revenue": info.get('totalRevenue'),
                "gross_margins": info.get('grossMargins'),
                "operating_margins": info.get('operatingMargins'),
                "profit_margins": info.get('profitMargins'),
                "debt_to_equity": info.get('debtToEquity'),
                "return_on_equity": info.get('returnOnEquity'),
                "revenue_growth": info.get('revenueGrowth'),
                "earnings_growth": info.get('earningsGrowth'),
                "source": "yahoo"
            }

            fundamentals["sources"].append(yahoo_data)

        except Exception as e:
            self.logger.warning(f"Yahoo fundamentals failed for {ticker}: {e}")

        # Source 2: Financial Modeling Prep (if API key provided)
        if self.fmp_key:
            try:
                self._acquire_token(self.fmp_limiter)

                # Key metrics
                url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}"
                params = {"apikey": self.fmp_key, "limit": 1}

                response = requests.get(url, params=params)
                data = response.json()

                if data and len(data) > 0:
                    metrics = data[0]
                    fmp_data = {
                        "pe_ratio": metrics.get('peRatio'),
                        "price_to_book": metrics.get('pbRatio'),
                        "price_to_sales": metrics.get('priceToSalesRatio'),
                        "enterprise_value": metrics.get('enterpriseValue'),
                        "ev_to_revenue": metrics.get('evToRevenue'),
                        "ev_to_ebitda": metrics.get('evToEbitda'),
                        "debt_to_equity": metrics.get('debtToEquity'),
                        "return_on_equity": metrics.get('roe'),
                        "return_on_assets": metrics.get('roa'),
                        "source": "fmp"
                    }

                    fundamentals["sources"].append(fmp_data)

            except Exception as e:
                self.logger.warning(f"FMP fundamentals failed for {ticker}: {e}")

        return fundamentals

    def get_earnings_calendar(self, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Get earnings calendar data
        """
        earnings = []

        # Source: Financial Modeling Prep
        if self.fmp_key:
            try:
                self._acquire_token(self.fmp_limiter)
                url = f"https://financialmodelingprep.com/api/v3/earning_calendar"
                params = {
                    "apikey": self.fmp_key,
                    "from": date_from,
                    "to": date_to
                }

                response = requests.get(url, params=params)
                data = response.json()

                for item in data:
                    earnings.append({
                        "symbol": item.get('symbol'),
                        "date": item.get('date'),
                        "time": item.get('time'),
                        "eps_estimate": item.get('epsEstimate'),
                        "eps_actual": item.get('epsActual'),
                        "revenue_estimate": item.get('revenueEstimate'),
                        "revenue_actual": item.get('revenueActual'),
                        "source": "fmp"
                    })

            except Exception as e:
                self.logger.warning(f"Earnings calendar fetch failed: {e}")

        return earnings

    def get_economic_indicators(self) -> Dict[str, Any]:
        """
        Get key economic indicators from FRED (Federal Reserve Economic Data)
        """
        indicators = {}

        try:
            # Key indicators (no API key required for basic access)
            fred_indicators = {
                'gdp': 'GDPC1',  # Real GDP
                'inflation': 'CPILFESL',  # Core CPI
                'unemployment': 'UNRATE',  # Unemployment Rate
                'fed_funds': 'FEDFUNDS',  # Federal Funds Rate
                'vix': 'VIXCLS'  # VIX Volatility Index
            }

            for name, series_id in fred_indicators.items():
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    'series_id': series_id,
                    'api_key': 'demo',  # Demo key for basic access
                    'file_type': 'json',
                    'limit': 1,
                    'sort_order': 'desc'
                }

                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if 'observations' in data and data['observations']:
                        latest = data['observations'][0]
                        indicators[name] = {
                            'value': latest.get('value'),
                            'date': latest.get('date'),
                            'source': 'fred'
                        }

        except Exception as e:
            self.logger.warning(f"FRED data fetch failed: {e}")

        return indicators

    def validate_data_quality(self, ticker: str, bars: List[Dict]) -> Dict[str, Any]:
        """
        Validate data quality and detect potential issues
        """
        if not bars:
            return {"status": "error", "issue": "no_data"}

        issues = []

        # Check for gaps in dates
        dates = [bar['date'] for bar in bars]
        date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

        for i in range(1, len(date_objects)):
            gap = (date_objects[i] - date_objects[i-1]).days
            if gap > 4:  # More than weekend gap
                issues.append(f"Data gap: {gap} days between {dates[i-1]} and {dates[i]}")

        # Check for extreme price movements (potential data errors)
        for i in range(1, len(bars)):
            prev_close = bars[i-1]['close']
            curr_open = bars[i]['open']
            gap = abs(curr_open - prev_close) / prev_close

            if gap > 0.5:  # 50% gap
                issues.append(f"Extreme gap: {gap:.1%} on {bars[i]['date']}")

        # Check volume anomalies
        volumes = [bar['volume'] for bar in bars if bar['volume'] > 0]
        if volumes:
            avg_volume = sum(volumes) / len(volumes)
            for bar in bars:
                if bar['volume'] > avg_volume * 10:
                    issues.append(f"Volume spike: {bar['volume']/avg_volume:.1f}x on {bar['date']}")

        return {
            "status": "validated",
            "symbol": ticker,
            "total_bars": len(bars),
            "date_range": f"{dates[0]} to {dates[-1]}" if dates else "none",
            "issues": issues,
            "quality_score": max(0, 100 - len(issues) * 10)
        }
