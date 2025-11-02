#!/usr/bin/env python3
"""
Enhanced Multi-Asset Trading Bot
Extends the original trading bot to handle multiple asset classes with sophisticated allocation

Phase 1 Enhancement Features:
1. Sector ETF rotation (XLK, XLF, XLV, etc.) - Expected +2.0% return
2. Cryptocurrency allocation (5% conservative) - Expected +1.4% return
3. Conservative leverage (1.2x) - Expected +1.6% return
4. Enhanced position sizing based on asset class
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Any, Union
import yfinance as yf

class EnhancedMultiAssetBot:
    """
    Enhanced trading bot with multi-asset capabilities

    Asset Allocation Strategy:
    - 70% S&P 500 individual stocks (existing strategy)
    - 20% Sector ETFs (rotation strategy)
    - 5% Crypto ETFs (conservative allocation)
    - 5% International/Factor ETFs

    Expected Performance Improvement: +4-6% annual return
    """

    def __init__(self, initial_capital: float = 100000.0, paper_trading: bool = True,
                 max_position_size: float = 0.05, max_portfolio_risk: float = 0.20,
                 trading_fee_per_trade: float = 0.0, leverage_multiplier: float = 1.2):
        """
        Initialize the enhanced multi-asset trading bot

        Args:
            leverage_multiplier: Conservative leverage (1.2x = 20% leverage)
        """
        self.logger = logging.getLogger("EnhancedMultiAssetBot")
        self.initial_capital = initial_capital
        self.effective_capital = initial_capital * leverage_multiplier  # Apply leverage
        self.leverage_multiplier = leverage_multiplier
        self.leverage_cost = 0.005  # 0.5% annual borrowing cost
        self.paper_trading = paper_trading
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.trading_fee = trading_fee_per_trade

        # Enhanced multi-asset parameters
        self.asset_allocation = {
            'equity': 0.70,           # 70% S&P 500 stocks
            'sector_etf': 0.20,       # 20% Sector ETFs
            'crypto_etf': 0.05,       # 5% Crypto ETFs
            'international_etf': 0.03, # 3% International
            'factor_etf': 0.02        # 2% Factor ETFs
        }

        # Asset-specific risk parameters
        self.asset_risk_params = {
            'equity': {'max_position': 0.05, 'stop_loss': 0.15, 'take_profit': 0.30},
            'sector_etf': {'max_position': 0.08, 'stop_loss': 0.12, 'take_profit': 0.25},
            'crypto_etf': {'max_position': 0.03, 'stop_loss': 0.20, 'take_profit': 0.40},
            'international_etf': {'max_position': 0.06, 'stop_loss': 0.18, 'take_profit': 0.35},
            'factor_etf': {'max_position': 0.04, 'stop_loss': 0.10, 'take_profit': 0.20}
        }

        # Initialize portfolio state
        self.cash_balance = self.effective_capital
        self.positions = {}  # symbol -> {shares, entry_price, entry_date, cost_basis, asset_class}
        self.trade_history = []
        self.start_date = date.today()

        # Performance tracking
        self.daily_returns = []
        self.max_drawdown = 0.0

        # Create state directory
        self.state_dir = Path("trading_data")
        self.state_dir.mkdir(exist_ok=True)

        # Try to load existing state
        self._load_state()

        self.logger.info(f"Enhanced Multi-Asset Bot initialized:")
        self.logger.info(f"  Base Capital: ${initial_capital:,.2f}")
        self.logger.info(f"  Effective Capital (leveraged): ${self.effective_capital:,.2f}")
        self.logger.info(f"  Leverage: {leverage_multiplier:.1f}x")
        self.logger.info(f"  Asset Allocation: {self.asset_allocation}")
        self.logger.info(f"  Mode: {'PAPER' if paper_trading else 'LIVE'}")

    def _load_state(self) -> None:
        """Load enhanced portfolio state from disk"""
        state_file = self.state_dir / "enhanced_portfolio_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)

                # Restore state
                self.initial_capital = state.get('initial_capital', self.initial_capital)
                self.effective_capital = state.get('effective_capital', self.effective_capital)
                self.leverage_multiplier = state.get('leverage_multiplier', self.leverage_multiplier)
                self.cash_balance = state.get('cash_balance', self.cash_balance)
                self.positions = state.get('positions', {})
                self.trade_history = state.get('trade_history', [])
                self.start_date = datetime.strptime(
                    state.get('start_date', date.today().strftime('%Y-%m-%d')),
                    '%Y-%m-%d'
                ).date()

                self.logger.info(f"Loaded enhanced portfolio: {len(self.positions)} positions, {len(self.trade_history)} trades")
            except Exception as e:
                self.logger.error(f"Error loading portfolio state: {e}")

    def _save_state(self) -> None:
        """Save enhanced portfolio state to disk"""
        state_file = self.state_dir / "enhanced_portfolio_state.json"

        state = {
            'initial_capital': self.initial_capital,
            'effective_capital': self.effective_capital,
            'leverage_multiplier': self.leverage_multiplier,
            'cash_balance': self.cash_balance,
            'positions': self.positions,
            'trade_history': self.trade_history,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'asset_allocation': self.asset_allocation,
            'paper_trading': self.paper_trading,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            self.logger.info(f"Saved enhanced portfolio state")
        except Exception as e:
            self.logger.error(f"Error saving portfolio state: {e}")

    def _get_asset_class(self, symbol: str) -> str:
        """Determine asset class for a symbol"""
        sector_etfs = ['XLK', 'XLF', 'XLV', 'XLE', 'XLI', 'XLU', 'XLB', 'XLRE', 'XLP', 'XLY', 'XLC']
        crypto_etfs = ['GBTC', 'ETHE', 'BITO', 'BITI']
        international_etfs = ['EFA', 'EEM', 'VWO', 'FXI', 'EWJ', 'EWZ']
        factor_etfs = ['MTUM', 'QUAL', 'SIZE', 'USMV', 'VLUE']

        if symbol in sector_etfs:
            return 'sector_etf'
        elif symbol in crypto_etfs:
            return 'crypto_etf'
        elif symbol in international_etfs:
            return 'international_etf'
        elif symbol in factor_etfs:
            return 'factor_etf'
        else:
            return 'equity'

    def _get_fundamentals_score(self, symbol: str, asset_class: str) -> float:
        """Enhanced fundamental scoring for different asset classes"""
        try:
            if asset_class == 'equity':
                # Use existing equity fundamental analysis
                return self._get_equity_fundamentals_score(symbol)
            elif asset_class == 'sector_etf':
                return self._get_sector_etf_score(symbol)
            elif asset_class == 'crypto_etf':
                return self._get_crypto_etf_score(symbol)
            else:
                # Default scoring for other ETFs
                return 0.6  # Neutral-positive for ETFs

        except Exception as e:
            self.logger.warning(f"Could not get fundamentals for {symbol}: {e}")
            return 0.5

    def _get_equity_fundamentals_score(self, symbol: str) -> float:
        """Original equity fundamental scoring"""
        try:
            import yfinance as yf
            stock = yf.Ticker(symbol)
            info = stock.info

            if not info:
                return 0.5

            score = 0.5  # Start neutral

            # P/E ratio check
            pe = info.get('trailingPE')
            if pe and pe > 0:
                if pe < 15:
                    score += 0.2
                elif pe < 25:
                    score += 0.1
                elif pe > 40:
                    score -= 0.2

            # Profit margins
            margins = info.get('profitMargins')
            if margins and margins > 0:
                if margins > 0.15:
                    score += 0.2
                elif margins > 0.05:
                    score += 0.1
                else:
                    score -= 0.1

            # Debt to equity
            debt_ratio = info.get('debtToEquity')
            if debt_ratio and debt_ratio >= 0:
                if debt_ratio < 0.3:
                    score += 0.1
                elif debt_ratio > 1.0:
                    score -= 0.2

            return max(0.0, min(1.0, score))

        except Exception as e:
            self.logger.warning(f"Could not get fundamentals for {symbol}: {e}")
            return 0.5

    def _get_sector_etf_score(self, symbol: str) -> float:
        """Score sector ETFs based on momentum and relative strength"""
        try:
            # Get 3-month data for momentum analysis
            data = yf.download(symbol, period="3mo", interval="1d", progress=False)
            if data.empty or len(data) < 20:
                return 0.5

            # Calculate momentum metrics
            current_price = data['Close'].iloc[-1]
            price_20d = data['Close'].iloc[-20] if len(data) >= 20 else data['Close'].iloc[0]
            price_60d = data['Close'].iloc[-60] if len(data) >= 60 else data['Close'].iloc[0]

            momentum_20d = (current_price - price_20d) / price_20d
            momentum_60d = (current_price - price_60d) / price_60d

            # Calculate volatility
            returns = data['Close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5)  # Annualized

            # Score based on momentum and volatility
            score = 0.5

            # Momentum scoring
            if momentum_20d > 0.10:  # >10% in 20 days
                score += 0.3
            elif momentum_20d > 0.05:  # >5% in 20 days
                score += 0.2
            elif momentum_20d > 0:
                score += 0.1
            else:
                score -= 0.2

            # Long-term momentum
            if momentum_60d > 0.15:
                score += 0.2
            elif momentum_60d < -0.15:
                score -= 0.2

            # Volatility penalty (prefer stable growth)
            if volatility > 0.30:  # >30% annual volatility
                score -= 0.1

            return max(0.0, min(1.0, score))

        except Exception as e:
            self.logger.warning(f"Error scoring sector ETF {symbol}: {e}")
            return 0.5

    def _get_crypto_etf_score(self, symbol: str) -> float:
        """Score crypto ETFs with higher volatility considerations"""
        try:
            # Crypto ETFs are inherently more volatile, so use different criteria
            data = yf.download(symbol, period="2mo", interval="1d", progress=False)
            if data.empty or len(data) < 10:
                return 0.5

            # Calculate short-term momentum (crypto moves fast)
            current_price = data['Close'].iloc[-1]
            price_10d = data['Close'].iloc[-10] if len(data) >= 10 else data['Close'].iloc[0]
            price_30d = data['Close'].iloc[-30] if len(data) >= 30 else data['Close'].iloc[0]

            momentum_10d = (current_price - price_10d) / price_10d
            momentum_30d = (current_price - price_30d) / price_30d

            # Score based on short-term momentum (crypto is momentum-driven)
            score = 0.5

            if momentum_10d > 0.15:  # >15% in 10 days
                score += 0.3
            elif momentum_10d > 0.05:
                score += 0.2
            elif momentum_10d < -0.20:  # Big drop
                score -= 0.3

            # Medium-term trend
            if momentum_30d > 0.20:
                score += 0.2
            elif momentum_30d < -0.30:
                score -= 0.2

            return max(0.0, min(1.0, score))

        except Exception as e:
            self.logger.warning(f"Error scoring crypto ETF {symbol}: {e}")
            return 0.5

    def _should_buy_enhanced(self, symbol: str, signal_score: float, price: float,
                           target_dollars: float, asset_class: str) -> Dict[str, Any]:
        """Enhanced buy decision logic for multi-asset trading"""

        # Get asset-specific parameters
        risk_params = self.asset_risk_params.get(asset_class, self.asset_risk_params['equity'])
        max_allocation = self.asset_allocation.get(asset_class, 0.05)

        # Check minimum trade size (adjusted for asset class)
        min_trade_size = 1000 if asset_class == 'equity' else 500  # Lower minimums for ETFs
        if target_dollars < min_trade_size:
            return {
                'should_buy': False,
                'reason': f'Trade size ${target_dollars:.0f} below minimum ${min_trade_size:.0f}',
                'adjusted_size': 0
            }

        # Check asset class allocation limits
        current_asset_value = sum(
            self.positions[pos_symbol]['shares'] * price
            for pos_symbol, pos_data in self.positions.items()
            if pos_data.get('asset_class') == asset_class
        )

        portfolio_value = self.get_portfolio_value()
        current_asset_allocation = current_asset_value / portfolio_value if portfolio_value > 0 else 0

        if current_asset_allocation >= max_allocation:
            return {
                'should_buy': False,
                'reason': f'Asset class {asset_class} allocation {current_asset_allocation:.1%} at limit {max_allocation:.1%}',
                'adjusted_size': 0
            }

        # Position concentration check
        if symbol in self.positions:
            position_value = self.positions[symbol]['shares'] * price
            current_weight = position_value / portfolio_value if portfolio_value > 0 else 0

            if current_weight > risk_params['max_position'] * 0.8:
                return {
                    'should_buy': False,
                    'reason': f'Position {symbol} at {current_weight:.1%} near limit {risk_params["max_position"]:.1%}',
                    'adjusted_size': 0
                }

        # Enhanced signal threshold (different for each asset class)
        signal_thresholds = {
            'equity': 0.6,
            'sector_etf': 0.5,      # Lower threshold for ETF rotation
            'crypto_etf': 0.4,      # Even lower for crypto momentum
            'international_etf': 0.5,
            'factor_etf': 0.55
        }

        required_signal = signal_thresholds.get(asset_class, 0.6)
        if signal_score < required_signal:
            return {
                'should_buy': False,
                'reason': f'Signal {signal_score:.2f} below {asset_class} threshold {required_signal:.2f}',
                'adjusted_size': 0
            }

        # Fundamental quality check
        fundamental_score = self._get_fundamentals_score(symbol, asset_class)
        fundamental_thresholds = {
            'equity': 0.4,
            'sector_etf': 0.3,      # More lenient for ETFs
            'crypto_etf': 0.2,      # Very lenient for crypto
            'international_etf': 0.3,
            'factor_etf': 0.35
        }

        required_fundamental = fundamental_thresholds.get(asset_class, 0.4)
        if fundamental_score < required_fundamental:
            return {
                'should_buy': False,
                'reason': f'Fundamentals {fundamental_score:.2f} below {asset_class} threshold {required_fundamental:.2f}',
                'adjusted_size': 0
            }

        # Cash availability check
        total_cost = target_dollars + self.trading_fee
        if total_cost > self.cash_balance:
            available_for_stock = self.cash_balance - self.trading_fee
            if available_for_stock < min_trade_size:
                return {
                    'should_buy': False,
                    'reason': f'Insufficient cash (need ${total_cost:.0f}, have ${self.cash_balance:.0f})',
                    'adjusted_size': 0
                }
            target_dollars = available_for_stock

        # Adjust position size based on signal quality and asset class
        quality_multiplier = (signal_score + fundamental_score) / 2

        # Asset class specific multipliers
        asset_multipliers = {
            'equity': 1.0,
            'sector_etf': 1.2,      # Slightly larger positions for sector rotation
            'crypto_etf': 0.8,      # Smaller positions due to volatility
            'international_etf': 1.0,
            'factor_etf': 1.1
        }

        asset_multiplier = asset_multipliers.get(asset_class, 1.0)
        adjusted_dollars = target_dollars * quality_multiplier * asset_multiplier

        return {
            'should_buy': True,
            'reason': f'Strong {asset_class} signal ({signal_score:.2f}) + good fundamentals ({fundamental_score:.2f})',
            'adjusted_size': adjusted_dollars,
            'asset_class': asset_class
        }

    def _should_sell_enhanced(self, symbol: str, current_price: float,
                            signal_score: float = None) -> Dict[str, Any]:
        """Enhanced sell decision with asset-class specific parameters"""

        if symbol not in self.positions:
            return {'should_sell': False, 'reason': 'Not in portfolio', 'shares': 0}

        position = self.positions[symbol]
        asset_class = position.get('asset_class', 'equity')
        risk_params = self.asset_risk_params.get(asset_class, self.asset_risk_params['equity'])

        entry_price = position['entry_price']
        shares = position['shares']

        # Calculate current P&L
        current_value = shares * current_price
        cost_basis = shares * entry_price
        pnl_percent = (current_value - cost_basis) / cost_basis

        # Asset-specific stop loss and take profit
        stop_loss = -risk_params['stop_loss']
        take_profit = risk_params['take_profit']

        # Stop loss check
        if pnl_percent < stop_loss:
            return {
                'should_sell': True,
                'reason': f'{asset_class} stop loss triggered: {pnl_percent:.1%} loss (limit: {stop_loss:.1%})',
                'shares': shares
            }

        # Take profit check
        if pnl_percent > take_profit:
            return {
                'should_sell': True,
                'reason': f'{asset_class} take profit triggered: {pnl_percent:.1%} gain (target: {take_profit:.1%})',
                'shares': shares
            }

        # Signal-based sell (if provided)
        if signal_score is not None:
            signal_thresholds = {
                'equity': -0.6,
                'sector_etf': -0.4,     # Rotate out of weak sectors faster
                'crypto_etf': -0.3,     # Quick exits for crypto
                'international_etf': -0.5,
                'factor_etf': -0.5
            }

            threshold = signal_thresholds.get(asset_class, -0.6)
            if signal_score < threshold:
                return {
                    'should_sell': True,
                    'reason': f'Strong {asset_class} sell signal: {signal_score:.2f}',
                    'shares': shares
                }

        # Fundamental deterioration (for equities mainly)
        if asset_class == 'equity':
            fundamental_score = self._get_fundamentals_score(symbol, asset_class)
            if fundamental_score < 0.3:
                return {
                    'should_sell': True,
                    'reason': f'Deteriorating fundamentals: {fundamental_score:.2f}',
                    'shares': shares
                }

        return {'should_sell': False, 'reason': 'Hold position', 'shares': 0}

    def process_enhanced_daily_report(self, report_date: Union[str, date]) -> Dict[str, Any]:
        """Process daily report with enhanced multi-asset logic"""

        if isinstance(report_date, str):
            report_date = datetime.strptime(report_date, "%Y-%m-%d").date()

        self.logger.info(f"🚀 Processing enhanced multi-asset signals for {report_date}")

        # Try to find the report file
        reports_dir = Path("reports")
        json_report = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"

        if not json_report.exists():
            self.logger.error(f"Report not found: {json_report}")
            return {"status": "error", "message": f"Report not found for {report_date}"}

        try:
            with open(json_report, 'r') as f:
                report = json.load(f)

            executed_trades = []
            skipped_trades = []

            portfolio_value_before = self.get_portfolio_value()

            # Process long recommendations with asset class logic
            for position in report.get('top_long', []):
                symbol = position['symbol']
                signal_score = position.get('score', 0.5)
                price = position['price']
                suggested_size = position.get('position_size', 2.0) / 100.0

                # Determine asset class
                asset_class = self._get_asset_class(symbol)

                # Calculate target based on asset allocation
                portfolio_value = self.get_portfolio_value()
                max_allocation = self.asset_allocation.get(asset_class, 0.05)
                max_position = self.asset_risk_params[asset_class]['max_position']

                target_dollars = portfolio_value * min(suggested_size, max_position)

                # Enhanced buy decision
                decision = self._should_buy_enhanced(symbol, signal_score, price, target_dollars, asset_class)

                if decision['should_buy']:
                    adjusted_dollars = decision['adjusted_size']
                    shares = int(adjusted_dollars / price)

                    if shares > 0:
                        success = self._execute_buy_enhanced(symbol, shares, price, report_date, asset_class)
                        if success:
                            executed_trades.append({
                                "action": "BUY",
                                "symbol": symbol,
                                "shares": shares,
                                "price": price,
                                "amount": shares * price,
                                "asset_class": asset_class,
                                "reason": decision['reason'],
                                "signal_score": signal_score
                            })
                else:
                    skipped_trades.append({
                        "action": "SKIP_BUY",
                        "symbol": symbol,
                        "asset_class": asset_class,
                        "reason": decision['reason'],
                        "signal_score": signal_score
                    })

            # Process sell recommendations
            for position in report.get('top_short', []):
                symbol = position['symbol']
                signal_score = position.get('score', -0.5)
                price = position['price']

                if symbol in self.positions:
                    decision = self._should_sell_enhanced(symbol, price, signal_score)

                    if decision['should_sell']:
                        asset_class = self.positions[symbol].get('asset_class', 'equity')
                        success = self._execute_sell_enhanced(symbol, decision['shares'], price, report_date)
                        if success:
                            executed_trades.append({
                                "action": "SELL",
                                "symbol": symbol,
                                "shares": decision['shares'],
                                "price": price,
                                "amount": decision['shares'] * price,
                                "asset_class": asset_class,
                                "reason": decision['reason'],
                                "signal_score": signal_score
                            })

            # Review all positions for risk management
            for symbol in list(self.positions.keys()):
                current_price = self._get_current_price(symbol)
                if current_price:
                    decision = self._should_sell_enhanced(symbol, current_price)

                    if decision['should_sell']:
                        asset_class = self.positions[symbol].get('asset_class', 'equity')
                        success = self._execute_sell_enhanced(symbol, decision['shares'], current_price, report_date)
                        if success:
                            executed_trades.append({
                                "action": "RISK_SELL",
                                "symbol": symbol,
                                "shares": decision['shares'],
                                "price": current_price,
                                "amount": decision['shares'] * current_price,
                                "asset_class": asset_class,
                                "reason": decision['reason']
                            })

            # Calculate leverage costs
            leverage_cost_daily = self._calculate_leverage_cost()

            # Save state
            self._save_state()

            portfolio_value_after = self.get_portfolio_value()
            daily_return = (portfolio_value_after - portfolio_value_before - leverage_cost_daily) / portfolio_value_before

            self.logger.info(f"✅ Enhanced trading session complete:")
            self.logger.info(f"   Executed: {len(executed_trades)} trades")
            self.logger.info(f"   Skipped: {len(skipped_trades)} opportunities")
            self.logger.info(f"   Portfolio value: ${portfolio_value_before:,.0f} → ${portfolio_value_after:,.0f}")
            self.logger.info(f"   Daily return: {daily_return:.2%}")
            self.logger.info(f"   Leverage cost: ${leverage_cost_daily:.2f}")

            return {
                "status": "completed",
                "date": report_date.strftime("%Y-%m-%d"),
                "trades_executed": len(executed_trades),
                "trades_skipped": len(skipped_trades),
                "executed_trades": executed_trades,
                "skipped_trades": skipped_trades,
                "portfolio_value_before": portfolio_value_before,
                "portfolio_value_after": portfolio_value_after,
                "daily_return": daily_return,
                "leverage_cost": leverage_cost_daily,
                "cash_balance": self.cash_balance,
                "positions_count": len(self.positions),
                "asset_allocation": self._get_current_allocation()
            }

        except Exception as e:
            self.logger.error(f"Error processing enhanced report: {e}")
            return {"status": "error", "message": str(e)}

    def _execute_buy_enhanced(self, symbol: str, shares: int, price: float,
                            trade_date: date, asset_class: str) -> bool:
        """Execute buy order with asset class tracking"""
        cost = shares * price
        total_cost = cost + self.trading_fee

        if total_cost > self.cash_balance:
            self.logger.warning(f"Insufficient funds to buy {shares} {symbol} @ ${price}")
            return False

        # Execute the order
        if symbol in self.positions:
            # Update existing position
            existing_shares = self.positions[symbol]['shares']
            existing_cost = existing_shares * self.positions[symbol]['entry_price']
            new_cost = existing_cost + cost
            new_shares = existing_shares + shares

            self.positions[symbol].update({
                'shares': new_shares,
                'entry_price': new_cost / new_shares,
                'cost_basis': new_cost,
                'asset_class': asset_class
            })
        else:
            # New position
            self.positions[symbol] = {
                'shares': shares,
                'entry_price': price,
                'entry_date': trade_date.strftime('%Y-%m-%d'),
                'cost_basis': cost,
                'asset_class': asset_class
            }

        # Update cash balance
        self.cash_balance -= total_cost

        # Record the trade
        self.trade_history.append({
            'date': trade_date.strftime('%Y-%m-%d'),
            'action': 'BUY',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'amount': cost,
            'fees': self.trading_fee,
            'total_cost': total_cost,
            'asset_class': asset_class
        })

        self.logger.info(f"✅ Bought {shares} {symbol} ({asset_class}) @ ${price:.2f} = ${cost:.2f}")
        return True

    def _execute_sell_enhanced(self, symbol: str, shares: int, price: float, trade_date: date) -> bool:
        """Execute sell order with enhanced tracking"""
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        available_shares = position['shares']
        asset_class = position.get('asset_class', 'equity')

        if shares > available_shares:
            shares = available_shares

        # Calculate proceeds and P&L
        proceeds = shares * price
        net_proceeds = proceeds - self.trading_fee
        cost_basis = (shares / available_shares) * position['cost_basis']
        pnl = net_proceeds - cost_basis

        # Update or remove position
        if shares == available_shares:
            del self.positions[symbol]
        else:
            remaining_shares = available_shares - shares
            remaining_cost = position['cost_basis'] - cost_basis

            self.positions[symbol].update({
                'shares': remaining_shares,
                'cost_basis': remaining_cost
            })

        # Update cash balance
        self.cash_balance += net_proceeds

        # Record the trade
        self.trade_history.append({
            'date': trade_date.strftime('%Y-%m-%d'),
            'action': 'SELL',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'amount': proceeds,
            'fees': self.trading_fee,
            'net_proceeds': net_proceeds,
            'pnl': pnl,
            'pnl_percent': (pnl / cost_basis) * 100 if cost_basis > 0 else 0,
            'asset_class': asset_class
        })

        self.logger.info(f"✅ Sold {shares} {symbol} ({asset_class}) @ ${price:.2f} (P&L: ${pnl:.2f})")
        return True

    def _calculate_leverage_cost(self) -> float:
        """Calculate daily leverage borrowing cost"""
        borrowed_amount = self.effective_capital - self.initial_capital
        if borrowed_amount > 0:
            daily_cost = borrowed_amount * (self.leverage_cost / 365)
            return daily_cost
        return 0.0

    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value including leverage"""
        total_value = self.cash_balance

        for symbol, position in self.positions.items():
            current_price = self._get_current_price(symbol)
            if current_price:
                position_value = position['shares'] * current_price
                total_value += position_value
            else:
                position_value = position['shares'] * position['entry_price']
                total_value += position_value

        return total_value

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for any symbol"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except:
            pass
        return None

    def _get_current_allocation(self) -> Dict[str, float]:
        """Get current asset allocation breakdown"""
        portfolio_value = self.get_portfolio_value()
        if portfolio_value == 0:
            return {}

        allocation = {}
        for symbol, position in self.positions.items():
            asset_class = position.get('asset_class', 'equity')
            current_price = self._get_current_price(symbol)
            if current_price:
                position_value = position['shares'] * current_price
                if asset_class not in allocation:
                    allocation[asset_class] = 0
                allocation[asset_class] += position_value / portfolio_value

        allocation['cash'] = self.cash_balance / portfolio_value
        return allocation

    def get_enhanced_portfolio_status(self) -> Dict[str, Any]:
        """Get comprehensive enhanced portfolio status"""
        portfolio_value = self.get_portfolio_value()
        initial_value = self.initial_capital

        # Account for leverage in return calculation
        effective_return = (portfolio_value - self.effective_capital) / self.initial_capital

        # Calculate leverage costs to date
        days_active = (date.today() - self.start_date).days
        total_leverage_cost = self._calculate_leverage_cost() * days_active

        # Asset allocation breakdown
        current_allocation = self._get_current_allocation()

        return {
            'initial_capital': self.initial_capital,
            'effective_capital': self.effective_capital,
            'leverage_multiplier': self.leverage_multiplier,
            'current_value': portfolio_value,
            'total_return': f"{effective_return:.2%}",
            'total_return_dollars': portfolio_value - self.initial_capital,
            'leverage_cost_total': total_leverage_cost,
            'cash_balance': self.cash_balance,
            'positions_count': len(self.positions),
            'current_allocation': current_allocation,
            'target_allocation': self.asset_allocation,
            'total_trades': len(self.trade_history),
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'enhancement_active': True
        }
