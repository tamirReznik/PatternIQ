#!/usr/bin/env python3
"""
Report Generator for Retrospective Simulation
Generates detailed reports in JSON, CSV, and HTML formats
"""

import logging
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import date
import pandas as pd


class ReportGenerator:
    """
    Generates comprehensive reports for retrospective simulations
    """
    
    def __init__(self, output_dir: str = "reports/retrospective"):
        self.logger = logging.getLogger("ReportGenerator")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(self, simulation_results: Dict, filename: Optional[str] = None) -> Path:
        """Generate JSON report"""
        if not filename:
            start_date = simulation_results['simulation_period']['start']
            end_date = simulation_results['simulation_period']['end']
            filename = f"retrospective_{start_date}_{end_date}.json"
        
        filepath = self.output_dir / filename
        
        # Add per-symbol trades if available (ensure dates are serialized as strings)
        if 'per_symbol_trades' in simulation_results:
            for trade in simulation_results['per_symbol_trades']:
                if 'trade_details' in trade:
                    for detail in trade['trade_details']:
                        if 'buy_date' in detail and hasattr(detail['buy_date'], 'isoformat'):
                            detail['buy_date'] = detail['buy_date'].isoformat()
                        if 'sell_date' in detail and hasattr(detail['sell_date'], 'isoformat'):
                            detail['sell_date'] = detail['sell_date'].isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(simulation_results, f, indent=2, default=str)
        
        self.logger.info(f"Generated JSON report: {filepath}")
        return filepath
    
    def generate_csv_report(self, simulation_results: Dict, filename: Optional[str] = None) -> Path:
        """Generate CSV report with daily decisions and portfolio values"""
        if not filename:
            start_date = simulation_results['simulation_period']['start']
            end_date = simulation_results['simulation_period']['end']
            filename = f"retrospective_{start_date}_{end_date}.csv"
        
        filepath = self.output_dir / filename
        
        # Create DataFrame from daily portfolio values
        portfolio_df = pd.DataFrame(simulation_results['daily_portfolio_values'])
        
        # Add profitability metrics as summary rows
        profitability = simulation_results['profitability_metrics']
        summary_rows = pd.DataFrame([{
            'date': 'SUMMARY',
            'portfolio_value': profitability['final_capital'],
            'cash_balance': 'N/A',
            'positions_count': 'N/A',
            'total_return': profitability['total_return'],
            'annualized_return': profitability['annualized_return'],
            'sharpe_ratio': profitability['sharpe_ratio'],
            'max_drawdown': profitability['max_drawdown'],
            'win_rate': profitability['win_rate']
        }])
        
        portfolio_df = pd.concat([portfolio_df, summary_rows], ignore_index=True)
        
        # Add per-symbol trades section if available
        if 'per_symbol_trades' in simulation_results and simulation_results['per_symbol_trades']:
            # Create per-symbol trades DataFrame
            trades_data = []
            for trade in simulation_results['per_symbol_trades']:
                trades_data.append({
                    'Symbol': trade['symbol'],
                    'First Buy Date': trade['first_buy_date'],
                    'Last Sell Date': trade['last_sell_date'] if not trade['is_still_open'] else 'Still Open',
                    'Number of Trades': trade['num_trades'],
                    'Total Profit ($)': f"${trade['total_profit']:,.2f}",
                    'Total Profit (%)': f"{trade['total_profit_percent']:.2%}",
                    'Avg Holding Period (days)': f"{trade['avg_holding_period']:.1f}"
                })
            
            trades_df = pd.DataFrame(trades_data)
            
            # Write both DataFrames to CSV (separate sections)
            with open(filepath, 'w') as f:
                f.write("=== Daily Portfolio Values ===\n")
                portfolio_df.to_csv(f, index=False)
                f.write("\n\n=== Per-Symbol Trade Summary ===\n")
                trades_df.to_csv(f, index=False)
        else:
            portfolio_df.to_csv(filepath, index=False)
        
        self.logger.info(f"Generated CSV report: {filepath}")
        return filepath
    
    def generate_html_report(self, simulation_results: Dict, filename: Optional[str] = None) -> Path:
        """Generate HTML report with charts and analysis"""
        if not filename:
            start_date = simulation_results['simulation_period']['start']
            end_date = simulation_results['simulation_period']['end']
            filename = f"retrospective_{start_date}_{end_date}.html"
        
        filepath = self.output_dir / filename
        
        profitability = simulation_results['profitability_metrics']
        decision_quality = simulation_results['decision_quality_metrics']
        simulation_period = simulation_results['simulation_period']
        per_symbol_trades = simulation_results.get('per_symbol_trades', [])
        
        # Generate per-symbol trades table rows
        per_symbol_trades_rows = ""
        if per_symbol_trades:
            for trade in per_symbol_trades:
                profit_class = "positive" if trade['total_profit'] >= 0 else "negative"
                profit_sign = "+" if trade['total_profit'] >= 0 else ""
                profit_percent_sign = "+" if trade['total_profit_percent'] >= 0 else ""
                last_sell = trade['last_sell_date'] if not trade['is_still_open'] else '<em>Still Open</em>'
                
                per_symbol_trades_rows += f"""
            <tr>
                <td><strong>{trade['symbol']}</strong></td>
                <td>{trade['first_buy_date']}</td>
                <td>{last_sell}</td>
                <td>{trade['num_trades']}</td>
                <td class="{profit_class}">{profit_sign}${trade['total_profit']:,.2f}</td>
                <td class="{profit_class}">{profit_percent_sign}{trade['total_profit_percent']:.2%}</td>
                <td>{trade['avg_holding_period']:.1f}</td>
            </tr>
                """
        else:
            per_symbol_trades_rows = "<tr><td colspan='7'>No trades executed</td></tr>"
        
        # Generate detailed transaction history
        all_transactions = []
        for trade in per_symbol_trades:
            symbol = trade['symbol']
            trade_details = trade.get('trade_details', [])
            for detail in trade_details:
                all_transactions.append({
                    'date': detail.get('buy_date', ''),
                    'symbol': symbol,
                    'action': 'BUY',
                    'profit': None,
                    'profit_percent': None
                })
                if 'sell_date' in detail:
                    all_transactions.append({
                        'date': detail.get('sell_date', ''),
                        'symbol': symbol,
                        'action': 'SELL',
                        'profit': detail.get('profit', 0),
                        'profit_percent': detail.get('profit_percent', 0)
                    })
        
        # Sort transactions by date
        all_transactions.sort(key=lambda x: x['date'])
        
        # Generate transaction history table rows
        transaction_rows = ""
        if all_transactions:
            for trans in all_transactions:
                action_class = "buy" if trans['action'] == 'BUY' else "sell"
                profit_cell = ""
                if trans['profit'] is not None:
                    profit_class = "positive" if trans['profit'] >= 0 else "negative"
                    profit_sign = "+" if trans['profit'] >= 0 else ""
                    profit_cell = f'<td class="{profit_class}">{profit_sign}${trans["profit"]:,.2f}</td><td class="{profit_class}">{profit_sign}{trans["profit_percent"]:.2%}</td>'
                else:
                    profit_cell = '<td>-</td><td>-</td>'
                
                transaction_rows += f"""
            <tr>
                <td>{trans['date']}</td>
                <td><strong>{trans['symbol']}</strong></td>
                <td class="{action_class}">{trans['action']}</td>
                {profit_cell}
            </tr>
                """
        else:
            transaction_rows = "<tr><td colspan='5'>No transactions recorded</td></tr>"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PatternIQ Retrospective Simulation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .metric-label {{ font-size: 12px; color: #666; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4CAF50; color: white; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
        .trade-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .trade-table th {{
            background-color: #1976d2;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        .trade-table td {{
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .trade-table tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <h1>PatternIQ Retrospective Simulation Report</h1>
    
    <h2>Simulation Period</h2>
    <p><strong>Start:</strong> {simulation_period['start']}</p>
    <p><strong>End:</strong> {simulation_period['end']}</p>
    <p><strong>Trading Days:</strong> {simulation_period['trading_days']}</p>
    
    <h2>Profitability Metrics</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-label">Total Return</div>
            <div class="metric-value {'positive' if profitability['total_return'] > 0 else 'negative'}">
                {profitability['total_return']:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Annualized Return</div>
            <div class="metric-value {'positive' if profitability['annualized_return'] > 0 else 'negative'}">
                {profitability['annualized_return']:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value">
                {profitability['sharpe_ratio']:.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value negative">
                {profitability['max_drawdown']:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value">
                {profitability['win_rate']:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Profit Factor</div>
            <div class="metric-value">
                {profitability['profit_factor']:.2f}
            </div>
        </div>
    </div>
    
    <h2>Per-Symbol Trade Summary</h2>
    <table class="trade-table">
        <thead>
            <tr>
                <th>Symbol</th>
                <th>First Buy Date</th>
                <th>Last Sell Date</th>
                <th>Trades</th>
                <th>Total Profit ($)</th>
                <th>Total Profit (%)</th>
                <th>Avg Holding (days)</th>
            </tr>
        </thead>
        <tbody>
            {per_symbol_trades_rows}
        </tbody>
    </table>
    
    <h2>Decision Quality Metrics</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-label">Decision Accuracy</div>
            <div class="metric-value">
                {decision_quality['accuracy']:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Signal Correlation</div>
            <div class="metric-value">
                {decision_quality['signal_correlation']:.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">False Positive Rate</div>
            <div class="metric-value negative">
                {decision_quality['false_positive_rate']:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">False Negative Rate</div>
            <div class="metric-value negative">
                {decision_quality['false_negative_rate']:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Timing Quality</div>
            <div class="metric-value">
                {decision_quality['timing_quality']:.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Decisions</div>
            <div class="metric-value">
                {decision_quality['total_decisions']}
            </div>
        </div>
    </div>
    
    <h2>Portfolio Performance</h2>
    <p><strong>Initial Capital:</strong> ${profitability['initial_capital']:,.2f}</p>
    <p><strong>Final Capital:</strong> ${profitability['final_capital']:,.2f}</p>
    <p><strong>Total Trades:</strong> {profitability['total_trades']}</p>
    <p><strong>Average Holding Period:</strong> {profitability['average_holding_period']:.1f} days</p>
    
    <h2>Detailed Transaction History</h2>
    <p>Chronological list of all buy and sell transactions:</p>
    <table class="trade-table">
        <thead>
            <tr>
                <th>Date</th>
                <th>Symbol</th>
                <th>Action</th>
                <th>Profit ($)</th>
                <th>Profit (%)</th>
            </tr>
        </thead>
        <tbody>
            {transaction_rows}
        </tbody>
    </table>
    <style>
        .buy {{ color: #4CAF50; font-weight: bold; }}
        .sell {{ color: #f44336; font-weight: bold; }}
    </style>
    
    <h2>Daily Decisions Summary</h2>
    <p>Total trading days: {len(simulation_results['daily_decisions'])}</p>
    <p>See CSV export for detailed day-by-day breakdown.</p>
</body>
</html>
        """
        
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Generated HTML report: {filepath}")
        return filepath
    
    def generate_all_reports(self, simulation_results: Dict) -> Dict[str, Path]:
        """Generate all report formats"""
        reports = {}
        
        reports['json'] = self.generate_json_report(simulation_results)
        reports['csv'] = self.generate_csv_report(simulation_results)
        reports['html'] = self.generate_html_report(simulation_results)
        
        return reports

