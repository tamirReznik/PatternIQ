#!/usr/bin/env python3
"""
Tests for SP500Provider
Tests data fetching, filtering, caching, and fallback mechanisms
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.providers.sp500_provider import SP500Provider, RateLimiter


class TestSP500Provider:
    """Test suite for SP500Provider"""
    
    @pytest.fixture
    def provider(self):
        """Create a provider instance for testing"""
        return SP500Provider(
            min_daily_volume=10_000_000,
            min_market_cap=1_000_000_000,
            min_days_listed=90
        )
    
    @pytest.fixture
    def mock_yfinance_data(self):
        """Mock yfinance data"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        return pd.DataFrame({
            'Open': [100.0] * 10,
            'High': [105.0] * 10,
            'Low': [95.0] * 10,
            'Close': [102.0] * 10,
            'Volume': [1000000] * 10
        }, index=dates)
    
    def test_provider_initialization(self, provider):
        """Test provider initializes with correct filters"""
        assert provider.min_daily_volume == 10_000_000
        assert provider.min_market_cap == 1_000_000_000
        assert provider.min_days_listed == 90
        assert provider._symbol_cache == {}
        assert provider._cache_ttl == 86400
    
    @patch('src.providers.sp500_provider.requests.get')
    def test_get_symbols_basic(self, mock_get, provider):
        """Test fetching S&P 500 symbols from Wikipedia"""
        # Mock Wikipedia response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <table id="constituents">
        <tr><td>AAPL</td></tr>
        <tr><td>MSFT</td></tr>
        <tr><td>GOOGL</td></tr>
        </table>
        """
        mock_get.return_value = mock_response
        
        symbols = provider._get_symbols_basic()
        assert len(symbols) == 3
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'GOOGL' in symbols
    
    @patch('src.providers.sp500_provider.requests.get')
    def test_get_symbols_fallback(self, mock_get, provider):
        """Test fallback to static list when Wikipedia fails"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        symbols = provider._get_symbols_basic()
        assert len(symbols) > 0
        assert 'AAPL' in symbols  # Should be in fallback list
    
    @patch('src.providers.sp500_provider.yf.download')
    def test_get_bars_yahoo_success(self, mock_download, provider, mock_yfinance_data):
        """Test successful bar fetching from Yahoo Finance"""
        mock_download.return_value = mock_yfinance_data
        
        bars = provider._get_bars_yahoo('AAPL', '1d', '2024-01-01', '2024-01-10')
        
        assert len(bars) == 10
        assert bars[0]['vendor'] == 'yahoo'
        assert bars[0]['o'] == 100.0
        assert bars[0]['c'] == 102.0
        assert bars[0]['v'] == 1000000
    
    @patch('src.providers.sp500_provider.yf.download')
    def test_get_bars_yahoo_empty(self, mock_download, provider):
        """Test handling of empty data from Yahoo Finance"""
        mock_download.return_value = pd.DataFrame()
        
        with pytest.raises(ValueError, match="No data returned"):
            provider._get_bars_yahoo('INVALID', '1d', '2024-01-01', '2024-01-10')
    
    @patch('src.providers.sp500_provider.yf.download')
    @patch('src.providers.sp500_provider.requests.get')
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
        
        bars = provider._get_bars_with_fallback('AAPL', '1d', '2024-01-01', '2024-01-01')
        
        assert len(bars) == 1
        assert bars[0]['vendor'] == 'alpha_vantage'
    
    def test_validate_data_quality_good_data(self, provider):
        """Test quality validation with good data"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-02'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 1100000},
            {'t': pd.Timestamp('2024-01-03'), 'o': 104.0, 'h': 109.0, 'l': 99.0, 'c': 106.0, 'v': 1200000},
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        assert report['status'] == 'validated'
        assert report['quality_score'] >= 70
        assert len(report['issues']) == 0
    
    def test_validate_data_quality_date_gaps(self, provider):
        """Test quality validation detects date gaps"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-10'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 1100000},  # 9 day gap
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        assert report['status'] == 'validated'
        assert len(report['issues']) > 0
        assert any('gap' in issue.lower() for issue in report['issues'])
    
    def test_validate_data_quality_invalid_prices(self, provider):
        """Test quality validation detects invalid prices"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 0.0, 'v': 1000000},  # Invalid close
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        assert len(report['issues']) > 0
        assert any('invalid' in issue.lower() for issue in report['issues'])
    
    def test_validate_data_quality_volume_spikes(self, provider):
        """Test quality validation detects volume spikes"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-02'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 15000000},  # 15x spike
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        assert len(report['issues']) > 0
        assert any('volume' in issue.lower() for issue in report['issues'])
    
    @patch('src.providers.sp500_provider.yf.Ticker')
    def test_get_symbol_metadata(self, mock_ticker, provider):
        """Test symbol metadata retrieval"""
        # Mock ticker info
        mock_info = {
            'marketCap': 2_000_000_000_000,
            'sector': 'Technology',
            'industry': 'Software'
        }
        
        # Mock history
        mock_hist = pd.DataFrame({
            'Close': [150.0] * 60,
            'Volume': [10_000_000] * 60
        }, index=pd.date_range('2024-01-01', periods=60, freq='D'))
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_info
        mock_ticker_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_ticker_instance
        
        metadata = provider._get_symbol_metadata('AAPL')
        
        assert metadata['symbol'] == 'AAPL'
        assert metadata['market_cap'] == 2_000_000_000_000
        assert metadata['avg_daily_volume'] > 0
        assert metadata['days_listed'] == 60
    
    @patch('src.providers.sp500_provider.SP500Provider._get_symbol_metadata')
    def test_filter_by_volume_and_quality(self, mock_metadata, provider):
        """Test volume and quality filtering"""
        # Mock metadata for different symbols
        def metadata_side_effect(symbol):
            if symbol == 'AAPL':
                return {
                    'symbol': 'AAPL',
                    'market_cap': 2_000_000_000_000,
                    'avg_daily_volume': 50_000_000,  # Above threshold
                    'days_listed': 100
                }
            elif symbol == 'SMALL':
                return {
                    'symbol': 'SMALL',
                    'market_cap': 500_000_000,  # Below threshold
                    'avg_daily_volume': 5_000_000,  # Below threshold
                    'days_listed': 50  # Below threshold
                }
            else:
                return {
                    'symbol': symbol,
                    'market_cap': 1_500_000_000,
                    'avg_daily_volume': 15_000_000,
                    'days_listed': 100
                }
        
        mock_metadata.side_effect = metadata_side_effect
        
        symbols = ['AAPL', 'SMALL', 'MSFT']
        filtered = provider._filter_by_volume_and_quality(symbols)
        
        assert 'AAPL' in filtered
        assert 'MSFT' in filtered
        assert 'SMALL' not in filtered  # Should be filtered out
    
    def test_symbol_metadata_caching(self, provider):
        """Test symbol metadata is cached"""
        with patch.object(provider, '_get_symbol_metadata') as mock_metadata:
            mock_metadata.return_value = {
                'symbol': 'AAPL',
                'market_cap': 2_000_000_000_000,
                'avg_daily_volume': 50_000_000,
                'days_listed': 100
            }
            
            # First call
            provider._filter_by_volume_and_quality(['AAPL'])
            assert mock_metadata.call_count == 1
            
            # Second call should use cache
            provider._filter_by_volume_and_quality(['AAPL'])
            assert mock_metadata.call_count == 1  # Still 1, used cache
    
    def test_rate_limiter(self):
        """Test rate limiter functionality"""
        limiter = RateLimiter(rate=10, per=60)
        
        # First 10 calls should succeed immediately
        for i in range(10):
            assert limiter.acquire() == True
        
        # 11th call should wait
        import time
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        assert elapsed > 0  # Should have waited

