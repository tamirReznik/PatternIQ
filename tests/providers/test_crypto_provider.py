#!/usr/bin/env python3
"""
Tests for CryptoProvider
Tests CoinGecko integration, CryptoCompare fallback, and crypto symbol listing
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.providers.crypto_provider import CryptoProvider


class TestCryptoProvider:
    """Test suite for CryptoProvider"""
    
    @pytest.fixture
    def provider(self):
        """Create a provider instance for testing"""
        return CryptoProvider()
    
    def test_provider_initialization(self, provider):
        """Test provider initializes with supported cryptos"""
        assert len(provider.supported_cryptos) > 0
        assert 'BTC' in provider.supported_cryptos
        assert 'ETH' in provider.supported_cryptos
        assert provider.supported_cryptos['BTC'] == 'bitcoin'
    
    def test_list_symbols(self, provider):
        """Test listing supported crypto symbols"""
        symbols = provider.list_symbols()
        
        assert len(symbols) > 0
        assert 'BTC' in symbols
        assert 'ETH' in symbols
        assert all(s in provider.supported_cryptos for s in symbols)
    
    @patch('src.providers.crypto_provider.requests.get')
    def test_get_bars_coingecko_success(self, mock_get, provider):
        """Test successful CoinGecko API call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'prices': [
                [1704067200000, 42000.0],  # 2024-01-01 00:00
                [1704070800000, 42100.0],  # 2024-01-01 01:00
                [1704074400000, 42200.0],  # 2024-01-01 02:00
                [1704153600000, 43000.0],  # 2024-01-02 00:00
            ],
            'market_caps': [
                [1704067200000, 800000000000],
                [1704153600000, 810000000000]
            ],
            'total_volumes': [
                [1704067200000, 20000000000],
                [1704153600000, 21000000000]
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        bars = provider._get_bars_coingecko('BTC', '2024-01-01', '2024-01-02')
        
        assert len(bars) > 0
        assert bars[0]['vendor'] == 'coingecko'
        assert bars[0]['asset_class'] == 'crypto'
        assert bars[0]['o'] > 0
        assert bars[0]['c'] > 0
    
    @patch('src.providers.crypto_provider.requests.get')
    def test_get_bars_coingecko_no_prices(self, mock_get, provider):
        """Test CoinGecko handles missing price data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'prices': []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="No price data"):
            provider._get_bars_coingecko('BTC', '2024-01-01', '2024-01-02')
    
    def test_get_bars_coingecko_unsupported_symbol(self, provider):
        """Test CoinGecko rejects unsupported symbols"""
        with pytest.raises(ValueError, match="Unsupported crypto symbol"):
            provider._get_bars_coingecko('UNKNOWN', '2024-01-01', '2024-01-02')
    
    @patch.dict(os.environ, {'CRYPTOCOMPARE_API_KEY': 'test_key'})
    @patch('src.providers.crypto_provider.requests.get')
    def test_get_bars_cryptocompare_success(self, mock_get, provider):
        """Test successful CryptoCompare API call"""
        provider.cryptocompare_key = 'test_key'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Response': 'Success',
            'Data': {
                'Data': [
                    {
                        'time': 1704067200,  # 2024-01-01
                        'open': 42000.0,
                        'high': 42500.0,
                        'low': 41500.0,
                        'close': 42200.0,
                        'volumefrom': 20000000000
                    },
                    {
                        'time': 1704153600,  # 2024-01-02
                        'open': 42200.0,
                        'high': 42700.0,
                        'low': 41700.0,
                        'close': 42400.0,
                        'volumefrom': 21000000000
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        bars = provider._get_bars_cryptocompare('BTC', '2024-01-01', '2024-01-02')
        
        assert len(bars) == 2
        assert bars[0]['vendor'] == 'cryptocompare'
        assert bars[0]['asset_class'] == 'crypto'
        assert bars[0]['o'] == 42000.0
    
    @patch.dict(os.environ, {'CRYPTOCOMPARE_API_KEY': 'test_key'})
    @patch('src.providers.crypto_provider.requests.get')
    def test_get_bars_cryptocompare_error(self, mock_get, provider):
        """Test CryptoCompare error handling"""
        provider.cryptocompare_key = 'test_key'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Response': 'Error',
            'Message': 'Invalid request'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="CryptoCompare error"):
            provider._get_bars_cryptocompare('BTC', '2024-01-01', '2024-01-02')
    
    @patch('src.providers.crypto_provider.CryptoProvider._get_bars_coingecko')
    @patch('src.providers.crypto_provider.CryptoProvider._get_bars_cryptocompare')
    def test_get_bars_fallback_chain(self, mock_cryptocompare, mock_coingecko, provider):
        """Test fallback chain: CoinGecko → CryptoCompare"""
        # CoinGecko fails
        mock_coingecko.side_effect = Exception("CoinGecko failed")
        
        # CryptoCompare succeeds
        provider.cryptocompare_key = 'test_key'
        mock_cryptocompare.return_value = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 42000.0, 'h': 42500.0, 'l': 41500.0, 'c': 42200.0, 'v': 20000000000, 'vendor': 'cryptocompare', 'asset_class': 'crypto'}
        ]
        
        bars = provider.get_bars('BTC', '2024-01-01', '2024-01-02')
        
        assert len(bars) == 1
        assert mock_coingecko.called
        assert mock_cryptocompare.called

