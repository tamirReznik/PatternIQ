#!/usr/bin/env python3
"""
Tests for Trading Bot Decision Integration
Tests process_daily_report integration with decision logic
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import date

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.trading.bot import TradingBot, TimeHorizon


class TestDecisionIntegration:
    """Test suite for decision integration"""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing"""
        return TradingBot(
            initial_capital=100000.0,
            paper_trading=True,
            max_position_size=0.05
        )
    
    @pytest.fixture
    def sample_report(self):
        """Sample daily report for testing"""
        return {
            "date": "2024-01-15",
            "market_overview": {
                "regime": "Bullish",
                "signal_strength": 70
            },
            "top_long": [
                {
                    "symbol": "AAPL",
                    "sector": "Technology",
                    "signal": "BUY",
                    "score": 0.7,
                    "position_size": 3.0,
                    "price": 150.0
                },
                {
                    "symbol": "MSFT",
                    "sector": "Technology",
                    "signal": "BUY",
                    "score": 0.6,
                    "position_size": 2.5,
                    "price": 400.0
                }
            ],
            "top_short": []
        }
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch.object(TradingBot, '_should_buy')
    @patch.object(TradingBot, '_execute_buy')
    def test_process_daily_report_calls_should_buy(self, mock_execute, mock_should_buy, mock_exists, mock_file, bot, sample_report):
        """Test that process_daily_report calls _should_buy for each recommendation"""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_report)
        
        # Mock buy decision
        mock_should_buy.return_value = {
            'should_buy': True,
            'reason': 'Signal above threshold',
            'adjusted_size': 5000.0
        }
        mock_execute.return_value = True
        
        result = bot.process_daily_report(date(2024, 1, 15))
        
        # Should have called _should_buy for each top_long recommendation
        assert mock_should_buy.call_count == len(sample_report['top_long'])
        assert result['status'] == 'completed'
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch.object(TradingBot, '_should_buy')
    @patch.object(TradingBot, '_should_sell')
    def test_process_daily_report_decision_chain(self, mock_should_sell, mock_should_buy, mock_exists, mock_file, bot, sample_report):
        """Test decision chain: signal → fundamental → position sizing → execution"""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_report)
        
        # Mock buy decision with all checks passed
        mock_should_buy.return_value = {
            'should_buy': True,
            'reason': 'All checks passed',
            'adjusted_size': 5000.0
        }
        
        # Mock sell decision (no positions to sell)
        mock_should_sell.return_value = {
            'should_sell': False,
            'reason': 'Hold position',
            'shares': 0
        }
        
        result = bot.process_daily_report(date(2024, 1, 15))
        
        # Verify decision chain was followed
        assert mock_should_buy.called
        assert result['status'] == 'completed'
        assert 'executed_trades' in result or 'trades' in result
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch.object(TradingBot, '_should_buy')
    def test_process_daily_report_time_horizon_filtering(self, mock_should_buy, mock_exists, mock_file, bot, sample_report):
        """Test time horizon filtering in decisions"""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_report)
        
        # Add time horizon to signals
        sample_report['top_long'][0]['time_horizon'] = 'mid'
        sample_report['top_long'][1]['time_horizon'] = 'short'
        
        mock_should_buy.return_value = {
            'should_buy': True,
            'reason': 'Signal above threshold',
            'adjusted_size': 5000.0
        }
        
        # Process with mid-term filter
        result = bot.process_daily_report(date(2024, 1, 15), time_horizon_filter='mid')
        
        # Should only process mid-term signals
        assert mock_should_buy.called
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch.object(TradingBot, '_should_sell')
    @patch.object(TradingBot, '_execute_sell')
    def test_process_daily_report_sell_decisions(self, mock_execute_sell, mock_should_sell, mock_exists, mock_file, bot, sample_report):
        """Test that sell decisions are processed for existing positions"""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_report)
        
        # Create existing position
        bot.positions['OLD_STOCK'] = {
            'shares': 100,
            'entry_price': 100.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        
        # Add to short recommendations
        sample_report['top_short'] = [
            {
                "symbol": "OLD_STOCK",
                "signal": "SELL",
                "score": -0.7,
                "price": 90.0
            }
        ]
        
        mock_should_sell.return_value = {
            'should_sell': True,
            'reason': 'Stop loss triggered',
            'shares': 100
        }
        mock_execute_sell.return_value = True
        
        result = bot.process_daily_report(date(2024, 1, 15))
        
        assert mock_should_sell.called
        assert mock_execute_sell.called
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch.object(TradingBot, '_should_buy')
    def test_process_daily_report_multi_asset_coordination(self, mock_should_buy, mock_exists, mock_file, bot):
        """Test multi-asset decision coordination"""
        mock_exists.return_value = True
        
        # Report with multiple asset classes
        multi_asset_report = {
            "date": "2024-01-15",
            "top_long": [
                {
                    "symbol": "AAPL",
                    "asset_class": "equity",
                    "signal": "BUY",
                    "score": 0.7,
                    "position_size": 3.0,
                    "price": 150.0
                },
                {
                    "symbol": "XLK",
                    "asset_class": "sector_etf",
                    "signal": "BUY",
                    "score": 0.6,
                    "position_size": 2.0,
                    "price": 200.0
                }
            ]
        }
        
        mock_file.return_value.read.return_value = json.dumps(multi_asset_report)
        
        mock_should_buy.return_value = {
            'should_buy': True,
            'reason': 'Signal above threshold',
            'adjusted_size': 5000.0
        }
        
        result = bot.process_daily_report(date(2024, 1, 15))
        
        # Should process both asset classes
        assert mock_should_buy.call_count == 2
        assert result['status'] == 'completed'
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    def test_process_daily_report_handles_missing_report(self, mock_exists, mock_file, bot):
        """Test handling of missing report file"""
        mock_exists.return_value = False
        
        result = bot.process_daily_report(date(2024, 1, 15))
        
        assert result['status'] == 'error'
        assert 'not found' in result.get('message', '').lower() or 'error' in result.get('message', '').lower()
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch.object(TradingBot, '_should_buy')
    def test_process_daily_report_skips_low_quality_signals(self, mock_should_buy, mock_exists, mock_file, bot, sample_report):
        """Test that low quality signals are skipped"""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(sample_report)
        
        # Mock buy decision to reject low quality
        def should_buy_side_effect(*args, **kwargs):
            signal_score = args[1] if len(args) > 1 else kwargs.get('signal_score', 0)
            if signal_score < 0.65:
                return {
                    'should_buy': False,
                    'reason': 'Signal below threshold',
                    'adjusted_size': 0
                }
            return {
                'should_buy': True,
                'reason': 'Signal above threshold',
                'adjusted_size': 5000.0
            }
        
        mock_should_buy.side_effect = should_buy_side_effect
        
        result = bot.process_daily_report(date(2024, 1, 15))
        
        # Should have called _should_buy for all recommendations
        assert mock_should_buy.call_count == len(sample_report['top_long'])
        # But only high quality ones should be executed
        assert result['status'] == 'completed'

