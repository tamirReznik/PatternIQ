#!/usr/bin/env python3
"""
Tests for BackupProvider
Tests fallback mechanisms, rate limiting, and error handling
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.providers.backup_provider import BackupProvider


class TestBackupProvider:
    """Test suite for BackupProvider"""
    
    @pytest.fixture
    def provider(self):
        """Create a provider instance for testing"""
        return BackupProvider()
    
    def test_provider_initialization(self, provider):
        """Test provider initializes correctly"""
        assert provider.alpha_vantage_key is None or isinstance(provider.alpha_vantage_key, str)
        assert provider.polygon_key is None or isinstance(provider.polygon_key, str)
        assert 'tokens' in provider.alpha_vantage_limiter
        assert 'tokens' in provider.polygon_limiter
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    @patch('src.providers.backup_provider.requests.get')
    def test_alpha_vantage_success(self, mock_get, provider):
        """Test successful Alpha Vantage API call"""
        provider.alpha_vantage_key = 'test_key'
        
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
                },
                '2024-01-02': {
                    '1. open': '102.0',
                    '2. high': '107.0',
                    '3. low': '97.0',
                    '4. close': '104.0',
                    '6. volume': '1100000'
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        bars = provider._get_bars_alpha_vantage('AAPL', '2024-01-01', '2024-01-02')
        
        assert len(bars) == 2
        assert bars[0]['vendor'] == 'alpha_vantage'
        assert bars[0]['o'] == 100.0
        assert bars[0]['c'] == 102.0
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    @patch('src.providers.backup_provider.requests.get')
    def test_alpha_vantage_error_message(self, mock_get, provider):
        """Test Alpha Vantage error message handling"""
        provider.alpha_vantage_key = 'test_key'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Error Message': 'Invalid API call'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="Alpha Vantage error"):
            provider._get_bars_alpha_vantage('INVALID', '2024-01-01', '2024-01-02')
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    @patch('src.providers.backup_provider.requests.get')
    def test_alpha_vantage_rate_limit(self, mock_get, provider):
        """Test Alpha Vantage rate limit handling"""
        provider.alpha_vantage_key = 'test_key'
        provider.alpha_vantage_limiter['tokens'] = 0  # No tokens available
        
        with pytest.raises(ValueError, match="rate limit"):
            provider._get_bars_alpha_vantage('AAPL', '2024-01-01', '2024-01-02')
    
    @patch.dict(os.environ, {'POLYGON_API_KEY': 'test_key'})
    @patch('src.providers.backup_provider.requests.get')
    def test_polygon_success(self, mock_get, provider):
        """Test successful Polygon.io API call"""
        provider.polygon_key = 'test_key'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {
                    't': 1704067200000,  # 2024-01-01 in milliseconds
                    'o': 100.0,
                    'h': 105.0,
                    'l': 95.0,
                    'c': 102.0,
                    'v': 1000000
                },
                {
                    't': 1704153600000,  # 2024-01-02
                    'o': 102.0,
                    'h': 107.0,
                    'l': 97.0,
                    'c': 104.0,
                    'v': 1100000
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        bars = provider._get_bars_polygon('AAPL', '2024-01-01', '2024-01-02')
        
        assert len(bars) == 2
        assert bars[0]['vendor'] == 'polygon'
        assert bars[0]['o'] == 100.0
        assert bars[0]['c'] == 102.0
    
    @patch.dict(os.environ, {'POLYGON_API_KEY': 'test_key'})
    @patch('src.providers.backup_provider.requests.get')
    def test_polygon_error_status(self, mock_get, provider):
        """Test Polygon.io error status handling"""
        provider.polygon_key = 'test_key'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ERROR',
            'message': 'Invalid request'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="Polygon.io error"):
            provider._get_bars_polygon('INVALID', '2024-01-01', '2024-01-02')
    
    @patch.dict(os.environ, {'POLYGON_API_KEY': 'test_key'})
    def test_polygon_no_api_key(self, provider):
        """Test Polygon.io requires API key"""
        provider.polygon_key = None
        
        with pytest.raises(ValueError, match="API key not configured"):
            provider._get_bars_polygon('AAPL', '2024-01-01', '2024-01-02')
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    @patch('src.providers.backup_provider.BackupProvider._get_bars_alpha_vantage')
    @patch('src.providers.backup_provider.BackupProvider._get_bars_polygon')
    def test_get_bars_fallback_chain(self, mock_polygon, mock_alpha, provider):
        """Test fallback chain: Alpha Vantage → Polygon"""
        provider.alpha_vantage_key = 'test_key'
        provider.polygon_key = 'test_key'
        
        # Alpha Vantage fails
        mock_alpha.side_effect = Exception("Alpha Vantage failed")
        
        # Polygon succeeds
        mock_polygon.return_value = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000}
        ]
        
        bars = provider.get_bars('AAPL', '2024-01-01', '2024-01-02')
        
        assert len(bars) == 1
        assert mock_alpha.called
        assert mock_polygon.called
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    @patch('src.providers.backup_provider.BackupProvider._get_bars_alpha_vantage')
    @patch('src.providers.backup_provider.BackupProvider._get_bars_polygon')
    def test_get_bars_all_sources_fail(self, mock_polygon, mock_alpha, provider):
        """Test error when all sources fail"""
        provider.alpha_vantage_key = 'test_key'
        provider.polygon_key = 'test_key'
        
        mock_alpha.side_effect = Exception("Alpha Vantage failed")
        mock_polygon.side_effect = Exception("Polygon failed")
        
        with pytest.raises(ValueError, match="All backup sources failed"):
            provider.get_bars('AAPL', '2024-01-01', '2024-01-02')
    
    @patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'})
    @patch('src.providers.backup_provider.BackupProvider._get_bars_alpha_vantage')
    def test_get_bars_preferred_source(self, mock_alpha, provider):
        """Test using preferred source when specified"""
        provider.alpha_vantage_key = 'test_key'
        
        mock_alpha.return_value = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000}
        ]
        
        bars = provider.get_bars('AAPL', '2024-01-01', '2024-01-02', source='alpha_vantage')
        
        assert len(bars) == 1
        assert mock_alpha.called

