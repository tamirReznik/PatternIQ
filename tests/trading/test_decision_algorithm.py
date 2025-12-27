#!/usr/bin/env python3
"""
Tests for Trading Bot Decision Algorithm
Tests buy/sell decision logic, signal thresholds, position sizing, and fundamental filters
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import date

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.trading.bot import TradingBot, TimeHorizon


class TestBuyDecisionAlgorithm:
    """Test suite for buy decision logic"""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing"""
        return TradingBot(
            initial_capital=100000.0,
            paper_trading=True,
            max_position_size=0.05,
            enable_multi_asset=True
        )
    
    def test_should_buy_signal_above_threshold(self, bot):
        """Test buy when signal above threshold"""
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.7,  # Above mid-term threshold (0.5)
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        assert decision['should_buy'] == True
        assert decision['adjusted_size'] > 0
    
    def test_should_buy_signal_below_threshold(self, bot):
        """Test reject when signal below threshold"""
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.3,  # Below mid-term threshold (0.5)
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        assert decision['should_buy'] == False
        assert 'below threshold' in decision['reason'].lower()
        assert decision['adjusted_size'] == 0
    
    def test_should_buy_different_time_horizon_thresholds(self, bot):
        """Test different thresholds for short/mid/long-term"""
        # Short-term: higher threshold (0.6)
        decision_short = bot._should_buy(
            symbol='AAPL',
            signal_score=0.55,  # Below short-term threshold
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.SHORT,
            asset_class='equity'
        )
        assert decision_short['should_buy'] == False
        
        # Mid-term: medium threshold (0.5)
        decision_mid = bot._should_buy(
            symbol='AAPL',
            signal_score=0.55,  # Above mid-term threshold
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        assert decision_mid['should_buy'] == True
        
        # Long-term: lower threshold (0.4)
        decision_long = bot._should_buy(
            symbol='AAPL',
            signal_score=0.45,  # Above long-term threshold
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.LONG,
            asset_class='equity'
        )
        assert decision_long['should_buy'] == True
    
    def test_should_buy_minimum_trade_size(self, bot):
        """Test minimum trade size enforcement"""
        # Equity: $1000 minimum
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.7,
            price=150.0,
            target_dollars=500.0,  # Below $1000 minimum
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        assert decision['should_buy'] == False
        assert 'below minimum' in decision['reason'].lower()
        
        # ETF: $500 minimum
        decision_etf = bot._should_buy(
            symbol='XLK',
            signal_score=0.7,
            price=100.0,
            target_dollars=300.0,  # Below $500 minimum
            time_horizon=TimeHorizon.MID,
            asset_class='sector_etf'
        )
        
        assert decision_etf['should_buy'] == False
    
    def test_should_buy_position_count_limit(self, bot):
        """Test position count limit enforcement"""
        # Fill up positions to max
        bot.max_positions = 5
        for i in range(5):
            bot.positions[f'SYMBOL{i}'] = {
                'shares': 100,
                'entry_price': 100.0,
                'asset_class': 'equity',
                'time_horizon': 'mid'
            }
        
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.7,
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        assert decision['should_buy'] == False
        assert 'max' in decision['reason'].lower() or 'limit' in decision['reason'].lower()
    
    @patch.object(TradingBot, '_get_fundamentals_score')
    def test_should_buy_fundamental_filter_equity(self, mock_fundamentals, bot):
        """Test fundamental filter for equity"""
        # Poor fundamentals
        mock_fundamentals.return_value = 0.3  # Below 0.4 threshold
        
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.7,
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        assert decision['should_buy'] == False
        assert 'fundamentals' in decision['reason'].lower()
        
        # Good fundamentals
        mock_fundamentals.return_value = 0.6  # Above 0.4 threshold
        
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.7,
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        assert decision['should_buy'] == True
    
    def test_should_buy_asset_allocation_limit(self, bot):
        """Test asset class allocation limits"""
        # Fill up equity allocation
        bot.asset_allocation['equity'] = 0.05  # 5% max
        bot.positions['EQUITY1'] = {
            'shares': 1000,
            'entry_price': 100.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        bot.cash_balance = 50000.0  # Set cash for portfolio value calculation
        
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.7,
            price=150.0,
            target_dollars=5000.0,  # Would exceed 5% allocation
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        # Should reject or adjust size
        assert decision['should_buy'] == False or decision['adjusted_size'] < target_dollars
    
    def test_should_buy_insufficient_cash(self, bot):
        """Test buy when insufficient cash"""
        bot.cash_balance = 500.0  # Less than target
        
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.7,
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        assert decision['should_buy'] == False
        assert 'insufficient cash' in decision['reason'].lower() or 'cash' in decision['reason'].lower()
    
    def test_should_buy_adjusted_size_when_partial_cash(self, bot):
        """Test adjusted size when cash partially available"""
        bot.cash_balance = 3000.0  # Partial cash
        
        decision = bot._should_buy(
            symbol='AAPL',
            signal_score=0.7,
            price=150.0,
            target_dollars=5000.0,
            time_horizon=TimeHorizon.MID,
            asset_class='equity'
        )
        
        # Should adjust size to available cash
        if decision['should_buy']:
            assert decision['adjusted_size'] <= 3000.0
            assert decision['adjusted_size'] >= 1000.0  # Above minimum


class TestSellDecisionAlgorithm:
    """Test suite for sell decision logic"""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing"""
        return TradingBot(
            initial_capital=100000.0,
            paper_trading=True,
            max_position_size=0.05
        )
    
    def test_should_sell_stop_loss_triggered(self, bot):
        """Test sell when stop loss triggered"""
        # Create a losing position (15% loss, stop loss is -10% for mid-term)
        bot.positions['AAPL'] = {
            'shares': 100,
            'entry_price': 150.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        
        decision = bot._should_sell('AAPL', current_price=127.5)  # 15% loss
        
        assert decision['should_sell'] == True
        assert 'stop loss' in decision['reason'].lower()
        assert decision['shares'] == 100
    
    def test_should_sell_take_profit_triggered(self, bot):
        """Test sell when take profit triggered"""
        # Create a winning position (25% gain, take profit is 20% for mid-term)
        bot.positions['AAPL'] = {
            'shares': 100,
            'entry_price': 150.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        
        decision = bot._should_sell('AAPL', current_price=187.5)  # 25% gain
        
        assert decision['should_sell'] == True
        assert 'take profit' in decision['reason'].lower() or 'profit' in decision['reason'].lower()
        assert decision['shares'] == 100
    
    def test_should_sell_different_time_horizon_stop_loss(self, bot):
        """Test different stop loss for short/mid/long-term"""
        # Short-term: -5% stop loss
        bot.positions['SHORT'] = {
            'shares': 100,
            'entry_price': 100.0,
            'asset_class': 'equity',
            'time_horizon': 'short'
        }
        decision = bot._should_sell('SHORT', current_price=94.0)  # 6% loss
        assert decision['should_sell'] == True
        
        # Mid-term: -10% stop loss
        bot.positions['MID'] = {
            'shares': 100,
            'entry_price': 100.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        decision = bot._should_sell('MID', current_price=91.0)  # 9% loss (should hold)
        assert decision['should_sell'] == False
        
        decision = bot._should_sell('MID', current_price=89.0)  # 11% loss (should sell)
        assert decision['should_sell'] == True
        
        # Long-term: -15% stop loss
        bot.positions['LONG'] = {
            'shares': 100,
            'entry_price': 100.0,
            'asset_class': 'equity',
            'time_horizon': 'long'
        }
        decision = bot._should_sell('LONG', current_price=86.0)  # 14% loss (should hold)
        assert decision['should_sell'] == False
    
    def test_should_sell_strong_negative_signal(self, bot):
        """Test sell when strong negative signal"""
        bot.positions['AAPL'] = {
            'shares': 100,
            'entry_price': 150.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        
        # Strong negative signal for equity (threshold is -0.6)
        decision = bot._should_sell('AAPL', current_price=150.0, signal_score=-0.7)
        
        assert decision['should_sell'] == True
        assert 'signal' in decision['reason'].lower()
    
    def test_should_sell_hold_on_weak_signal(self, bot):
        """Test hold when signal not strong enough"""
        bot.positions['AAPL'] = {
            'shares': 100,
            'entry_price': 150.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        
        # Weak negative signal (above -0.6 threshold)
        decision = bot._should_sell('AAPL', current_price=150.0, signal_score=-0.4)
        
        assert decision['should_sell'] == False
        assert 'hold' in decision['reason'].lower() or decision['reason'] == 'Hold position'
    
    @patch.object(TradingBot, '_get_fundamentals_score')
    def test_should_sell_fundamental_deterioration(self, mock_fundamentals, bot):
        """Test sell when fundamentals deteriorate"""
        bot.positions['AAPL'] = {
            'shares': 100,
            'entry_price': 150.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        
        # Deteriorating fundamentals (below 0.3 threshold)
        mock_fundamentals.return_value = 0.2
        
        decision = bot._should_sell('AAPL', current_price=150.0)
        
        assert decision['should_sell'] == True
        assert 'fundamentals' in decision['reason'].lower()
        
        # Acceptable fundamentals
        mock_fundamentals.return_value = 0.5
        
        decision = bot._should_sell('AAPL', current_price=150.0)
        
        assert decision['should_sell'] == False
    
    def test_should_sell_not_in_portfolio(self, bot):
        """Test sell when symbol not in portfolio"""
        decision = bot._should_sell('NOT_IN_PORTFOLIO', current_price=100.0)
        
        assert decision['should_sell'] == False
        assert 'not in portfolio' in decision['reason'].lower()
    
    def test_should_sell_asset_class_specific_thresholds(self, bot):
        """Test asset-class specific signal thresholds"""
        # Crypto ETF: lower threshold (-0.3)
        bot.positions['GBTC'] = {
            'shares': 100,
            'entry_price': 50.0,
            'asset_class': 'crypto_etf',
            'time_horizon': 'mid'
        }
        
        decision = bot._should_sell('GBTC', current_price=50.0, signal_score=-0.35)
        assert decision['should_sell'] == True
        
        # Equity: higher threshold (-0.6)
        bot.positions['AAPL'] = {
            'shares': 100,
            'entry_price': 150.0,
            'asset_class': 'equity',
            'time_horizon': 'mid'
        }
        
        decision = bot._should_sell('AAPL', current_price=150.0, signal_score=-0.35)
        assert decision['should_sell'] == False  # Not strong enough for equity

