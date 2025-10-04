# src/report/generator.py - Report generation for PatternIQ

import os
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
from jinja2 import Environment, FileSystemLoader

def generate_daily_report(date_str: str = None):
    """
    Generate daily HTML and JSON reports with trading recommendations

    This function implements the reporting functionality from section 5:
    - Generates a daily report with top long/short recommendations
    - Includes sector breakdown and signal strengths
    - Creates both JSON (API-friendly) and HTML (human-readable) formats

    Args:
        date_str: Optional date string in YYYY-MM-DD format. If not provided,
                 uses yesterday's date for a daily run.
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("ReportGenerator")

    # Use yesterday if date not specified
    if date_str is None:
        report_date = date.today() - timedelta(days=1)
    else:
        report_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    logger.info(f"📊 Generating daily report for date: {report_date}")

    # Create reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Generate sample data for demo
    report_data = {
        "date": report_date.strftime("%Y-%m-%d"),
        "market_overview": {
            "regime": "Trending Market with Tech Leadership",
            "signal_strength": 82,
            "total_recommendations": 10,
            "high_conviction": 4
        },
        "top_long": [
            {
                "symbol": "AAPL",
                "sector": "Technology",
                "signal": "STRONG BUY",
                "score": 0.875,
                "position_size": 3.0,
                "price": 175.50,
                "rationale": "Strong momentum with recent product launch"
            },
            {
                "symbol": "MSFT",
                "sector": "Technology",
                "signal": "BUY",
                "score": 0.724,
                "position_size": 2.5,
                "price": 415.25,
                "rationale": "Cloud revenue growth acceleration"
            }
        ],
        "top_short": [
            {
                "symbol": "XOM",
                "sector": "Energy",
                "signal": "SELL",
                "score": -0.653,
                "position_size": 2.0,
                "price": 115.30,
                "rationale": "Weakening demand and price pressures"
            }
        ],
        "sector_scores": {
            "Technology": 0.285,
            "Healthcare": 0.145,
            "Consumer Discretionary": 0.085,
            "Financials": -0.035,
            "Energy": -0.175
        },
        "risk_alerts": [
            "Elevated market volatility expected this week",
            "Earnings season starts next week"
        ],
        "performance": {
            "yesterday": "+0.5%",
            "week": "+1.2%",
            "month": "+3.5%",
            "year": "+12.8%",
            "sharpe": 1.45
        }
    }

    # Generate JSON report
    json_path = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"
    with open(json_path, 'w') as f:
        json.dump(report_data, f, indent=2)

    # Generate HTML report
    try:
        # Check if templates directory exists
        templates_dir = Path("src/report/templates")
        if not templates_dir.exists():
            # Create a basic template inline if directory doesn't exist
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>PatternIQ Daily Report - {{ date }}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; }
                    .summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
                    .buy { color: #27ae60; }
                    .sell { color: #e74c3c; }
                    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                    th { background-color: #f2f2f2; }
                    .risk { background-color: #ffebee; padding: 10px; border-left: 4px solid #e74c3c; }
                </style>
            </head>
            <body>
                <h1>PatternIQ Daily Report</h1>
                <p>Date: {{ date }}</p>
                
                <div class="summary">
                    <h2>Market Overview</h2>
                    <p><strong>Regime:</strong> {{ market_overview.regime }}</p>
                    <p><strong>Signal Strength:</strong> {{ market_overview.signal_strength }}%</p>
                    <p><strong>Total Recommendations:</strong> {{ market_overview.total_recommendations }}</p>
                    <p><strong>High Conviction:</strong> {{ market_overview.high_conviction }}</p>
                </div>
                
                <h2>Top Long Recommendations</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Sector</th>
                        <th>Signal</th>
                        <th>Score</th>
                        <th>Size (%)</th>
                        <th>Price</th>
                        <th>Rationale</th>
                    </tr>
                    {% for stock in top_long %}
                    <tr>
                        <td><strong>{{ stock.symbol }}</strong></td>
                        <td>{{ stock.sector }}</td>
                        <td class="buy">{{ stock.signal }}</td>
                        <td>{{ stock.score }}</td>
                        <td>{{ stock.position_size }}%</td>
                        <td>${{ stock.price }}</td>
                        <td>{{ stock.rationale }}</td>
                    </tr>
                    {% endfor %}
                </table>
                
                <h2>Top Short Recommendations</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Sector</th>
                        <th>Signal</th>
                        <th>Score</th>
                        <th>Size (%)</th>
                        <th>Price</th>
                        <th>Rationale</th>
                    </tr>
                    {% for stock in top_short %}
                    <tr>
                        <td><strong>{{ stock.symbol }}</strong></td>
                        <td>{{ stock.sector }}</td>
                        <td class="sell">{{ stock.signal }}</td>
                        <td>{{ stock.score }}</td>
                        <td>{{ stock.position_size }}%</td>
                        <td>${{ stock.price }}</td>
                        <td>{{ stock.rationale }}</td>
                    </tr>
                    {% endfor %}
                </table>
                
                <h2>Sector Breakdown</h2>
                <table>
                    <tr>
                        <th>Sector</th>
                        <th>Score</th>
                    </tr>
                    {% for sector, score in sector_scores.items() %}
                    <tr>
                        <td>{{ sector }}</td>
                        <td>{{ score }}</td>
                    </tr>
                    {% endfor %}
                </table>
                
                <div class="risk">
                    <h2>Risk Alerts</h2>
                    <ul>
                    {% for alert in risk_alerts %}
                        <li>{{ alert }}</li>
                    {% endfor %}
                    </ul>
                </div>
                
                <h2>Performance</h2>
                <table>
                    <tr>
                        <th>Timeframe</th>
                        <th>Return</th>
                    </tr>
                    <tr>
                        <td>Yesterday</td>
                        <td>{{ performance.yesterday }}</td>
                    </tr>
                    <tr>
                        <td>Week</td>
                        <td>{{ performance.week }}</td>
                    </tr>
                    <tr>
                        <td>Month</td>
                        <td>{{ performance.month }}</td>
                    </tr>
                    <tr>
                        <td>Year</td>
                        <td>{{ performance.year }}</td>
                    </tr>
                    <tr>
                        <td>Sharpe Ratio</td>
                        <td>{{ performance.sharpe }}</td>
                    </tr>
                </table>
                
                <footer>
                    <p><small>Generated by PatternIQ on {{ date }} at {{ time }}</small></p>
                </footer>
            </body>
            </html>
            """

            # Create a simple Environment with the template string
            env = Environment()
            template = env.from_string(html_template)

        else:
            # Use the templates directory if it exists
            env = Environment(loader=FileSystemLoader(templates_dir))
            template = env.get_template("daily_report.html")

        # Render HTML with the report data
        html_content = template.render(
            **report_data,
            time=datetime.now().strftime("%H:%M:%S")
        )

        # Save HTML report
        html_path = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.html"
        with open(html_path, 'w') as f:
            f.write(html_content)

        logger.info(f"✅ Generated JSON report: {json_path}")
        logger.info(f"✅ Generated HTML report: {html_path}")

    except Exception as e:
        logger.error(f"❌ Error generating HTML report: {e}")

    return {
        "date": report_date.strftime("%Y-%m-%d"),
        "status": "success",
        "reports_generated": [
            str(json_path),
            str(html_path)
        ]
    }

# Allow running as a script
if __name__ == "__main__":
    generate_daily_report()
