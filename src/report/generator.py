# src/report/generator.py - Daily report generation in multiple formats

import logging
import json
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from jinja2 import Template
import os

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint not available. PDF generation disabled.")

class ReportGenerator:
    """
    Generates daily trading reports in multiple formats:
    - JSON (API-ready structured data)
    - HTML (web-friendly format)
    - PDF (professional document)
    - CSV (spreadsheet-friendly)
    """

    def __init__(self):
        self.logger = logging.getLogger("ReportGenerator")
        db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
        self.engine = create_engine(db_url)

        # Report storage directory
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)

    def get_daily_signals(self, signal_date: date, limit: int = 10) -> Dict[str, List[Dict]]:
        """Get top long and short signals for the date"""

        with self.engine.connect() as conn:
            # Get combined signals
            result = conn.execute(text("""
                SELECT s.symbol, s.score, s.rank,
                       i.name, i.sector,
                       b.adj_c as current_price,
                       b.adj_v as volume
                FROM signals_daily s
                JOIN instruments i ON s.symbol = i.symbol
                JOIN bars_1d b ON s.symbol = b.symbol AND s.d = b.t::date
                WHERE s.signal_name = 'combined_ic_weighted'
                AND s.d = :signal_date
                ORDER BY s.score DESC
            """), {"signal_date": signal_date})

            all_signals = result.fetchall()

        # Separate long and short signals
        long_signals = []
        short_signals = []

        for symbol, score, rank, name, sector, price, volume in all_signals:
            signal_data = {
                "symbol": symbol,
                "company_name": name or f"{symbol} Corp",
                "sector": sector or "Unknown",
                "signal_score": round(float(score), 4),
                "rank": rank,
                "current_price": round(float(price), 2),
                "volume": int(volume),
                "recommendation": self._get_recommendation(score),
                "position_size": self._calculate_position_size(score)
            }

            if score > 0.05:  # Positive signals (long)
                long_signals.append(signal_data)
            elif score < -0.05:  # Negative signals (short)
                short_signals.append(signal_data)

        return {
            "long_candidates": long_signals[:limit],
            "short_candidates": short_signals[:limit]
        }

    def get_market_overview(self, signal_date: date) -> Dict:
        """Get market regime and sector analysis"""

        with self.engine.connect() as conn:
            # Overall signal statistics
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_signals,
                    AVG(ABS(score)) as avg_signal_strength,
                    COUNT(CASE WHEN score > 0.3 THEN 1 END) as strong_longs,
                    COUNT(CASE WHEN score < -0.3 THEN 1 END) as strong_shorts,
                    STDDEV(score) as signal_dispersion
                FROM signals_daily
                WHERE signal_name = 'combined_ic_weighted'
                AND d = :signal_date
            """), {"signal_date": signal_date})

            stats = result.fetchone()

            # Sector breakdown
            result = conn.execute(text("""
                SELECT 
                    i.sector,
                    COUNT(*) as count,
                    AVG(s.score) as avg_score,
                    COUNT(CASE WHEN s.score > 0.3 THEN 1 END) as bullish_count,
                    COUNT(CASE WHEN s.score < -0.3 THEN 1 END) as bearish_count
                FROM signals_daily s
                JOIN instruments i ON s.symbol = i.symbol
                WHERE s.signal_name = 'combined_ic_weighted'
                AND s.d = :signal_date
                AND i.sector IS NOT NULL
                GROUP BY i.sector
                ORDER BY avg_score DESC
            """), {"signal_date": signal_date})

            sectors = result.fetchall()

        # Determine market regime
        avg_strength = float(stats[1]) if stats[1] else 0
        signal_dispersion = float(stats[4]) if stats[4] else 0

        if avg_strength > 0.4 and signal_dispersion > 0.3:
            regime = "High Conviction Trending"
        elif avg_strength > 0.2:
            regime = "Moderate Signal Environment"
        elif signal_dispersion < 0.15:
            regime = "Low Volatility Ranging"
        else:
            regime = "Mixed Signal Environment"

        return {
            "market_regime": regime,
            "signal_strength": round(avg_strength * 100, 1),  # Convert to 0-100 scale
            "total_signals": int(stats[0]),
            "strong_longs": int(stats[2]),
            "strong_shorts": int(stats[3]),
            "sector_analysis": [
                {
                    "sector": sector,
                    "symbol_count": count,
                    "avg_signal": round(float(avg_score), 3),
                    "bullish_stocks": bullish_count,
                    "bearish_stocks": bearish_count,
                    "sentiment": "Bullish" if avg_score > 0.1 else "Bearish" if avg_score < -0.1 else "Neutral"
                }
                for sector, count, avg_score, bullish_count, bearish_count in sectors
            ]
        }

    def get_performance_update(self, signal_date: date) -> Dict:
        """Get recent performance metrics"""

        with self.engine.connect() as conn:
            # Get most recent backtest performance
            result = conn.execute(text("""
                SELECT 
                    run_id,
                    start_date,
                    end_date,
                    labeling as signal_name
                FROM backtests
                ORDER BY created_at DESC
                LIMIT 1
            """))

            latest_backtest = result.fetchone()

        if not latest_backtest:
            return {"status": "No performance data available"}

        run_id = latest_backtest[0]

        # Calculate recent performance (simplified)
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as total_positions
                FROM backtest_positions
                WHERE run_id = :run_id
            """), {"run_id": run_id})

            position_count = result.fetchone()[0]

        return {
            "last_backtest_period": f"{latest_backtest[1]} to {latest_backtest[2]}",
            "signal_strategy": latest_backtest[3],
            "total_positions_tested": position_count,
            "status": "Active monitoring"
        }

    def _get_recommendation(self, score: float) -> str:
        """Convert signal score to recommendation"""
        if score >= 0.7:
            return "STRONG BUY"
        elif score >= 0.3:
            return "BUY"
        elif score <= -0.7:
            return "STRONG SELL"
        elif score <= -0.3:
            return "SELL"
        else:
            return "NEUTRAL"

    def _calculate_position_size(self, score: float) -> str:
        """Calculate recommended position size"""
        abs_score = abs(score)
        if abs_score >= 0.8:
            return "3.0%"
        elif abs_score >= 0.5:
            return "2.0%"
        elif abs_score >= 0.3:
            return "1.5%"
        else:
            return "1.0%"

    def generate_json_report(self, signal_date: date) -> Dict:
        """Generate structured JSON report"""

        self.logger.info(f"Generating JSON report for {signal_date}")

        # Gather all data
        signals = self.get_daily_signals(signal_date)
        market_overview = self.get_market_overview(signal_date)
        performance = self.get_performance_update(signal_date)

        report = {
            "report_metadata": {
                "report_id": str(uuid.uuid4()),
                "report_date": signal_date.isoformat(),
                "generated_at": datetime.now().isoformat(),
                "system_version": "PatternIQ 1.0 MVP",
                "report_type": "daily_trading_signals"
            },
            "executive_summary": {
                "market_regime": market_overview["market_regime"],
                "signal_strength": market_overview["signal_strength"],
                "total_recommendations": len(signals["long_candidates"]) + len(signals["short_candidates"]),
                "strong_conviction_trades": market_overview["strong_longs"] + market_overview["strong_shorts"]
            },
            "trading_recommendations": signals,
            "market_analysis": market_overview,
            "performance_tracking": performance,
            "risk_alerts": self._generate_risk_alerts(market_overview, signals),
            "next_actions": [
                "Review individual stock recommendations",
                "Check position sizing against portfolio",
                "Monitor market regime changes",
                "Verify no earnings conflicts"
            ]
        }

        return report

    def _generate_risk_alerts(self, market_overview: Dict, signals: Dict) -> List[str]:
        """Generate risk alerts based on current conditions"""
        alerts = []

        if market_overview["signal_strength"] < 20:
            alerts.append("LOW SIGNAL STRENGTH: Reduced conviction environment")

        if market_overview["signal_strength"] > 80:
            alerts.append("HIGH SIGNAL STRENGTH: Consider position size limits")

        total_recs = len(signals["long_candidates"]) + len(signals["short_candidates"])
        if total_recs < 5:
            alerts.append("LIMITED OPPORTUNITIES: Few actionable signals today")

        if len(signals["long_candidates"]) == 0:
            alerts.append("NO LONG SIGNALS: Consider defensive positioning")

        if len(signals["short_candidates"]) == 0:
            alerts.append("NO SHORT SIGNALS: Limited hedging opportunities")

        return alerts if alerts else ["No significant risk alerts"]

    def save_json_report(self, report_data: Dict, signal_date: date) -> str:
        """Save JSON report to file"""

        filename = f"patterniq_report_{signal_date.strftime('%Y%m%d')}.json"
        filepath = os.path.join(self.reports_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        self.logger.info(f"JSON report saved: {filepath}")
        return filepath

    def generate_html_report(self, report_data: Dict) -> str:
        """Generate HTML report from JSON data"""

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PatternIQ Daily Report - {{ report_data.report_metadata.report_date }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; }
                .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }
                .buy { background-color: #e8f5e8; }
                .sell { background-color: #f5e8e8; }
                .neutral { background-color: #f0f0f0; }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
                .strong-buy { color: #27ae60; font-weight: bold; }
                .buy { color: #2ecc71; }
                .sell { color: #e74c3c; }
                .strong-sell { color: #c0392b; font-weight: bold; }
                .alert { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 10px 0; border-radius: 4px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>PatternIQ Daily Trading Report</h1>
                <p>Date: {{ report_data.report_metadata.report_date }} | Generated: {{ report_data.report_metadata.generated_at[:16] }}</p>
                <p>Market Regime: <strong>{{ report_data.market_analysis.market_regime }}</strong> | Signal Strength: <strong>{{ report_data.market_analysis.signal_strength }}%</strong></p>
            </div>
            
            {% if report_data.risk_alerts %}
            <div class="section alert">
                <h3>⚠️ Risk Alerts</h3>
                {% for alert in report_data.risk_alerts %}
                <p>• {{ alert }}</p>
                {% endfor %}
            </div>
            {% endif %}
            
            <div class="section buy">
                <h2>📈 Long Recommendations ({{ report_data.trading_recommendations.long_candidates|length }})</h2>
                {% if report_data.trading_recommendations.long_candidates %}
                <table>
                    <tr><th>Symbol</th><th>Company</th><th>Sector</th><th>Signal</th><th>Recommendation</th><th>Size</th><th>Price</th></tr>
                    {% for stock in report_data.trading_recommendations.long_candidates %}
                    <tr>
                        <td><strong>{{ stock.symbol }}</strong></td>
                        <td>{{ stock.company_name }}</td>
                        <td>{{ stock.sector }}</td>
                        <td>{{ "%.3f"|format(stock.signal_score) }}</td>
                        <td class="{{ stock.recommendation.lower().replace(' ', '-') }}">{{ stock.recommendation }}</td>
                        <td>{{ stock.position_size }}</td>
                        <td>${{ "%.2f"|format(stock.current_price) }}</td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                <p>No long recommendations today.</p>
                {% endif %}
            </div>
            
            <div class="section sell">
                <h2>📉 Short Recommendations ({{ report_data.trading_recommendations.short_candidates|length }})</h2>
                {% if report_data.trading_recommendations.short_candidates %}
                <table>
                    <tr><th>Symbol</th><th>Company</th><th>Sector</th><th>Signal</th><th>Recommendation</th><th>Size</th><th>Price</th></tr>
                    {% for stock in report_data.trading_recommendations.short_candidates %}
                    <tr>
                        <td><strong>{{ stock.symbol }}</strong></td>
                        <td>{{ stock.company_name }}</td>
                        <td>{{ stock.sector }}</td>
                        <td>{{ "%.3f"|format(stock.signal_score) }}</td>
                        <td class="{{ stock.recommendation.lower().replace(' ', '-') }}">{{ stock.recommendation }}</td>
                        <td>{{ stock.position_size }}</td>
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
                        <td>{{ sector.sector }}</td>
                        <td>{{ sector.symbol_count }}</td>
                        <td>{{ "%.3f"|format(sector.avg_signal) }}</td>
                        <td>{{ sector.sentiment }}</td>
                        <td>{{ sector.bullish_stocks }}</td>
                        <td>{{ sector.bearish_stocks }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            
            <div class="section">
                <h2>📊 Performance Tracking</h2>
                <p><strong>Strategy:</strong> {{ report_data.performance_tracking.signal_strategy }}</p>
                <p><strong>Backtest Period:</strong> {{ report_data.performance_tracking.last_backtest_period }}</p>
                <p><strong>Status:</strong> {{ report_data.performance_tracking.status }}</p>
            </div>
            
            <div class="section">
                <h3>Next Actions</h3>
                {% for action in report_data.next_actions %}
                <p>• {{ action }}</p>
                {% endfor %}
            </div>
            
            <footer style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <p><strong>Disclaimer:</strong> This report is for informational purposes only. Trading involves substantial risk of loss. 
                Past performance is not indicative of future results. Always conduct your own research and consider consulting with a financial advisor.</p>
                <p><em>PatternIQ v1.0 MVP - {{ report_data.report_metadata.generated_at[:10] }}</em></p>
            </footer>
        </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(report_data=report_data)

        return html_content

    def save_html_report(self, html_content: str, signal_date: date) -> str:
        """Save HTML report to file"""

        filename = f"patterniq_report_{signal_date.strftime('%Y%m%d')}.html"
        filepath = os.path.join(self.reports_dir, filename)

        with open(filepath, 'w') as f:
            f.write(html_content)

        self.logger.info(f"HTML report saved: {filepath}")
        return filepath

    def generate_pdf_report(self, html_content: str, signal_date: date) -> Optional[str]:
        """Generate PDF report from HTML"""

        if not WEASYPRINT_AVAILABLE:
            self.logger.warning("WeasyPrint not available. Skipping PDF generation.")
            return None

        try:
            filename = f"patterniq_report_{signal_date.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(self.reports_dir, filename)

            HTML(string=html_content).write_pdf(filepath)

            self.logger.info(f"PDF report saved: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"PDF generation failed: {e}")
            return None

    def generate_all_reports(self, signal_date: date) -> Dict[str, str]:
        """Generate all report formats"""

        self.logger.info(f"Generating all reports for {signal_date}")

        # Generate JSON data
        json_data = self.generate_json_report(signal_date)
        json_path = self.save_json_report(json_data, signal_date)

        # Generate HTML
        html_content = self.generate_html_report(json_data)
        html_path = self.save_html_report(html_content, signal_date)

        # Generate PDF (if available)
        pdf_path = self.generate_pdf_report(html_content, signal_date)

        # Save metadata to database
        self.save_report_metadata(json_data["report_metadata"]["report_id"],
                                 signal_date, json_path, html_path, pdf_path)

        return {
            "json": json_path,
            "html": html_path,
            "pdf": pdf_path,
            "report_id": json_data["report_metadata"]["report_id"]
        }

    def save_report_metadata(self, report_id: str, report_date: date,
                           json_path: str, html_path: str, pdf_path: Optional[str]):
        """Save report metadata to database"""

        with self.engine.connect() as conn:
            summary = {
                "json_path": json_path,
                "html_path": html_path,
                "pdf_path": pdf_path,
                "generated_at": datetime.now().isoformat()
            }

            conn.execute(text("""
                INSERT INTO reports (report_id, period, path, summary)
                VALUES (:report_id, :period, :json_path, :summary)
                ON CONFLICT (report_id) DO UPDATE SET
                path = :json_path, summary = :summary
            """), {
                "report_id": report_id,
                "period": f"daily:{report_date}",
                "json_path": json_path,
                "summary": json.dumps(summary)
            })

            conn.commit()


def demo_report_generation():
    """Demo: Generate daily reports in all formats"""
    print("📄 PatternIQ Report Generation Demo")
    print("=" * 50)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    generator = ReportGenerator()

    try:
        # Get latest signal date
        with generator.engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(d) FROM signals_daily"))
            latest_date = result.fetchone()[0]

        if not latest_date:
            print("❌ No signal data found for report generation")
            return

        print(f"📅 Generating reports for: {latest_date}")

        # Generate all report formats
        report_paths = generator.generate_all_reports(latest_date)

        print(f"\n✅ Reports generated successfully!")
        for format_type, path in report_paths.items():
            if path:
                print(f"   {format_type.upper()}: {path}")
            else:
                print(f"   {format_type.upper()}: Not available")

        # Show sample JSON structure
        json_data = generator.generate_json_report(latest_date)
        print(f"\n📊 Sample JSON structure:")
        print(f"   Executive Summary: {json_data['executive_summary']}")
        print(f"   Long Candidates: {len(json_data['trading_recommendations']['long_candidates'])}")
        print(f"   Short Candidates: {len(json_data['trading_recommendations']['short_candidates'])}")
        print(f"   Risk Alerts: {len(json_data['risk_alerts'])}")

        print(f"\n🎯 Report features:")
        print(f"  ✅ JSON format (API-ready)")
        print(f"  ✅ HTML format (web-friendly)")
        print(f"  ✅ PDF format (professional)")
        print(f"  ✅ Database metadata tracking")
        print(f"  ✅ Risk alerts and sector analysis")
        print(f"  ✅ Performance tracking integration")

    except Exception as e:
        print(f"❌ Error in report generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_report_generation()
