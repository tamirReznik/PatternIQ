"""
Asset Universe - Manage multiple asset classes (Stocks, Indexes, Crypto)

This module extends PatternIQ to support trading across multiple asset classes:
- S&P 500 stocks (existing)
- Major market indexes (SPY, QQQ, DIA, IWM)
- Cryptocurrencies (BTC, ETH, and major altcoins)
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class AssetClass:
    """Enum-like class for asset types"""
    STOCK = "stock"
    INDEX = "index"
    CRYPTO = "crypto"


class AssetUniverse:
    """
    Manages the expanded universe of tradeable assets

    Features:
    - Multi-asset class support
    - Different trading rules per asset class
    - 24/7 trading for crypto
    - Lower position limits for volatile assets
    """

    # Major market indexes
    INDEXES = {
        'SPY': {'name': 'S&P 500 ETF', 'category': 'broad_market'},
        'QQQ': {'name': 'NASDAQ-100 ETF', 'category': 'tech'},
        'DIA': {'name': 'Dow Jones ETF', 'category': 'blue_chip'},
        'IWM': {'name': 'Russell 2000 ETF', 'category': 'small_cap'},
        'VTI': {'name': 'Total Stock Market ETF', 'category': 'broad_market'},
        'EFA': {'name': 'International Developed Markets', 'category': 'international'},
    }

    # Major cryptocurrencies (with exchange suffix for Yahoo Finance)
    CRYPTOS = {
        'BTC-USD': {'name': 'Bitcoin', 'category': 'crypto_blue_chip', 'volatility': 'high'},
        'ETH-USD': {'name': 'Ethereum', 'category': 'crypto_blue_chip', 'volatility': 'high'},
        'BNB-USD': {'name': 'Binance Coin', 'category': 'exchange_token', 'volatility': 'very_high'},
        'SOL-USD': {'name': 'Solana', 'category': 'smart_contract', 'volatility': 'very_high'},
        'ADA-USD': {'name': 'Cardano', 'category': 'smart_contract', 'volatility': 'very_high'},
        'XRP-USD': {'name': 'Ripple', 'category': 'payment', 'volatility': 'very_high'},
        'DOGE-USD': {'name': 'Dogecoin', 'category': 'meme', 'volatility': 'extreme'},
        'MATIC-USD': {'name': 'Polygon', 'category': 'scaling', 'volatility': 'very_high'},
    }

    def __init__(self):
        self.logger = logging.getLogger("AssetUniverse")

    @staticmethod
    def get_asset_class(symbol: str) -> str:
        """Determine asset class from symbol"""
        if symbol in AssetUniverse.INDEXES:
            return AssetClass.INDEX
        elif symbol in AssetUniverse.CRYPTOS or '-USD' in symbol:
            return AssetClass.CRYPTO
        else:
            return AssetClass.STOCK

    @staticmethod
    def get_position_limits(asset_class: str) -> Dict[str, float]:
        """
        Get appropriate position sizing limits for each asset class

        Returns:
            Dict with max_position_size and max_portfolio_allocation
        """
        limits = {
            AssetClass.STOCK: {
                'max_position_size': 0.05,  # 5% per stock
                'max_portfolio_allocation': 0.70,  # 70% total in stocks
                'stop_loss': 0.15,  # 15% stop loss
                'take_profit': 0.30,  # 30% take profit
            },
            AssetClass.INDEX: {
                'max_position_size': 0.15,  # 15% per index (less risky)
                'max_portfolio_allocation': 0.40,  # 40% total in indexes
                'stop_loss': 0.10,  # 10% stop loss (tighter for indexes)
                'take_profit': 0.20,  # 20% take profit
            },
            AssetClass.CRYPTO: {
                'max_position_size': 0.03,  # 3% per crypto (very risky)
                'max_portfolio_allocation': 0.15,  # 15% total in crypto
                'stop_loss': 0.20,  # 20% stop loss (wider for volatility)
                'take_profit': 0.50,  # 50% take profit (can have big moves)
            },
        }
        return limits.get(asset_class, limits[AssetClass.STOCK])

    @staticmethod
    def is_market_open(asset_class: str, check_time: Optional[datetime] = None) -> bool:
        """
        Check if the market is open for trading this asset class

        Args:
            asset_class: Type of asset
            check_time: Time to check (defaults to now)

        Returns:
            True if market is open for this asset
        """
        if check_time is None:
            check_time = datetime.now()

        # Crypto markets are always open
        if asset_class == AssetClass.CRYPTO:
            return True

        # Stock and index markets: weekdays 9:30 AM - 4:00 PM ET
        if check_time.weekday() >= 5:  # Saturday or Sunday
            return False

        # Convert to ET time (simplified - real implementation should use pytz)
        hour = check_time.hour
        minute = check_time.minute

        # Market hours: 9:30 AM - 4:00 PM ET
        market_open_time = 9 * 60 + 30  # 9:30 AM in minutes
        market_close_time = 16 * 60  # 4:00 PM in minutes
        current_time = hour * 60 + minute

        return market_open_time <= current_time < market_close_time

    @staticmethod
    def get_all_tradeable_assets() -> Dict[str, Dict]:
        """
        Get complete universe of tradeable assets

        Returns:
            Dict mapping symbol -> asset metadata
        """
        assets = {}

        # Add indexes
        for symbol, info in AssetUniverse.INDEXES.items():
            assets[symbol] = {
                **info,
                'asset_class': AssetClass.INDEX,
                'tradeable': True,
            }

        # Add cryptocurrencies
        for symbol, info in AssetUniverse.CRYPTOS.items():
            assets[symbol] = {
                **info,
                'asset_class': AssetClass.CRYPTO,
                'tradeable': True,
                '24_7_trading': True,
            }

        return assets

    @staticmethod
    def get_trading_fees(asset_class: str) -> Dict[str, float]:
        """
        Get typical trading fees for each asset class

        Returns:
            Dict with fee structure
        """
        fees = {
            AssetClass.STOCK: {
                'commission': 0.0,  # Most brokers are commission-free now
                'spread_bps': 1,  # 1 basis point typical spread
                'sec_fee_bps': 0.0008,  # SEC fee on sells
            },
            AssetClass.INDEX: {
                'commission': 0.0,
                'spread_bps': 0.5,  # Tighter spreads for liquid ETFs
                'expense_ratio': 0.0003,  # Annual expense ratio (e.g., 0.03% for SPY)
            },
            AssetClass.CRYPTO: {
                'commission': 0.0,
                'spread_bps': 5,  # Wider spreads for crypto
                'exchange_fee': 0.001,  # 0.1% typical exchange fee
                'network_fee': 5.0,  # Flat network fee (varies by crypto)
            },
        }
        return fees.get(asset_class, fees[AssetClass.STOCK])

    def fetch_price_data(self, symbols: List[str], start_date: date, end_date: date) -> pd.DataFrame:
        """
        Fetch historical price data for any asset class

        Args:
            symbols: List of symbols to fetch
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with price data
        """
        all_data = []

        for symbol in symbols:
            try:
                self.logger.info(f"Fetching data for {symbol}...")
                ticker = yf.Ticker(symbol)

                # Download data
                df = ticker.history(start=start_date, end=end_date)

                if df.empty:
                    self.logger.warning(f"No data available for {symbol}")
                    continue

                # Add symbol and asset class
                df['symbol'] = symbol
                df['asset_class'] = self.get_asset_class(symbol)

                all_data.append(df)

            except Exception as e:
                self.logger.error(f"Error fetching {symbol}: {e}")

        if not all_data:
            return pd.DataFrame()

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=False)
        combined_df.reset_index(inplace=True)

        return combined_df


def test_asset_universe():
    """Demonstrate the expanded asset universe"""
    print("🌍 PATTERNIQ EXPANDED ASSET UNIVERSE")
    print("=" * 70)

    universe = AssetUniverse()
    assets = universe.get_all_tradeable_assets()

    print(f"\n📊 Total Tradeable Assets: {len(assets)}")

    # Show indexes
    indexes = {k: v for k, v in assets.items() if v['asset_class'] == AssetClass.INDEX}
    print(f"\n📈 MARKET INDEXES ({len(indexes)}):")
    for symbol, info in indexes.items():
        print(f"  {symbol:6} - {info['name']:30} [{info['category']}]")

    # Show cryptos
    cryptos = {k: v for k, v in assets.items() if v['asset_class'] == AssetClass.CRYPTO}
    print(f"\n₿ CRYPTOCURRENCIES ({len(cryptos)}):")
    for symbol, info in cryptos.items():
        volatility = info.get('volatility', 'unknown')
        print(f"  {symbol:10} - {info['name']:20} [{info['category']:15}] Volatility: {volatility}")

    # Show position limits
    print(f"\n⚖️ POSITION LIMITS BY ASSET CLASS:")
    for asset_class in [AssetClass.STOCK, AssetClass.INDEX, AssetClass.CRYPTO]:
        limits = universe.get_position_limits(asset_class)
        print(f"\n  {asset_class.upper()}:")
        print(f"    Max per position: {limits['max_position_size']:.1%}")
        print(f"    Max total allocation: {limits['max_portfolio_allocation']:.1%}")
        print(f"    Stop loss: {limits['stop_loss']:.1%}")
        print(f"    Take profit: {limits['take_profit']:.1%}")

    # Show trading fees
    print(f"\n💰 TRADING FEES BY ASSET CLASS:")
    for asset_class in [AssetClass.STOCK, AssetClass.INDEX, AssetClass.CRYPTO]:
        fees = universe.get_trading_fees(asset_class)
        print(f"\n  {asset_class.upper()}:")
        for fee_type, amount in fees.items():
            print(f"    {fee_type}: {amount}")

    # Market hours
    print(f"\n🕒 MARKET HOURS:")
    now = datetime.now()
    for asset_class in [AssetClass.STOCK, AssetClass.INDEX, AssetClass.CRYPTO]:
        is_open = universe.is_market_open(asset_class, now)
        status = "OPEN ✅" if is_open else "CLOSED ❌"
        hours = "24/7" if asset_class == AssetClass.CRYPTO else "9:30 AM - 4:00 PM ET"
        print(f"  {asset_class.upper():10} - {hours:25} {status}")


if __name__ == "__main__":
    demo_asset_universe()

