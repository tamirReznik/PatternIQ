#!/usr/bin/env python3
"""
Unified Backup Data Provider
Provides fallback data sources when primary provider fails
Supports: Alpha Vantage, Polygon.io
"""

import os
import logging
import requests
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime

class BackupProvider:
    """
    Unified backup provider for when primary data sources fail
    Supports multiple backup APIs with automatic failover
    """
    
    def __init__(self):
        self.logger = logging.getLogger("BackupProvider")
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.polygon_key = os.getenv('POLYGON_API_KEY')
        
        # Rate limiters
        self.alpha_vantage_limiter = {'tokens': 25, 'last': 0, 'rate': 25, 'per': 86400}  # 25/day
        self.polygon_limiter = {'tokens': 5, 'last': 0, 'rate': 5, 'per': 60}  # 5/minute
    
    def get_bars(self, ticker: str, start: str, end: str, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get price bars from backup source
        
        Args:
            ticker: Symbol to fetch
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            source: Preferred source ('alpha_vantage' or 'polygon'), None for auto
        
        Returns:
            List of bar dictionaries
        """
        if source == 'alpha_vantage' or (source is None and self.alpha_vantage_key):
            try:
                return self._get_bars_alpha_vantage(ticker, start, end)
            except Exception as e:
                self.logger.warning(f"Alpha Vantage backup failed for {ticker}: {e}")
        
        if source == 'polygon' or (source is None and self.polygon_key):
            try:
                return self._get_bars_polygon(ticker, start, end)
            except Exception as e:
                self.logger.warning(f"Polygon.io backup failed for {ticker}: {e}")
        
        raise ValueError(f"All backup sources failed for {ticker}")
    
    def _get_bars_alpha_vantage(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        """Alpha Vantage API (free tier: 25 calls/day)"""
        if not self.alpha_vantage_key:
            raise ValueError("Alpha Vantage API key not configured")
        
        # Check rate limit
        import time
        now = time.time()
        elapsed = now - self.alpha_vantage_limiter['last']
        self.alpha_vantage_limiter['tokens'] = min(
            self.alpha_vantage_limiter['rate'],
            self.alpha_vantage_limiter['tokens'] + int(elapsed * (self.alpha_vantage_limiter['rate'] / self.alpha_vantage_limiter['per']))
        )
        
        if self.alpha_vantage_limiter['tokens'] < 1:
            raise ValueError("Alpha Vantage rate limit exceeded (25 calls/day)")
        
        self.alpha_vantage_limiter['tokens'] -= 1
        self.alpha_vantage_limiter['last'] = now
        
        self.logger.debug(f"Fetching {ticker} via Alpha Vantage backup")
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': ticker,
            'outputsize': 'full',
            'apikey': self.alpha_vantage_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'Error Message' in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        if 'Note' in data:
            raise ValueError(f"Alpha Vantage rate limit: {data['Note']}")
        
        if 'Time Series (Daily)' not in data:
            raise ValueError(f"No time series data for {ticker}")
        
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
    
    def _get_bars_polygon(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        """Polygon.io API (free tier: 5 calls/minute)"""
        if not self.polygon_key:
            raise ValueError("Polygon.io API key not configured")
        
        # Check rate limit
        import time
        now = time.time()
        elapsed = now - self.polygon_limiter['last']
        self.polygon_limiter['tokens'] = min(
            self.polygon_limiter['rate'],
            self.polygon_limiter['tokens'] + int(elapsed * (self.polygon_limiter['rate'] / self.polygon_limiter['per']))
        )
        
        if self.polygon_limiter['tokens'] < 1:
            # Wait for token
            sleep_time = (1 - self.polygon_limiter['tokens']) * (self.polygon_limiter['per'] / self.polygon_limiter['rate'])
            time.sleep(sleep_time)
            self.polygon_limiter['tokens'] = 0
        
        self.polygon_limiter['tokens'] -= 1
        self.polygon_limiter['last'] = now
        
        self.logger.debug(f"Fetching {ticker} via Polygon.io backup")
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 5000,
            'apiKey': self.polygon_key
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

