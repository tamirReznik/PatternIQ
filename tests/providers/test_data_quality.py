#!/usr/bin/env python3
"""
Tests for data quality validation
Tests gap detection, anomaly detection, and quality scoring
"""

import pytest
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.providers.sp500_provider import SP500Provider


class TestDataQuality:
    """Test suite for data quality validation"""
    
    @pytest.fixture
    def provider(self):
        """Create a provider instance for testing"""
        return SP500Provider()
    
    @pytest.fixture
    def good_bars(self):
        """Sample good quality bars"""
        return [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-02'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 1100000},
            {'t': pd.Timestamp('2024-01-03'), 'o': 104.0, 'h': 109.0, 'l': 99.0, 'c': 106.0, 'v': 1200000},
            {'t': pd.Timestamp('2024-01-04'), 'o': 106.0, 'h': 111.0, 'l': 101.0, 'c': 108.0, 'v': 1150000},
            {'t': pd.Timestamp('2024-01-05'), 'o': 108.0, 'h': 113.0, 'l': 103.0, 'c': 110.0, 'v': 1250000},
        ]
    
    def test_validate_empty_data(self, provider):
        """Test validation with empty data"""
        report = provider._validate_data_quality('AAPL', [])
        
        assert report['status'] == 'error'
        assert report['issue'] == 'no_data'
        assert report['quality_score'] == 0
    
    def test_validate_good_data(self, provider, good_bars):
        """Test validation with good quality data"""
        report = provider._validate_data_quality('AAPL', good_bars)
        
        assert report['status'] == 'validated'
        assert report['symbol'] == 'AAPL'
        assert report['total_bars'] == 5
        assert report['quality_score'] >= 90
        assert len(report['issues']) == 0
    
    def test_detect_date_gaps(self, provider):
        """Test detection of date gaps > 4 days"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-10'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 1100000},  # 9 day gap
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        assert len(report['issues']) > 0
        gap_issues = [i for i in report['issues'] if 'gap' in i.lower()]
        assert len(gap_issues) > 0
        assert '9' in gap_issues[0]  # Should mention 9 days
    
    def test_detect_weekend_gap_not_flagged(self, provider):
        """Test that weekend gaps (2-3 days) are not flagged"""
        bars = [
            {'t': pd.Timestamp('2024-01-05'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},  # Friday
            {'t': pd.Timestamp('2024-01-08'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 1100000},  # Monday (3 day gap)
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        # Weekend gaps should not be flagged
        gap_issues = [i for i in report['issues'] if 'gap' in i.lower()]
        assert len(gap_issues) == 0
    
    def test_detect_extreme_price_movements(self, provider):
        """Test detection of extreme price movements (>50% gaps)"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 100.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-02'), 'o': 200.0, 'h': 205.0, 'l': 195.0, 'c': 200.0, 'v': 1100000},  # 100% gap
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        assert len(report['issues']) > 0
        price_issues = [i for i in report['issues'] if 'gap' in i.lower() or 'extreme' in i.lower()]
        assert len(price_issues) > 0
    
    def test_allow_reasonable_splits(self, provider):
        """Test that reasonable stock splits (2:1, 3:1) are not flagged"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 100.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-02'), 'o': 50.0, 'h': 52.5, 'l': 47.5, 'c': 50.0, 'v': 2000000},  # 2:1 split
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        # 2:1 split should not be flagged (ratio 0.5 is within 0.3-3.0 range)
        extreme_issues = [i for i in report['issues'] if 'extreme' in i.lower()]
        assert len(extreme_issues) == 0
    
    def test_detect_invalid_prices(self, provider):
        """Test detection of zero or negative prices"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 0.0, 'v': 1000000},  # Invalid close
            {'t': pd.Timestamp('2024-01-02'), 'o': -10.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1100000},  # Invalid open
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        assert len(report['issues']) > 0
        invalid_issues = [i for i in report['issues'] if 'invalid' in i.lower()]
        assert len(invalid_issues) >= 2  # Should detect both invalid prices
    
    def test_detect_volume_spikes(self, provider):
        """Test detection of volume spikes (>10x average)"""
        bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-02'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 1100000},
            {'t': pd.Timestamp('2024-01-03'), 'o': 104.0, 'h': 109.0, 'l': 99.0, 'c': 106.0, 'v': 1200000},
            {'t': pd.Timestamp('2024-01-04'), 'o': 106.0, 'h': 111.0, 'l': 101.0, 'c': 108.0, 'v': 15000000},  # 12.5x spike
        ]
        
        report = provider._validate_data_quality('AAPL', bars)
        
        assert len(report['issues']) > 0
        volume_issues = [i for i in report['issues'] if 'volume' in i.lower()]
        assert len(volume_issues) > 0
    
    def test_quality_score_calculation(self, provider, good_bars):
        """Test quality score calculation (0-100 scale)"""
        report = provider._validate_data_quality('AAPL', good_bars)
        
        assert 0 <= report['quality_score'] <= 100
        assert report['quality_score'] >= 90  # Good data should score high
    
    def test_quality_score_decreases_with_issues(self, provider):
        """Test that quality score decreases with more issues"""
        good_bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 102.0, 'v': 1000000},
            {'t': pd.Timestamp('2024-01-02'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 1100000},
        ]
        
        bad_bars = [
            {'t': pd.Timestamp('2024-01-01'), 'o': 100.0, 'h': 105.0, 'l': 95.0, 'c': 0.0, 'v': 1000000},  # Invalid
            {'t': pd.Timestamp('2024-01-10'), 'o': 102.0, 'h': 107.0, 'l': 97.0, 'c': 104.0, 'v': 15000000},  # Gap + spike
        ]
        
        good_report = provider._validate_data_quality('AAPL', good_bars)
        bad_report = provider._validate_data_quality('AAPL', bad_bars)
        
        assert good_report['quality_score'] > bad_report['quality_score']
    
    def test_quality_report_structure(self, provider, good_bars):
        """Test quality report has expected structure"""
        report = provider._validate_data_quality('AAPL', good_bars)
        
        assert 'status' in report
        assert 'symbol' in report
        assert 'total_bars' in report
        assert 'date_range' in report
        assert 'issues' in report
        assert 'quality_score' in report
        assert isinstance(report['issues'], list)
        assert isinstance(report['quality_score'], (int, float))

