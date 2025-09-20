# test_report_generation.py - Simple test to fix and verify report generation

import os
import json
from datetime import date
from jinja2 import Template

def create_simple_report():
    """Create a simple test report to verify the generation process"""

    print("🧪 Testing Report Generation Step by Step")
    print("=" * 50)

    # Ensure reports directory exists
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    print(f"✅ Reports directory created: {os.path.abspath(reports_dir)}")

    # Create sample data
    today = date.today()
    sample_data = {
        "report_metadata": {
            "report_id": "test-001",
            "report_date": today.isoformat(),
            "generated_at": "2025-09-20T16:30:00",
            "system_version": "PatternIQ 1.0 MVP",
            "report_type": "daily_trading_signals"
        },
        "executive_summary": {
            "market_regime": "Test Mode - Demo Data",
            "signal_strength": 85,
            "total_recommendations": 6,
            "strong_conviction_trades": 3
        },
        "trading_recommendations": {
            "long_candidates": [
                {
                    "symbol": "AAPL",
                    "company_name": "Apple Inc.",
                    "sector": "Technology",
                    "signal_score": 0.875,
                    "recommendation": "STRONG BUY",
                    "position_size": "3.0%",
                    "current_price": 175.50,
                    "volume": 50000000,
                    "rank": 1
                },
                {
                    "symbol": "MSFT",
                    "company_name": "Microsoft Corporation",
                    "sector": "Technology",
                    "signal_score": 0.724,
                    "recommendation": "BUY",
                    "position_size": "2.5%",
                    "current_price": 415.25,
                    "volume": 25000000,
                    "rank": 2
                },
                {
                    "symbol": "GOOGL",
                    "company_name": "Alphabet Inc.",
                    "sector": "Technology",
                    "signal_score": 0.681,
                    "recommendation": "BUY",
                    "position_size": "2.0%",
                    "current_price": 138.75,
                    "volume": 30000000,
                    "rank": 3
                }
            ],
            "short_candidates": [
                {
                    "symbol": "XOM",
                    "company_name": "Exxon Mobil Corporation",
                    "sector": "Energy",
                    "signal_score": -0.653,
                    "recommendation": "SELL",
                    "position_size": "2.0%",
                    "current_price": 115.30,
                    "volume": 15000000,
                    "rank": 1
                },
                {
                    "symbol": "CVX",
                    "company_name": "Chevron Corporation",
                    "sector": "Energy",
                    "signal_score": -0.587,
                    "recommendation": "SELL",
                    "position_size": "1.5%",
                    "current_price": 155.80,
                    "volume": 12000000,
                    "rank": 2
                }
            ]
        },
        "market_analysis": {
            "market_regime": "Test Mode with Tech Leadership",
            "signal_strength": 85,
            "total_signals": 503,
            "strong_longs": 3,
            "strong_shorts": 2,
            "sector_analysis": [
                {
                    "sector": "Technology",
                    "symbol_count": 75,
                    "avg_signal": 0.285,
                    "sentiment": "Bullish",
                    "bullish_stocks": 52,
                    "bearish_stocks": 8
                },
                {
                    "sector": "Energy",
                    "symbol_count": 25,
                    "avg_signal": -0.175,
                    "sentiment": "Bearish",
                    "bullish_stocks": 6,
                    "bearish_stocks": 15
                }
            ]
        },
        "performance_tracking": {
            "last_backtest_period": "2024-01-01 to 2024-09-20",
            "signal_strategy": "combined_ic_weighted",
            "total_positions_tested": 1250,
            "status": "Test Mode - Demo Data"
        },
        "risk_alerts": [
            "Tech sector concentration: 60% of long signals",
            "Energy sector weakness continues",
            "Test mode: Using sample data"
        ],
        "next_actions": [
            "Review demo recommendations",
            "Verify PDF generation working",
            "Test HTML and JSON formats",
            "Configure live data feeds"
        ]
    }

    # Step 1: Generate JSON report
    print("\n📄 Step 1: Generating JSON report...")
    json_filename = f"patterniq_report_{today.strftime('%Y%m%d')}.json"
    json_path = os.path.join(reports_dir, json_filename)

    with open(json_path, 'w') as f:
        json.dump(sample_data, f, indent=2, default=str)

    if os.path.exists(json_path):
        size = os.path.getsize(json_path)
        print(f"✅ JSON report created: {json_filename} ({size:,} bytes)")
    else:
        print(f"❌ JSON report failed")
        return False

    # Step 2: Generate HTML report
    print("\n📄 Step 2: Generating HTML report...")

    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>PatternIQ Daily Report - {{ report_data.report_metadata.report_date }}</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f7fa;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 30px; 
            text-align: center;
        }
        .header h1 { margin: 0; font-size: 2.5em; font-weight: 300; }
        .header p { margin: 10px 0 0 0; opacity: 0.9; }
        .section { 
            margin: 0; 
            padding: 25px; 
            border-bottom: 1px solid #e1e8ed;
        }
        .section:last-child { border-bottom: none; }
        .section h2 { color: #2c3e50; margin-top: 0; }
        .buy-section { background: linear-gradient(to right, #e8f5e8, #ffffff); }
        .sell-section { background: linear-gradient(to right, #f5e8e8, #ffffff); }
        .alert { 
            background: #fff3cd; 
            border: 1px solid #ffeaa7; 
            padding: 15px; 
            margin: 15px 0; 
            border-radius: 8px;
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 15px 0; 
            background: white;
        }
        th, td { 
            padding: 12px; 
            text-align: left; 
            border-bottom: 1px solid #ddd; 
        }
        th { 
            background-color: #f8f9fa; 
            font-weight: 600;
            color: #495057;
        }
        .strong-buy { color: #27ae60; font-weight: bold; }
        .buy { color: #2ecc71; font-weight: 500; }
        .sell { color: #e74c3c; font-weight: 500; }
        .strong-sell { color: #c0392b; font-weight: bold; }
        .score-positive { background: #d4edda; }
        .score-negative { background: #f8d7da; }
        .metric-card {
            display: inline-block;
            background: #f8f9fa;
            padding: 15px;
            margin: 10px;
            border-radius: 8px;
            min-width: 150px;
            text-align: center;
        }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }
        .metric-label {
            color: #6c757d;
            font-size: 0.9em;
        }
        footer {
            background: #f8f9fa;
            padding: 20px;
            margin-top: 20px;
            border-top: 1px solid #e9ecef;
            font-size: 0.9em;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 PatternIQ Daily Report</h1>
            <p><strong>{{ report_data.report_metadata.report_date }}</strong> | Generated: {{ report_data.report_metadata.generated_at[:16] }}</p>
            <p>Market Regime: <strong>{{ report_data.market_analysis.market_regime }}</strong></p>
        </div>
        
        <div class="section">
            <h2>📈 Executive Summary</h2>
            <div class="metric-card">
                <div class="metric-value">{{ report_data.executive_summary.signal_strength }}%</div>
                <div class="metric-label">Signal Strength</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ report_data.executive_summary.total_recommendations }}</div>
                <div class="metric-label">Total Recommendations</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ report_data.executive_summary.strong_conviction_trades }}</div>
                <div class="metric-label">High Conviction</div>
            </div>
        </div>
        
        {% if report_data.risk_alerts %}
        <div class="section">
            <div class="alert">
                <h3>⚠️ Risk Alerts</h3>
                {% for alert in report_data.risk_alerts %}
                <p>• {{ alert }}</p>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <div class="section buy-section">
            <h2>📈 Long Recommendations ({{ report_data.trading_recommendations.long_candidates|length }})</h2>
            {% if report_data.trading_recommendations.long_candidates %}
            <table>
                <tr>
                    <th>Rank</th><th>Symbol</th><th>Company</th><th>Sector</th>
                    <th>Signal Score</th><th>Recommendation</th><th>Position Size</th><th>Current Price</th>
                </tr>
                {% for stock in report_data.trading_recommendations.long_candidates %}
                <tr>
                    <td><strong>{{ stock.rank }}</strong></td>
                    <td><strong>{{ stock.symbol }}</strong></td>
                    <td>{{ stock.company_name }}</td>
                    <td>{{ stock.sector }}</td>
                    <td class="score-positive">{{ "%.3f"|format(stock.signal_score) }}</td>
                    <td class="{{ stock.recommendation.lower().replace(' ', '-') }}">{{ stock.recommendation }}</td>
                    <td><strong>{{ stock.position_size }}</strong></td>
                    <td>${{ "%.2f"|format(stock.current_price) }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No long recommendations today.</p>
            {% endif %}
        </div>
        
        <div class="section sell-section">
            <h2>📉 Short Recommendations ({{ report_data.trading_recommendations.short_candidates|length }})</h2>
            {% if report_data.trading_recommendations.short_candidates %}
            <table>
                <tr>
                    <th>Rank</th><th>Symbol</th><th>Company</th><th>Sector</th>
                    <th>Signal Score</th><th>Recommendation</th><th>Position Size</th><th>Current Price</th>
                </tr>
                {% for stock in report_data.trading_recommendations.short_candidates %}
                <tr>
                    <td><strong>{{ stock.rank }}</strong></td>
                    <td><strong>{{ stock.symbol }}</strong></td>
                    <td>{{ stock.company_name }}</td>
                    <td>{{ stock.sector }}</td>
                    <td class="score-negative">{{ "%.3f"|format(stock.signal_score) }}</td>
                    <td class="{{ stock.recommendation.lower().replace(' ', '-') }}">{{ stock.recommendation }}</td>
                    <td><strong>{{ stock.position_size }}</strong></td>
                    <td>${{ "%.2f"|format(stock.current_price) }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No short recommendations today.</p>
            {% endif %}
        </div>
        
        <div class="section">
            <h2>🏢 Sector Analysis</h2>
            <table>
                <tr><th>Sector</th><th>Stocks</th><th>Avg Signal</th><th>Sentiment</th><th>Bullish</th><th>Bearish</th></tr>
                {% for sector in report_data.market_analysis.sector_analysis %}
                <tr>
                    <td><strong>{{ sector.sector }}</strong></td>
                    <td>{{ sector.symbol_count }}</td>
                    <td>{{ "%.3f"|format(sector.avg_signal) }}</td>
                    <td><strong>{{ sector.sentiment }}</strong></td>
                    <td style="color: green;">{{ sector.bullish_stocks }}</td>
                    <td style="color: red;">{{ sector.bearish_stocks }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="section">
            <h2>📊 Performance Tracking</h2>
            <p><strong>Strategy:</strong> {{ report_data.performance_tracking.signal_strategy }}</p>
            <p><strong>Backtest Period:</strong> {{ report_data.performance_tracking.last_backtest_period }}</p>
            <p><strong>Total Positions Tested:</strong> {{ report_data.performance_tracking.total_positions_tested }}</p>
            <p><strong>Status:</strong> {{ report_data.performance_tracking.status }}</p>
        </div>
        
        <div class="section">
            <h2>🎯 Next Actions</h2>
            <ul>
            {% for action in report_data.next_actions %}
                <li>{{ action }}</li>
            {% endfor %}
            </ul>
        </div>
        
        <footer>
            <p><strong>Important Disclaimer:</strong> This report is for informational purposes only. Trading involves substantial risk of loss. 
            Past performance is not indicative of future results. Always conduct your own research and consider consulting with a financial advisor.</p>
            <p><em>Generated by PatternIQ v1.0 MVP on {{ report_data.report_metadata.generated_at[:10] }}</em></p>
        </footer>
    </div>
</body>
</html>
    """

    # Step 1: Create JSON
    json_filename = f"patterniq_report_{today.strftime('%Y%m%d')}.json"
    json_path = os.path.join(reports_dir, json_filename)

    with open(json_path, 'w') as f:
        json.dump(sample_data, f, indent=2)

    print(f"✅ JSON report created: {json_filename}")

    # Step 2: Create HTML
    html_filename = f"patterniq_report_{today.strftime('%Y%m%d')}.html"
    html_path = os.path.join(reports_dir, html_filename)

    template = Template(html_template)
    html_content = template.render(report_data=sample_data)

    with open(html_path, 'w') as f:
        f.write(html_content)

    print(f"✅ HTML report created: {html_filename}")

    # Step 3: Try to create PDF
    pdf_filename = f"patterniq_report_{today.strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.join(reports_dir, pdf_filename)

    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(pdf_path)

        if os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            print(f"✅ PDF report created: {pdf_filename} ({size:,} bytes)")
            print(f"🎯 PDF Location: {os.path.abspath(pdf_path)}")
        else:
            print(f"❌ PDF creation failed - file not found")

    except ImportError:
        print(f"⚠️ WeasyPrint not available - PDF generation skipped")
        print(f"   Install with: pip install weasyprint")
    except Exception as e:
        print(f"❌ PDF generation error: {e}")

    # Step 4: List all created files
    print(f"\n📂 Final Results:")
    reports_abs_path = os.path.abspath(reports_dir)
    print(f"Reports directory: {reports_abs_path}")

    if os.path.exists(reports_dir):
        files = [f for f in os.listdir(reports_dir) if os.path.isfile(os.path.join(reports_dir, f))]
        if files:
            print(f"Generated files ({len(files)}):")
            for file in sorted(files):
                file_path = os.path.join(reports_dir, file)
                size = os.path.getsize(file_path)
                abs_path = os.path.abspath(file_path)
                print(f"   📄 {file} ({size:,} bytes)")
                print(f"      📍 {abs_path}")

                if file.endswith('.pdf'):
                    print(f"      🎯 THIS IS YOUR PDF - Double-click to open!")
        else:
            print("   (No files created)")

    print(f"\n🔗 To open reports folder:")
    print(f"   open {reports_abs_path}")

    return True

if __name__ == "__main__":
    success = create_simple_report()
    if success:
        print(f"\n🎉 Report generation test completed successfully!")
    else:
        print(f"\n❌ Report generation test failed!")
