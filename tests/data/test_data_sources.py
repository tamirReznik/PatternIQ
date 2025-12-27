#!/usr/bin/env python3
"""
Test script to demonstrate enhanced data sources vs basic sources
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.providers.sp500_provider import SP500Provider
from src.config.data_sources import DataSourceConfig
import json

def test_data_sources():
    """Test and compare data sources"""
    print("🔍 Testing PatternIQ Data Sources")
    print("=" * 50)

    # Initialize provider
    provider = SP500Provider()

    # Get data quality report
    quality_report = provider.get_data_quality_report()
    print("\n📊 Data Source Availability:")
    print(f"Enhanced Provider: {'✅' if quality_report['enhanced_provider_available'] else '❌'}")
    print(f"Available Sources: {', '.join(quality_report['available_sources'])}")

    if quality_report['api_keys_configured']:
        print("API Keys Configured:")
        for api, configured in quality_report['api_keys_configured'].items():
            print(f"  {api}: {'✅' if configured else '❌'}")
    else:
        print("No additional API keys configured (using free Yahoo Finance only)")

    # Test S&P 500 constituents
    print("\n🏢 Testing S&P 500 Constituents:")
    symbols = provider.list_symbols()
    print(f"Found {len(symbols)} S&P 500 companies")
    print(f"Sample symbols: {symbols[:10]}")

    # Check if enhanced metadata was stored
    metadata_file = Path("data/sp500_metadata.json")
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        print(f"Enhanced metadata available with sectors and industries")
        sample = metadata[0] if metadata else {}
        if sample:
            print(f"Sample: {sample.get('symbol')} - {sample.get('company_name')} ({sample.get('sector')})")

    # Test price data for a sample stock
    print("\n📈 Testing Price Data (AAPL):")
    try:
        bars = provider.get_bars("AAPL", "1d", "2024-10-01", "2024-10-31")
        if bars:
            print(f"Retrieved {len(bars)} trading days")
            latest = bars[-1]
            print(f"Latest data: {latest['t']} - Close: ${latest['c']:.2f}, Volume: {latest['v']:,}")
            print(f"Data source: {latest.get('vendor', 'unknown')}")
        else:
            print("No price data retrieved")
    except Exception as e:
        print(f"Error getting price data: {e}")

    # Test fundamentals
    print("\n💰 Testing Fundamental Data (AAPL):")
    try:
        fundamentals = provider.get_fundamentals("AAPL")
        if fundamentals:
            if 'sources' in fundamentals:
                print(f"Multi-source fundamentals from {len(fundamentals['sources'])} providers")
                for source in fundamentals['sources']:
                    print(f"  Source: {source.get('source', 'unknown')}")
                    if source.get('market_cap'):
                        print(f"    Market Cap: ${source['market_cap']:,.0f}")
                    if source.get('pe_ratio'):
                        print(f"    P/E Ratio: {source['pe_ratio']:.2f}")
            else:
                print(f"Basic fundamentals from {fundamentals.get('source', 'unknown')}")
                if fundamentals.get('market_cap'):
                    print(f"  Market Cap: ${fundamentals['market_cap']:,.0f}")
        else:
            print("No fundamental data available")
    except Exception as e:
        print(f"Error getting fundamentals: {e}")

    # Test corporate actions
    print("\n📋 Testing Corporate Actions (AAPL):")
    try:
        actions = provider.get_corporate_actions("AAPL", "2024-01-01", "2024-10-31")
        if actions:
            print(f"Found {len(actions)} corporate actions")
            for action in actions[:3]:  # Show first 3
                print(f"  {action['date']}: {action['type']} - {action.get('amount', action.get('ratio', 'N/A'))}")
        else:
            print("No corporate actions found")
    except Exception as e:
        print(f"Error getting corporate actions: {e}")

    print("\n🔧 Setup Instructions:")
    config = DataSourceConfig()
    print(config.setup_instructions())

if __name__ == "__main__":
    test_data_sources()
