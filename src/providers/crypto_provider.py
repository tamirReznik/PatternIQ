#!/usr/bin/env python3
"""
Cryptocurrency Data Provider
Provides direct crypto prices (BTC, ETH, etc.) for mid/long-term trading
Uses CoinGecko API (free, no key required) and CryptoCompare as backup
"""

import os
import logging
import requests
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class CryptoProvider:
    """
    Provider for direct cryptocurrency prices
    Supports: CoinGecko (primary), CryptoCompare (backup)
    """
    
    def __init__(self):
        self.logger = logging.getLogger("CryptoProvider")
        self.cryptocompare_key = os.getenv('CRYPTOCOMPARE_API_KEY')  # Optional
        
        # Supported cryptocurrencies for mid/long-term trading
        self.supported_cryptos = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'ADA': 'cardano',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'MATIC': 'matic-network',
            'AVAX': 'avalanche-2',
            'LINK': 'chainlink'
        }
        
        # Rate limiter for CoinGecko (50 calls/minute)
        self.coingecko_limiter = {'tokens': 50, 'last': 0, 'rate': 50, 'per': 60}
    
    def list_symbols(self) -> List[str]:
        """Get list of supported cryptocurrency symbols"""
        return list(self.supported_cryptos.keys())
    
    def get_bars(self, symbol: str, start: str, end: str) -> List[Dict[str, Any]]:
        """
        Get price bars for cryptocurrency
        
        Args:
            symbol: Crypto symbol (BTC, ETH, etc.)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
        
        Returns:
            List of bar dictionaries with OHLCV data
        """
        # Primary: CoinGecko
        try:
            return self._get_bars_coingecko(symbol, start, end)
        except Exception as e:
            self.logger.warning(f"CoinGecko failed for {symbol}: {e}")
        
        # Backup: CryptoCompare (if API key available)
        if self.cryptocompare_key:
            try:
                return self._get_bars_cryptocompare(symbol, start, end)
            except Exception as e:
                self.logger.warning(f"CryptoCompare failed for {symbol}: {e}")
        
        self.logger.error(f"All crypto data sources failed for {symbol}")
        return []
    
    def _get_bars_coingecko(self, symbol: str, start: str, end: str) -> List[Dict[str, Any]]:
        """CoinGecko API (free, no key required, 50 calls/minute)"""
        if symbol not in self.supported_cryptos:
            raise ValueError(f"Unsupported crypto symbol: {symbol}")
        
        coin_id = self.supported_cryptos[symbol]
        
        # Check rate limit
        import time
        now = time.time()
        elapsed = now - self.coingecko_limiter['last']
        self.coingecko_limiter['tokens'] = min(
            self.coingecko_limiter['rate'],
            self.coingecko_limiter['tokens'] + int(elapsed * (self.coingecko_limiter['rate'] / self.coingecko_limiter['per']))
        )
        
        if self.coingecko_limiter['tokens'] < 1:
            sleep_time = (1 - self.coingecko_limiter['tokens']) * (self.coingecko_limiter['per'] / self.coingecko_limiter['rate'])
            time.sleep(sleep_time)
            self.coingecko_limiter['tokens'] = 0
        
        self.coingecko_limiter['tokens'] -= 1
        self.coingecko_limiter['last'] = now
        
        self.logger.debug(f"Fetching {symbol} via CoinGecko")
        
        # Convert dates to Unix timestamps
        start_ts = int(pd.to_datetime(start).timestamp())
        end_ts = int(pd.to_datetime(end).timestamp())
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        params = {
            'vs_currency': 'usd',
            'from': start_ts,
            'to': end_ts
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'prices' not in data:
            raise ValueError(f"No price data in CoinGecko response for {symbol}")
        
        bars = []
        prices = data.get('prices', [])
        market_caps = {ts: cap for ts, cap in data.get('market_caps', [])}
        volumes = {ts: vol for ts, vol in data.get('total_volumes', [])}
        
        # CoinGecko returns hourly data, we need to aggregate to daily
        daily_data = {}
        for price_point in prices:
            timestamp = price_point[0] / 1000  # Convert ms to seconds
            price = price_point[1]
            date = pd.to_datetime(timestamp, unit='s').date()
            
            if date not in daily_data:
                daily_data[date] = {
                    'prices': [],
                    'market_cap': market_caps.get(price_point[0], 0),
                    'volume': volumes.get(price_point[0], 0)
                }
            daily_data[date]['prices'].append(price)
        
        # Convert to OHLCV bars
        for date, data in sorted(daily_data.items()):
            prices_list = data['prices']
            if prices_list:
                bars.append({
                    "t": pd.to_datetime(date),
                    "o": prices_list[0],  # First price of day
                    "h": max(prices_list),
                    "l": min(prices_list),
                    "c": prices_list[-1],  # Last price of day
                    "v": int(data['volume']),
                    "vendor": "coingecko",
                    "asset_class": "crypto"
                })
        
        return sorted(bars, key=lambda x: x['t'])
    
    def _get_bars_cryptocompare(self, symbol: str, start: str, end: str) -> List[Dict[str, Any]]:
        """CryptoCompare API (free tier: 100k calls/month)"""
        if not self.cryptocompare_key:
            raise ValueError("CryptoCompare API key not configured")
        
        self.logger.debug(f"Fetching {symbol} via CryptoCompare")
        
        # CryptoCompare uses different symbol format
        symbol_map = {
            'BTC': 'BTC',
            'ETH': 'ETH',
            'BNB': 'BNB',
            'SOL': 'SOL',
            'ADA': 'ADA',
            'XRP': 'XRP',
            'DOT': 'DOT',
            'MATIC': 'MATIC',
            'AVAX': 'AVAX',
            'LINK': 'LINK'
        }
        
        if symbol not in symbol_map:
            raise ValueError(f"Unsupported crypto symbol: {symbol}")
        
        url = f"https://min-api.cryptocompare.com/data/v2/histoday"
        params = {
            'fsym': symbol,
            'tsym': 'USD',
            'limit': 2000,  # Max historical data
            'api_key': self.cryptocompare_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('Response') == 'Error':
            raise ValueError(f"CryptoCompare error: {data.get('Message', 'Unknown error')}")
        
        bars = []
        for result in data.get('Data', {}).get('Data', []):
            bar_date = pd.to_datetime(result['time'], unit='s').date()
            if start <= str(bar_date) <= end:
                bars.append({
                    "t": pd.to_datetime(result['time'], unit='s'),
                    "o": float(result['open']),
                    "h": float(result['high']),
                    "l": float(result['low']),
                    "c": float(result['close']),
                    "v": int(result['volumefrom']),  # Volume in base currency
                    "vendor": "cryptocompare",
                    "asset_class": "crypto"
                })
        
        return sorted(bars, key=lambda x: x['t'])

