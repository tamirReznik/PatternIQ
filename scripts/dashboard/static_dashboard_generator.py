#!/usr/bin/env python3
"""
Static report generator for PatternIQ
Creates self-contained HTML files that can be viewed without a running server
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
import shutil

class StaticReportGenerator:
    """Generate static HTML reports and dashboard"""

    def __init__(self, output_dir="dashboard_static"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.reports_dir = Path("reports")
        self.trading_dir = Path("trading_data")

    def generate_static_dashboard(self):
        """Generate a static HTML dashboard"""
        print("📊 Generating static dashboard...")

        # Load data
        portfolio = self.load_portfolio_data()
        latest_report = self.load_latest_report()
        available_reports = self.get_available_reports()

        # Generate main dashboard
        dashboard_html = self.create_dashboard_html(portfolio, latest_report, available_reports)

        # Save dashboard
        dashboard_file = self.output_dir / "index.html"
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_html)

        # Copy all reports to dashboard directory
        self.copy_reports()

        # Generate portfolio history
        self.generate_portfolio_history()

        print(f"✅ Static dashboard generated at: {dashboard_file.absolute()}")
        print(f"🌐 Open in browser: file://{dashboard_file.absolute()}")

        return dashboard_file

    def create_dashboard_html(self, portfolio, latest_report, available_reports):
        """Create the main dashboard HTML"""
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>PatternIQ Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; color: #333; background: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .card {{ background: white; border-radius: 12px; padding: 25px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 28px; font-weight: bold; margin-bottom: 5px; }}
        .metric-label {{ font-size: 14px; opacity: 0.9; }}
        .positive {{ background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }}
        .negative {{ background: linear-gradient(135deg, #f44336 0%, #da190b 100%); }}
        .neutral {{ background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); }}
        .portfolio-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .portfolio-table th, .portfolio-table td {{ padding: 15px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        .portfolio-table th {{ background-color: #f8f9fa; font-weight: 600; }}
        .portfolio-table tr:hover {{ background-color: #f8f9fa; }}
        .recommendations {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 20px; }}
        .recommendation {{ padding: 20px; border-radius: 8px; border-left: 5px solid; }}
        .buy {{ background: #e8f5e8; border-left-color: #4CAF50; }}
        .sell {{ background: #ffeaea; border-left-color: #f44336; }}
        .recommendation h4 {{ margin: 0 0 10px 0; color: #333; }}
        .recommendation p {{ margin: 5px 0; color: #666; }}
        .reports-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
        .report-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; }}
        .report-card h4 {{ margin: 0 0 10px 0; color: #333; }}
        .report-link {{ color: #2196F3; text-decoration: none; font-weight: 500; }}
        .report-link:hover {{ text-decoration: underline; }}
        .status-indicator {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
        .status-active {{ background: #4CAF50; }}
        .status-inactive {{ background: #f44336; }}
        .last-updated {{ text-align: center; color: #666; font-size: 14px; margin-top: 20px; }}
        .trade-history {{ margin-top: 20px; }}
        .trade-row {{ display: flex; justify-content: space-between; align-items: center; padding: 12px; margin: 8px 0; border-radius: 6px; background: #f8f9fa; }}
        .trade-buy {{ border-left: 4px solid #4CAF50; }}
        .trade-sell {{ border-left: 4px solid #f44336; }}
        .trade-details {{ flex: 1; }}
        .trade-amount {{ font-weight: bold; color: #333; }}
        .bot-status {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #2196F3; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 PatternIQ Dashboard</h1>
            <p><span class="status-indicator status-active"></span>Last Updated: {last_updated}</p>
        </div>

        <div class="card">
            <h2>💼 Portfolio Performance</h2>
            <div class="metrics">
                <div class="metric {self.get_metric_class(portfolio.get('total_return_num', 0))}">
                    <div class="metric-value">${portfolio.get('current_value', 0):,.0f}</div>
                    <div class="metric-label">Total Value</div>
                </div>
                <div class="metric {self.get_metric_class(portfolio.get('total_return_num', 0))}">
                    <div class="metric-value">{portfolio.get('total_return', '0.00%')}</div>
                    <div class="metric-label">Total Return</div>
                </div>
                <div class="metric neutral">
                    <div class="metric-value">${portfolio.get('cash_balance', 0):,.0f}</div>
                    <div class="metric-label">Cash Balance</div>
                </div>
                <div class="metric neutral">
                    <div class="metric-value">{portfolio.get('positions_count', 0)}</div>
                    <div class="metric-label">Active Positions</div>
                </div>
                <div class="metric neutral">
                    <div class="metric-value">{portfolio.get('total_trades', 0)}</div>
                    <div class="metric-label">Total Trades</div>
                </div>
            </div>

            {self.generate_positions_table(portfolio.get('positions', []))}
            {self.generate_bot_status_section(portfolio)}
            {self.generate_trade_history_section(portfolio)}
        </div>

        {self.generate_latest_report_section(latest_report)}

        <div class="card">
            <h2>📋 Report History</h2>
            <div class="reports-grid">
                {self.generate_reports_grid(available_reports)}
            </div>
        </div>

        <div class="card">
            <h2>📊 Additional Data</h2>
            <p><a href="portfolio_history.html" class="report-link">📈 Portfolio History Chart</a></p>
            <p><a href="latest_report.json" class="report-link">📄 Latest Report (JSON)</a></p>
            <p><a href="portfolio_data.json" class="report-link">💼 Portfolio Data (JSON)</a></p>
        </div>

        <div class="last-updated">
            <p>🔄 Dashboard auto-generates after each PatternIQ batch run</p>
            <p>📱 Bookmark this page for easy access to your trading results</p>
        </div>
    </div>
</body>
</html>
"""

    def get_metric_class(self, value):
        """Get CSS class based on metric value"""
        if value > 0:
            return "positive"
        elif value < 0:
            return "negative"
        else:
            return "neutral"

    def generate_positions_table(self, positions):
        """Generate HTML for positions table"""
        if not positions:
            return "<p>No current positions</p>"

        table_rows = ""
        for pos in positions:
            table_rows += f"""
                <tr>
                    <td><strong>{pos['symbol']}</strong></td>
                    <td>{pos['shares']}</td>
                    <td>${pos['entry_price']}</td>
                    <td>${pos['current_value']}</td>
                    <td>{pos['entry_date']}</td>
                </tr>
            """

        return f"""
            <h3>Current Positions</h3>
            <table class="portfolio-table">
                <thead>
                    <tr><th>Symbol</th><th>Shares</th><th>Entry Price</th><th>Current Value</th><th>Entry Date</th></tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
        """

    def generate_bot_status_section(self, portfolio):
        """Generate HTML for bot status section"""
        # Load raw portfolio data to get more details
        portfolio_file = self.trading_dir / "portfolio_state.json"
        bot_info = {}

        if portfolio_file.exists():
            try:
                with open(portfolio_file, 'r') as f:
                    data = json.load(f)
                bot_info = {
                    'paper_trading': data.get('paper_trading', True),
                    'last_updated': data.get('last_updated', 'Unknown'),
                    'start_date': data.get('start_date', 'Unknown')
                }
            except:
                pass

        status_icon = "📝" if bot_info.get('paper_trading', True) else "💰"
        trading_mode = "Paper Trading" if bot_info.get('paper_trading', True) else "Live Trading"

        return f"""
        <div class="bot-status">
            <h3>🤖 Trading Bot Status</h3>
            <p><strong>Mode:</strong> {status_icon} {trading_mode}</p>
            <p><strong>Started:</strong> {bot_info.get('start_date', 'Unknown')}</p>
            <p><strong>Last Updated:</strong> {bot_info.get('last_updated', 'Unknown')}</p>
            <p><strong>Total Trades:</strong> {portfolio.get('total_trades', 0)}</p>
            <p><strong>Active Positions:</strong> {portfolio.get('positions_count', 0)}</p>
        </div>
        """

    def generate_trade_history_section(self, portfolio):
        """Generate HTML for trade history section"""
        # Load raw portfolio data to get trade history
        portfolio_file = self.trading_dir / "portfolio_state.json"
        trades = []

        if portfolio_file.exists():
            try:
                with open(portfolio_file, 'r') as f:
                    data = json.load(f)
                trades = data.get('trade_history', [])
            except:
                pass

        if not trades:
            return """
            <div class="trade-history">
                <h3>📈 Trade History</h3>
                <p>🎯 No trades executed yet. The bot will start trading when it finds suitable opportunities based on the daily reports.</p>
                <p>💡 <strong>Why no trades yet?</strong> The bot is configured to process yesterday's report (Oct 3rd), but it's looking for today's report (Oct 4th). This is the expected behavior we discussed - the bot trades the day after analysis.</p>
            </div>
            """

        trade_rows = ""
        for trade in trades[-10:]:  # Show last 10 trades
            action_class = "trade-buy" if trade.get('action') == 'BUY' else "trade-sell"
            pnl = trade.get('pnl', 0)
            pnl_color = "color: #4CAF50;" if pnl >= 0 else "color: #f44336;"

            trade_rows += f"""
                <div class="trade-row {action_class}">
                    <div class="trade-details">
                        <div><strong>{trade.get('action', 'N/A')}:</strong> {trade.get('symbol', 'N/A')}</div>
                        <div><strong>Shares:</strong> {trade.get('shares', 0)}</div>
                        <div><strong>Price:</strong> ${trade.get('price', 0):.2f}</div>
                        <div><strong>Date:</strong> {trade.get('date', 'Unknown')}</div>
                    </div>
                    <div class="trade-amount" style="{pnl_color}">
                        ${trade.get('amount', 0):,.2f}
                        {f'(P&L: ${pnl:,.2f})' if 'pnl' in trade else ''}
                    </div>
                </div>
            """

        return f"""
        <div class="trade-history">
            <h3>📈 Recent Trade History</h3>
            {trade_rows}
        </div>
        """

    def generate_latest_report_section(self, report):
        """Generate HTML for latest report section"""
        if not report:
            return '<div class="card"><h2>📈 Latest Analysis</h2><p>No reports available</p></div>'

        recommendations_html = ""

        # Long recommendations
        for rec in report.get('top_long', []):
            recommendations_html += f"""
                <div class="recommendation buy">
                    <h4>{rec['symbol']} - {rec['signal']}</h4>
                    <p><strong>Sector:</strong> {rec['sector']}</p>
                    <p><strong>Score:</strong> {rec['score']*100:.1f}%</p>
                    <p><strong>Target Size:</strong> {rec['position_size']}%</p>
                    <p><strong>Price:</strong> ${rec['price']}</p>
                </div>
            """

        # Short recommendations
        for rec in report.get('top_short', []):
            recommendations_html += f"""
                <div class="recommendation sell">
                    <h4>{rec['symbol']} - SELL</h4>
                    <p><strong>Sector:</strong> {rec['sector']}</p>
                    <p><strong>Score:</strong> {rec['score']*100:.1f}%</p>
                    <p><strong>Price:</strong> ${rec['price']}</p>
                </div>
            """

        market_sentiment = report.get('market_sentiment', {})

        return f"""
        <div class="card">
            <h2>📈 Latest Market Analysis</h2>
            <p><strong>Report Date:</strong> {report.get('date', 'Unknown')}</p>
            <p><strong>Market Sentiment:</strong> {market_sentiment.get('overall_signal', 'N/A')} 
               ({market_sentiment.get('signal_strength', 0)*100:.1f}% confidence)</p>
            
            <h3>🎯 Current Recommendations</h3>
            <div class="recommendations">
                {recommendations_html}
            </div>
        </div>
        """

    def generate_reports_grid(self, reports):
        """Generate HTML for reports grid"""
        grid_html = ""
        for report in reports:
            grid_html += f"""
                <div class="report-card">
                    <h4>📊 {report['date']}</h4>
                    <p><a href="reports/{report['filename']}" class="report-link">View JSON Report</a></p>
                    <p><a href="reports/{report['filename'].replace('.json', '.html')}" class="report-link">View HTML Report</a></p>
                </div>
            """
        return grid_html

    def copy_reports(self):
        """Copy all reports to dashboard directory"""
        reports_output = self.output_dir / "reports"
        reports_output.mkdir(exist_ok=True)

        if self.reports_dir.exists():
            for report_file in self.reports_dir.glob("*"):
                shutil.copy2(report_file, reports_output)

    def generate_portfolio_history(self):
        """Generate portfolio history page"""
        # This is a simplified version - in a real implementation you'd track historical data
        portfolio = self.load_portfolio_data()

        history_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Portfolio History - PatternIQ</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 12px; padding: 25px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .back-link {{ color: #2196F3; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>📈 Portfolio History</h1>
            <p><a href="index.html" class="back-link">← Back to Dashboard</a></p>
            
            <h3>Current Status</h3>
            <p><strong>Total Value:</strong> ${portfolio.get('current_value', 0):,.2f}</p>
            <p><strong>Total Return:</strong> {portfolio.get('total_return', '0.00%')}</p>
            <p><strong>Cash Balance:</strong> ${portfolio.get('cash_balance', 0):,.2f}</p>
            
            <h3>Trade History</h3>
            <p>Trade history will be displayed here as the bot executes more trades.</p>
            
            <h3>Performance Chart</h3>
            <p>Performance charts will be added as historical data accumulates.</p>
        </div>
    </div>
</body>
</html>
        """

        with open(self.output_dir / "portfolio_history.html", 'w') as f:
            f.write(history_html)

    def load_portfolio_data(self):
        """Load portfolio data (same as dashboard.py)"""
        portfolio_file = self.trading_dir / "portfolio_state.json"

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

            # Save portfolio data as JSON for API access
            with open(self.output_dir / "portfolio_data.json", 'w') as f:
                json.dump(data, f, indent=2)

            # Calculate portfolio metrics (same logic as dashboard.py)
            positions_value = 0
            positions_list = []

            for symbol, pos_data in data.get('positions', {}).items():
                shares = pos_data['shares']
                entry_price = pos_data['entry_price']
                current_value = shares * entry_price
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

    def load_latest_report(self):
        """Load latest report (same as dashboard.py)"""
        if not self.reports_dir.exists():
            return None

        json_reports = list(self.reports_dir.glob("*.json"))
        if not json_reports:
            return None

        latest_report = max(json_reports, key=lambda x: x.stat().st_mtime)

        try:
            with open(latest_report, 'r') as f:
                report_data = json.load(f)

            # Save latest report as JSON for API access
            with open(self.output_dir / "latest_report.json", 'w') as f:
                json.dump(report_data, f, indent=2)

            return report_data
        except Exception as e:
            print(f"Error loading report: {e}")
            return None

    def get_available_reports(self):
        """Get available reports (same as dashboard.py)"""
        if not self.reports_dir.exists():
            return []

        reports = []
        for json_file in sorted(self.reports_dir.glob("*.json"), reverse=True):
            filename = json_file.name
            if filename.startswith("patterniq_report_"):
                date_str = filename.replace("patterniq_report_", "").replace(".json", "")
                try:
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

if __name__ == "__main__":
    generator = StaticReportGenerator()
    dashboard_file = generator.generate_static_dashboard()

    print("\\n🎯 Static Dashboard Generated!")
    print(f"📁 Location: {dashboard_file}")
    print(f"🌐 Open in browser: file://{dashboard_file.absolute()}")
    print("\\n💡 Tip: Bookmark this file in your browser for easy access!")
