"""
Data source configuration and free API key management

Free API tiers available:
1. Alpha Vantage: 25 calls/day (free) - good for backup price data
2. Financial Modeling Prep: 250 calls/day (free) - excellent for fundamentals
3. FRED (Federal Reserve): Unlimited basic access - economic indicators
4. SEC EDGAR: 10 requests/second - official filings
"""

import os
from typing import Dict, Optional

class DataSourceConfig:
    """Manage data source configurations and API keys"""

    def __init__(self):
        # Free API keys (get from environment or config)
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')  # Free: 25 calls/day
        self.fmp_key = os.getenv('FMP_API_KEY')  # Free: 250 calls/day

        # Rate limits for free tiers
        self.rate_limits = {
            'yahoo': {'requests': 100, 'period': 3600},  # Conservative estimate
            'alpha_vantage': {'requests': 25, 'period': 86400},  # 25/day
            'fmp': {'requests': 250, 'period': 86400},  # 250/day
            'sec': {'requests': 10, 'period': 1},  # 10/second
            'fred': {'requests': 1000, 'period': 3600}  # Very generous
        }

    def get_api_keys(self) -> Dict[str, Optional[str]]:
        """Get available API keys"""
        return {
            'alpha_vantage': self.alpha_vantage_key,
            'fmp': self.fmp_key
        }

    def get_free_tier_limits(self) -> Dict[str, Dict[str, int]]:
        """Get rate limits for free API tiers"""
        return self.rate_limits

    def setup_instructions(self) -> str:
        """Return setup instructions for free APIs"""
        return """
🔑 FREE API SETUP INSTRUCTIONS:

1. Alpha Vantage (Backup price data):
   - Visit: https://www.alphavantage.co/support/#api-key
   - Sign up for free account
   - Get API key (25 calls/day)
   - Add to .env: ALPHA_VANTAGE_API_KEY=your_key_here

2. Financial Modeling Prep (Fundamentals):
   - Visit: https://financialmodelingprep.com/developer/docs
   - Sign up for free account  
   - Get API key (250 calls/day)
   - Add to .env: FMP_API_KEY=your_key_here

3. FRED (Economic data):
   - No API key needed for basic access
   - Visit: https://fred.stlouisfed.org/docs/api/

4. SEC EDGAR (Corporate filings):
   - No API key needed
   - Rate limited to 10 requests/second

BENEFITS:
✅ Redundant price data sources
✅ Rich fundamental data 
✅ Economic indicators
✅ Corporate actions and filings
✅ Data quality validation
✅ All FREE tiers combined give you robust coverage
        """
