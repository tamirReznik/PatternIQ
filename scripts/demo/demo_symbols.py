r# src/data/demo_symbols.py - Quick symbol fetching demo

import logging
from src.providers.sp500_provider import SP500Provider

def main():
    """Demo: Just fetch and display S&P 500 symbols"""
    logging.basicConfig(level=logging.INFO)

    print("🔍 Fetching S&P 500 Symbols")
    print("=" * 40)

    provider = SP500Provider()
    symbols = provider.list_symbols()

    print(f"✅ Found {len(symbols)} symbols")
    print(f"First 20: {symbols[:20]}")
    print(f"Contains AAPL: {'AAPL' in symbols}")
    print(f"Contains MSFT: {'MSFT' in symbols}")

    # Save to file for reference
    with open("sp500_symbols.txt", "w") as f:
        for symbol in symbols:
            f.write(f"{symbol}\n")

    print(f"💾 Saved complete list to sp500_symbols.txt")

if __name__ == "__main__":
    main()
