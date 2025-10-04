#!/usr/bin/env python3
"""
Simple web dashboard to view PatternIQ reports and portfolio status
Run this to access your reports via web browser
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from flask import Flask, render_template_string, jsonify, send_file
import sqlite3

app = Flask(__name__)

# HTML template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PatternIQ Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; color: #333; }
        .metric { display: inline-block; margin: 10px; padding: 15px; background: #e8f4fd; border-radius: 5px; min-width: 150px; text-align: center; }
        .metric-value { font-size: 24px; font-weight: bold; color: #2196F3; }
        .metric-label { font-size: 14px; color: #666; }
        .positive { color: #4CAF50; }
        .negative { color: #f44336; }
        .portfolio-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .portfolio-table th, .portfolio-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .portfolio-table th { background-color: #f8f9fa; }
        .recommendations { display: flex; flex-wrap: wrap; gap: 15px; }
        .recommendation { background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid; min-width: 200px; }
        .buy { border-left-color: #4CAF50; }
        .sell { border-left-color: #f44336; }
        .btn { padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px; }
        .btn:hover { background: #1976D2; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 PatternIQ Dashboard</h1>
            <p>Last Updated: {{ last_updated }}</p>
        </div>

        <div class="card">
            <h2>📊 Portfolio Status</h2>
            <div>
                <div class="metric">
                    <div class="metric-value">${{ portfolio.current_value | round(2) | string | replace('.0', '') }}</div>
                    <div class="metric-label">Total Value</div>
                </div>
                <div class="metric">
                    <div class="metric-value {{ 'positive' if portfolio.total_return_num >= 0 else 'negative' }}">{{ portfolio.total_return }}</div>
                    <div class="metric-label">Total Return</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${{ portfolio.cash_balance | round(2) | string | replace('.0', '') }}</div>
                    <div class="metric-label">Cash Balance</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ portfolio.positions_count }}</div>
                    <div class="metric-label">Positions</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ portfolio.total_trades }}</div>
                    <div class="metric-label">Total Trades</div>
                </div>
            </div>

            {% if portfolio.positions %}
            <h3>Current Positions</h3>
            <table class="portfolio-table">
                <thead>
                    <tr><th>Symbol</th><th>Shares</th><th>Entry Price</th><th>Current Value</th><th>Entry Date</th></tr>
                </thead>
                <tbody>
                {% for pos in portfolio.positions %}
                    <tr>
                        <td><strong>{{ pos.symbol }}</strong></td>
                        <td>{{ pos.shares }}</td>
                        <td>${{ pos.entry_price }}</td>
                        <td>${{ pos.current_value }}</td>
                        <td>{{ pos.entry_date }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
            {% endif %}
        </div>

        {% if latest_report %}
        <div class="card">
            <h2>📈 Latest Market Analysis</h2>
            <p><strong>Report Date:</strong> {{ latest_report.date }}</p>
            <p><strong>Market Sentiment:</strong> {{ latest_report.market_sentiment.overall_signal }} ({{ (latest_report.market_sentiment.signal_strength * 100) | round(1) }}% confidence)</p>
            
            <h3>🎯 Current Recommendations</h3>
            <div class="recommendations">
                {% for rec in latest_report.top_long %}
                <div class="recommendation buy">
                    <h4>{{ rec.symbol }} - {{ rec.signal }}</h4>
                    <p><strong>Sector:</strong> {{ rec.sector }}</p>
                    <p><strong>Score:</strong> {{ (rec.score * 100) | round(1) }}%</p>
                    <p><strong>Target Size:</strong> {{ rec.position_size }}%</p>
                    <p><strong>Price:</strong> ${{ rec.price }}</p>
                </div>
                {% endfor %}
                {% for rec in latest_report.top_short %}
                <div class="recommendation sell">
                    <h4>{{ rec.symbol }} - SELL</h4>
                    <p><strong>Sector:</strong> {{ rec.sector }}</p>
                    <p><strong>Score:</strong> {{ (rec.score * 100) | round(1) }}%</p>
                    <p><strong>Price:</strong> ${{ rec.price }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="card">
            <h2>📋 Available Reports</h2>
            {% for report in available_reports %}
                <a href="/report/{{ report.filename }}" class="btn">{{ report.date }} Report</a>
            {% endfor %}
        </div>

        <div class="card">
            <h2>🔄 Actions</h2>
            <a href="/api/portfolio" class="btn">Portfolio JSON</a>
            <a href="/api/latest-report" class="btn">Latest Report JSON</a>
            <a href="/" class="btn">Refresh Dashboard</a>
        </div>
    </div>

    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => location.reload(), 300000);
    </script>
</body>
</html>
"""

