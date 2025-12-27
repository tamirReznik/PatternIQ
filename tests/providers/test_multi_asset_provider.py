#!/usr/bin/env python3
"""
Tests for MultiAssetProvider
Tests ETF symbol listing, asset class detection, and multi-asset fallback
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.providers.multi_asset_provider import MultiAssetProvider


class TestMultiAssetProvider:
    """Test suite for MultiAssetProvider"""
    
    @pytest.fixture
    def provider(self):
        """Create a provider instance for testing"""
        return MultiAssetProvider(
            min_daily_volume=10_000_000,
            min_market_cap=1_000_000_000
        )
    
    def test_provider_initialization(self, provider):
        """Test provider initializes with ETF universes"""
        assert len(provider.sector_etfs) > 0
        assert len(provider.crypto_etfs) > 0
        assert len(provider.international_etfs) > 0
        assert len(provider.factor_etfs) > 0
        assert 'XLK' in provider.sector_etfs
        assert 'GBTC' in provider.crypto_etfs
    
    def test_list_symbols_includes_etfs(self, provider):
        """Test that list_symbols includes ETFs"""
        # Mock the base list_symbols to return S&P 500 symbols
        with patch.object(provider, '_get_sp500_symbols', return_value=['AAPL', 'MSFT']):
            symbols = provider.list_symbols()
            
            # Should include S&P 500 + ETFs
            assert 'AAPL' in symbols or 'MSFT' in symbols
            # Should include some ETFs
            etf_symbols = [s for s in symbols if s in provider.sector_etfs or 
                          s in provider.crypto_etfs or 
                          s in provider.international_etfs or 
                          s in provider.factor_etfs]
            assert len(etf_symbols) > 0
    
    def test_get_symbol_metadata_equity(self, provider):
        """Test symbol metadata for equity"""
        metadata = provider.get_symbol_metadata('AAPL')
        
        assert metadata['symbol'] == 'AAPL'
        assert metadata['asset_class'] == 'equity'
        assert metadata['type'] == 'Stock'
    
    def test_get_symbol_metadata_sector_etf(self, provider):
        """Test symbol metadata for sector ETF"""
        metadata = provider.get_symbol_metadata('XLK')
        
        assert metadata['symbol'] == 'XLK'
        assert metadata['asset_class'] == 'sector_etf'
        assert metadata['type'] == 'ETF'
        assert 'Technology' in metadata.get('description', '')
    
    def test_get_symbol_metadata_crypto_etf(self, provider):
        """Test symbol metadata for crypto ETF"""
        metadata = provider.get_symbol_metadata('GBTC')
        
        assert metadata['symbol'] == 'GBTC'
        assert metadata['asset_class'] == 'crypto_etf'
        assert metadata['type'] == 'ETF'
    
    @patch('src.providers.multi_asset_provider.yf.download')
    def test_get_bars_yahoo_success(self, mock_download, provider):
        """Test successful bar fetching from Yahoo Finance"""
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        mock_data = pd.DataFrame({
            'Open': [100.0] * 5,
            'High': [105.0] * 5,
            'Low': [95.0] * 5,
            'Close': [102.0] * 5,
            'Volume': [1000000] * 5
        }, index=dates)
        mock_download.return_value = mock_data
        
        bars = provider._get_bars_yahoo('AAPL', '1d', '2024-01-01', '2024-01-05')
        
        assert len(bars) == 5
        assert bars[0]['vendor'] == 'yahoo'
        assert bars[0]['asset_class'] in ['equity', 'sector_etf', 'crypto_etf', 'international_etf', 'factor_etf', 'unknown']
    
    @patch('src.providers.multi_asset_provider.yf.download')
    def test_get_bars_yahoo_empty(self, mock_download, provider):
        """Test handling of empty data from Yahoo Finance"""
        mock_download.return_value = pd.DataFrame()
        
        with pytest.raises(ValueError, match="No data returned"):
            provider._get_bars_yahoo('INVALID', '1d', '2024-01-01', '2024-01-05')
    
    @patch('src.providers.multi_asset_provider.yf.download')
    @patch('src.providers.multi_asset_provider.requests.get')
    def test_get_bars_fallback_alpha_vantage(self, mock_requests, mock_download, provider):
        """Test fallback to Alpha Vantage when Yahoo fails"""
        # Yahoo fails
        mock_download.side_effect = Exception("Yahoo Finance failed")
        
        # Alpha Vantage succeeds
        import os
        os.environ['ALPHA_VANTAGE_API_KEY'] = 'test_key'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Time Series (Daily)': {
                '2024-01-01': {
                    '1. open': '100.0',
                    '2. high': '105.0',
                    '3. low': '95.0',
                    '4. close': '102.0',
                    '6. volume': '1000000'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response
        
        bars = provider._get_bars_with_fallback('XLK', '1d', '2024-01-01', '2024-01-01')
        
        assert len(bars) == 1
        assert bars[0]['vendor'] == 'alpha_vantage'
    
    def test_validate_data_quality_multi_asset(self, provider):
        """Test data quality validation for multi-asset provider"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-02'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 1100000},
        ]
        
        report = provider._validate_data_quality('XLK', bars)
        
        assert report['status'] == 'validated'
        assert report['symbol'] == 'XLK'
        assert 'quality_score' in report

