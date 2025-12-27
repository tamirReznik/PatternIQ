# src/report/generator.py - Report generation for PatternIQ

import os
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text

def generate_daily_report(date_str: str = None):
    """
    Generate daily HTML and JSON reports with trading recommendations
    
    This function implements the reporting functionality:
    - Generates a daily report with top long/short recommendations
    - Includes time horizon classification (short/mid/long-term)
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

    # Fetch real signals from database
    try:
        from src.common.db_manager import db_manager
        engine = db_manager.get_engine()
        report_data = _fetch_report_data(engine, report_date, logger)
    except Exception as e:
        logger.warning(f"Could not fetch data from database: {e}. Using sample data.")
        report_data = _generate_sample_data(report_date)

    # Generate JSON report
    json_path = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"
    with open(json_path, 'w') as f:
        json.dump(report_data, f, indent=2)

    # Generate HTML report
    try:
        html_path = _generate_html_report(report_data, reports_dir, report_date, logger)
        logger.info(f"✅ Generated JSON report: {json_path}")
        logger.info(f"✅ Generated HTML report: {html_path}")
    except Exception as e:
        logger.error(f"❌ Error generating HTML report: {e}")
        html_path = None

    return {
        "date": report_date.strftime("%Y-%m-%d"),
        "status": "success",
        "reports_generated": [
            str(json_path),
            str(html_path) if html_path else None
        ]
    }

def _fetch_report_data(engine, report_date: date, logger) -> Dict:
    """Fetch real signal data from database and organize by time horizon"""
    
    # Get combined signals (from blend) or individual signals
    with engine.connect() as conn:
        # Try to get combined signal first
        result = conn.execute(text("""
            SELECT symbol, score, explain
            FROM signals_daily
            WHERE d = :report_date
            AND signal_name = 'combined_ic_weighted'
            ORDER BY score DESC
            LIMIT 50
        """), {"report_date": report_date})
        
        combined_signals = result.fetchall()
        
        # If no combined signals, get individual signals and combine
        if not combined_signals:
            logger.info("No combined signals found, fetching individual signals...")
            result = conn.execute(text("""
                SELECT symbol, signal_name, score, explain
                FROM signals_daily
                WHERE d = :report_date
                AND signal_name IN ('momentum_20_120', 'meanrev_bollinger', 'gap_breakaway')
                ORDER BY symbol, signal_name
            """), {"report_date": report_date})
            
            individual_signals = result.fetchall()
            combined_signals = _combine_individual_signals(individual_signals)
        
        # Get instrument metadata (sector, name)
        symbols = [row[0] for row in combined_signals]
        if not symbols:
            logger.warning("No signals found for report date")
            return _generate_sample_data(report_date)
        
        placeholders = ','.join([f"'{s}'" for s in symbols])
        result = conn.execute(text(f"""
            SELECT symbol, sector, name
            FROM instruments
            WHERE symbol IN ({placeholders})
        """))
        
        instrument_data = {row[0]: {"sector": row[1] or "Unknown", "name": row[2]} 
                          for row in result.fetchall()}
        
        # Get latest prices
        result = conn.execute(text(f"""
            SELECT symbol, adj_c
            FROM bars_1d
            WHERE symbol IN ({placeholders})
            AND t <= :report_date
            ORDER BY symbol, t DESC
        """), {"report_date": report_date})
        
        # Get most recent price per symbol
        price_data = {}
        seen_symbols = set()
        for row in result.fetchall():
            if row[0] not in seen_symbols:
                price_data[row[0]] = float(row[1])
                seen_symbols.add(row[0])
    
    # Organize signals by time horizon
    top_long_short = {"short": [], "mid": [], "long": []}
    top_short_short = {"short": [], "mid": [], "long": []}
    
    for row in combined_signals:
        symbol = row[0]
        score = float(row[1])
        explain_json = row[2] if row[2] else "{}"
        
        try:
            explain = json.loads(explain_json) if isinstance(explain_json, str) else explain_json
            time_horizon = explain.get("time_horizon", "mid")
        except:
            time_horizon = "mid"
        
        sector = instrument_data.get(symbol, {}).get("sector", "Unknown")
        price = price_data.get(symbol, 0.0)
        
        signal_entry = {
            "symbol": symbol,
            "sector": sector,
            "signal": _get_signal_label(score),
            "score": round(score, 3),
            "position_size": _calculate_position_size(score),
            "price": round(price, 2),
            "time_horizon": time_horizon,
            "rationale": _generate_rationale(score, time_horizon)
        }
        
        if score > 0.3:
            top_long_short[time_horizon].append(signal_entry)
        elif score < -0.3:
            top_short_short[time_horizon].append(signal_entry)
    
    # Sort and limit each horizon
    for horizon in ["short", "mid", "long"]:
        top_long_short[horizon].sort(key=lambda x: x["score"], reverse=True)
        top_long_short[horizon] = top_long_short[horizon][:10]
        top_short_short[horizon].sort(key=lambda x: x["score"])
        top_short_short[horizon] = top_short_short[horizon][:5]
    
    # Flatten for backward compatibility
    top_long = (top_long_short["short"] + top_long_short["mid"] + top_long_short["long"])[:10]
    top_short = (top_short_short["short"] + top_short_short["mid"] + top_short_short["long"])[:5]
    
    # Calculate sector scores
    sector_scores = _calculate_sector_scores(top_long + top_short)
    
    return {
        "date": report_date.strftime("%Y-%m-%d"),
        "market_overview": {
            "regime": _determine_market_regime(sector_scores),
            "signal_strength": _calculate_signal_strength(combined_signals),
            "total_recommendations": len(top_long) + len(top_short),
            "high_conviction": len([s for s in top_long if s["score"] > 0.7]),
            "time_horizon_breakdown": {
                "short": len(top_long_short["short"]) + len(top_short_short["short"]),
                "mid": len(top_long_short["mid"]) + len(top_short_short["mid"]),
                "long": len(top_long_short["long"]) + len(top_short_short["long"])
            }
        },
        "top_long": top_long,
        "top_short": top_short,
        "top_long_by_horizon": top_long_short,
        "top_short_by_horizon": top_short_short,
        "sector_scores": sector_scores,
        "risk_alerts": _generate_risk_alerts(report_date),
        "performance": _get_performance_metrics()
    }

def _combine_individual_signals(individual_signals: List) -> List:
    """Combine individual signals into composite scores"""
    signal_dict = {}
    for symbol, signal_name, score, explain in individual_signals:
        if symbol not in signal_dict:
            signal_dict[symbol] = {"scores": [], "explain": explain}
        signal_dict[symbol]["scores"].append(float(score))
    
    # Simple average for now (should use IC weighting)
    combined = []
    for symbol, data in signal_dict.items():
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
        combined.append((symbol, avg_score, data["explain"]))
    
    combined.sort(key=lambda x: x[1], reverse=True)
    return combined

def _get_signal_label(score: float) -> str:
    """Convert score to signal label"""
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

def _calculate_position_size(score: float) -> float:
    """Calculate position size based on signal strength"""
    abs_score = abs(score)
    if abs_score >= 0.7:
        return min(5.0, abs_score * 7.0)
    elif abs_score >= 0.5:
        return min(3.5, abs_score * 6.0)
    else:
        return min(2.0, abs_score * 5.0)

def _generate_rationale(score: float, time_horizon: str) -> str:
    """Generate rationale based on score and time horizon"""
    if time_horizon == "short":
        if score > 0.5:
            return "Strong short-term momentum signal"
        elif score < -0.5:
            return "Weak short-term momentum, potential reversal"
        else:
            return "Moderate short-term signal"
    elif time_horizon == "long":
        if score > 0.5:
            return "Strong long-term trend following signal"
        elif score < -0.5:
            return "Long-term trend weakening"
        else:
            return "Moderate long-term signal"
    else:  # mid
        if score > 0.5:
            return "Balanced momentum and mean reversion signal"
        elif score < -0.5:
            return "Mean reversion opportunity"
        else:
            return "Moderate mid-term signal"

def _calculate_sector_scores(recommendations: List) -> Dict[str, float]:
    """Calculate average score per sector"""
    sector_scores = {}
    sector_counts = {}
    
    for rec in recommendations:
        sector = rec.get("sector", "Unknown")
        score = rec.get("score", 0.0)
        
        if sector not in sector_scores:
            sector_scores[sector] = 0.0
            sector_counts[sector] = 0
        
        sector_scores[sector] += score
        sector_counts[sector] += 1
    
    # Calculate averages
    for sector in sector_scores:
        if sector_counts[sector] > 0:
            sector_scores[sector] = round(sector_scores[sector] / sector_counts[sector], 3)
    
    return sector_scores

def _determine_market_regime(sector_scores: Dict[str, float]) -> str:
    """Determine market regime from sector scores"""
    if not sector_scores:
        return "Neutral Market"
    
    avg_score = sum(sector_scores.values()) / len(sector_scores)
    positive_sectors = len([s for s in sector_scores.values() if s > 0])
    
    if avg_score > 0.15 and positive_sectors > len(sector_scores) * 0.6:
        return "Bullish Market with Broad Strength"
    elif avg_score > 0.05:
        return "Trending Market with Selective Strength"
    elif avg_score < -0.15:
        return "Bearish Market with Broad Weakness"
    else:
        return "Mixed Market Conditions"

def _calculate_signal_strength(signals: List) -> int:
    """Calculate overall signal strength percentage"""
    if not signals:
        return 0
    
    avg_abs_score = sum(abs(float(row[1])) for row in signals) / len(signals)
    return int(avg_abs_score * 100)

def _generate_risk_alerts(report_date: date) -> List[str]:
    """Generate risk alerts for the report"""
    alerts = []
    
    # Check for upcoming earnings (simplified)
    weekday = report_date.weekday()
    if weekday >= 3:  # Thursday or Friday
        alerts.append("Weekend approaching - consider position sizing")
    
    # Generic alerts
    alerts.append("Always use stop-losses appropriate for your time horizon")
    alerts.append("Diversify across sectors and time horizons")
    
    return alerts

def _get_performance_metrics() -> Dict[str, str]:
    """Get performance metrics (placeholder - should fetch from database)"""
    return {
        "yesterday": "N/A",
        "week": "N/A",
        "month": "N/A",
        "year": "N/A",
        "sharpe": "N/A"
    }

def _generate_sample_data(report_date: date) -> Dict:
    """Generate sample data if database fetch fails"""
    return {
        "date": report_date.strftime("%Y-%m-%d"),
        "market_overview": {
            "regime": "Trending Market with Tech Leadership",
            "signal_strength": 82,
            "total_recommendations": 10,
            "high_conviction": 4,
            "time_horizon_breakdown": {"short": 3, "mid": 5, "long": 2}
        },
        "top_long": [
            {
                "symbol": "AAPL",
                "sector": "Technology",
                "signal": "STRONG BUY",
                "score": 0.875,
                "position_size": 3.0,
                "price": 175.50,
                "time_horizon": "mid",
                "rationale": "Strong momentum with recent product launch"
            }
        ],
        "top_short": [],
        "top_long_by_horizon": {"short": [], "mid": [], "long": []},
        "top_short_by_horizon": {"short": [], "mid": [], "long": []},
        "sector_scores": {"Technology": 0.285},
        "risk_alerts": ["Sample data - database connection may be unavailable"],
        "performance": {"yesterday": "N/A", "week": "N/A", "month": "N/A", "year": "N/A", "sharpe": "N/A"}
    }

def _generate_html_report(report_data: Dict, reports_dir: Path, report_date: date, logger) -> Path:
    """Generate HTML report with time horizon sections"""
    
    # Enhanced HTML template with time horizons
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PatternIQ Daily Report - {{ date }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }
            h3 { color: #7f8c8d; margin-top: 20px; }
            .summary { background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .horizon-section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .horizon-short { border-left: 4px solid #e74c3c; background-color: #fdf2f2; }
            .horizon-mid { border-left: 4px solid #f39c12; background-color: #fef9e7; }
            .horizon-long { border-left: 4px solid #27ae60; background-color: #eafaf1; }
            .buy { color: #27ae60; font-weight: bold; }
            .sell { color: #e74c3c; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f2f2f2; font-weight: bold; }
            .time-horizon-badge { display: inline-block; padding: 4px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold; }
            .badge-short { background-color: #e74c3c; color: white; }
            .badge-mid { background-color: #f39c12; color: white; }
            .badge-long { background-color: #27ae60; color: white; }
            .risk { background-color: #ffebee; padding: 15px; border-left: 4px solid #e74c3c; margin: 20px 0; }
            .stats { display: flex; gap: 20px; margin: 20px 0; }
            .stat-box { flex: 1; padding: 15px; background: #f8f9fa; border-radius: 5px; text-align: center; }
            .stat-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
            .stat-label { font-size: 12px; color: #7f8c8d; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PatternIQ Daily Report</h1>
            <p><strong>Date:</strong> {{ date }}</p>
            
            <div class="summary">
                <h2>Market Overview</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-value">{{ market_overview.signal_strength }}%</div>
                        <div class="stat-label">Signal Strength</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{{ market_overview.total_recommendations }}</div>
                        <div class="stat-label">Total Recommendations</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{{ market_overview.high_conviction }}</div>
                        <div class="stat-label">High Conviction</div>
                    </div>
                </div>
                <p><strong>Regime:</strong> {{ market_overview.regime }}</p>
                {% if market_overview.time_horizon_breakdown %}
                <p><strong>Time Horizon Breakdown:</strong>
                    Short: {{ market_overview.time_horizon_breakdown.short }},
                    Mid: {{ market_overview.time_horizon_breakdown.mid }},
                    Long: {{ market_overview.time_horizon_breakdown.long }}
                </p>
                {% endif %}
            </div>
            
            {% if top_long_by_horizon %}
            <h2>Long Recommendations by Time Horizon</h2>
            
            {% if top_long_by_horizon.short %}
            <div class="horizon-section horizon-short">
                <h3>📈 Short-Term (Days to Weeks)</h3>
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
                    {% for stock in top_long_by_horizon.short %}
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
            </div>
            {% endif %}
            
            {% if top_long_by_horizon.mid %}
            <div class="horizon-section horizon-mid">
                <h3>📊 Mid-Term (Weeks to Months)</h3>
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
                    {% for stock in top_long_by_horizon.mid %}
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
            </div>
            {% endif %}
            
            {% if top_long_by_horizon.long %}
            <div class="horizon-section horizon-long">
                <h3>📅 Long-Term (Months to Years)</h3>
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
                    {% for stock in top_long_by_horizon.long %}
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
            </div>
            {% endif %}
            {% endif %}
            
            {% if top_short %}
            <h2>Short Recommendations</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Sector</th>
                    <th>Signal</th>
                    <th>Score</th>
                    <th>Size (%)</th>
                    <th>Price</th>
                    <th>Time Horizon</th>
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
                    <td><span class="time-horizon-badge badge-{{ stock.time_horizon }}">{{ stock.time_horizon|upper }}</span></td>
                    <td>{{ stock.rationale }}</td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}
            
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
            
            <footer>
                <p><small>Generated by PatternIQ on {{ date }} at {{ time }}</small></p>
                <p><small><em>Focus: Passive Income Generation through Intelligent Trading</em></small></p>
            </footer>
        </div>
    </body>
    </html>
    """
    
    env = Environment()
    template = env.from_string(html_template)
    
    html_content = template.render(
        **report_data,
        time=datetime.now().strftime("%H:%M:%S")
    )
    
    html_path = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.html"
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    return html_path

# Allow running as a script
if __name__ == "__main__":
    generate_daily_report()