def load_portfolio_data():
    """Load current portfolio status"""
    portfolio_file = Path("trading_data/portfolio_state.json")

    if not portfolio_file.exists():
        return {
            "current_value": 100000,
            "total_return": "0.00%",
            "total_return_num": 0,
            "cash_balance": 100000,
            "positions_count": 0,
            "total_trades": 0,
            "positions": []
        }

    try:
        with open(portfolio_file, 'r') as f:
            data = json.load(f)

        # Calculate current portfolio value
        positions_value = 0
        positions_list = []

        for symbol, pos_data in data.get('positions', {}).items():
            shares = pos_data['shares']
            entry_price = pos_data['entry_price']
            current_value = shares * entry_price  # In real system, use current market price
            positions_value += current_value

            positions_list.append({
                'symbol': symbol,
                'shares': shares,
                'entry_price': f"{entry_price:.2f}",
                'current_value': f"{current_value:.2f}",
                'entry_date': pos_data['entry_date']
            })

        current_value = data.get('cash_balance', 0) + positions_value
        initial_capital = data.get('initial_capital', 100000)
        total_return_num = (current_value - initial_capital) / initial_capital * 100

        return {
            "current_value": current_value,
            "total_return": f"{total_return_num:+.2f}%",
            "total_return_num": total_return_num,
            "cash_balance": data.get('cash_balance', 0),
            "positions_count": len(data.get('positions', {})),
            "total_trades": len(data.get('trade_history', [])),
            "positions": positions_list
        }

    except Exception as e:
        print(f"Error loading portfolio: {e}")
        return {"error": str(e)}

def load_latest_report():
    """Load the most recent report"""
    reports_dir = Path("reports")

    if not reports_dir.exists():
        return None

    json_reports = list(reports_dir.glob("*.json"))
    if not json_reports:
        return None

    # Get the most recent report
    latest_report = max(json_reports, key=lambda x: x.stat().st_mtime)

    try:
        with open(latest_report, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading report: {e}")
        return None

def get_available_reports():
    """Get list of available reports"""
    reports_dir = Path("reports")

    if not reports_dir.exists():
        return []

    reports = []
    for json_file in sorted(reports_dir.glob("*.json"), reverse=True):
        # Extract date from filename
        filename = json_file.name
        if filename.startswith("patterniq_report_"):
            date_str = filename.replace("patterniq_report_", "").replace(".json", "")
            try:
                # Convert YYYYMMDD to YYYY-MM-DD
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                reports.append({
                    "filename": filename,
                    "date": formatted_date
                })
            except:
                reports.append({
                    "filename": filename,
                    "date": "Unknown"
                })

    return reports

@app.route('/')
def dashboard():
    """Main dashboard page"""
    portfolio = load_portfolio_data()
    latest_report = load_latest_report()
    available_reports = get_available_reports()

    return render_template_string(
        DASHBOARD_TEMPLATE,
        portfolio=portfolio,
        latest_report=latest_report,
        available_reports=available_reports,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

@app.route('/api/portfolio')
def api_portfolio():
    """API endpoint for portfolio data"""
    return jsonify(load_portfolio_data())

@app.route('/api/latest-report')
def api_latest_report():
    """API endpoint for latest report"""
    report = load_latest_report()
    if report:
        return jsonify(report)
    else:
        return jsonify({"error": "No reports found"}), 404

@app.route('/report/<filename>')
def view_report(filename):
    """View specific report file"""
    reports_dir = Path("reports")
    report_file = reports_dir / filename

    if not report_file.exists():
        return "Report not found", 404

    # If it's an HTML file, serve it directly
    if filename.endswith('.html'):
        return send_file(report_file)

    # If it's JSON, return as JSON response
    if filename.endswith('.json'):
        try:
            with open(report_file, 'r') as f:
                return jsonify(json.load(f))
        except Exception as e:
            return f"Error loading report: {e}", 500

    return "Unsupported file type", 400

if __name__ == '__main__':
    print("🌐 Starting PatternIQ Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔄 Dashboard auto-refreshes every 5 minutes")
    print("📱 Access from any device on your network")

    # Change to the PatternIQ directory if running from elsewhere
    if not Path("reports").exists() and not Path("trading_data").exists():
        print("⚠️  Warning: reports and trading_data directories not found")
        print("   Make sure you're running this from the PatternIQ directory")

    app.run(host='0.0.0.0', port=5000, debug=False)
