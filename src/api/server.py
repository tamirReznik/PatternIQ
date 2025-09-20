# src/api/server.py - FastAPI server for PatternIQ reports and trading data

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
import os
import json
from sqlalchemy import create_engine, text

from src.report.generator import ReportGenerator

app = FastAPI(
    title="PatternIQ API",
    description="Advanced Quantitative Trading System API",
    version="1.0.0"
)

# Initialize components
report_generator = ReportGenerator()
db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
engine = create_engine(db_url)

@app.get("/")
async def root():
    """API health check"""
    return {
        "service": "PatternIQ API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": [
            "/reports/daily/{date}",
            "/reports/latest",
            "/signals/{date}",
            "/portfolio/status",
            "/trading/performance"
        ]
    }

@app.get("/reports/latest")
async def get_latest_report(format: str = Query("json", regex="^(json|html|pdf)$")):
    """Get the latest daily report in specified format"""

    try:
        # Get latest report date
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(d) FROM signals_daily"))
            latest_date = result.fetchone()[0]

        if not latest_date:
            raise HTTPException(status_code=404, detail="No reports available")

        return await get_daily_report(latest_date, format)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest report: {str(e)}")

@app.get("/reports/daily/{report_date}")
async def get_daily_report(report_date: date, format: str = Query("json", regex="^(json|html|pdf)$")):
    """Get daily report for specific date"""

    try:
        if format == "json":
            # Generate fresh JSON data
            json_data = report_generator.generate_json_report(report_date)
            return JSONResponse(content=json_data)

        elif format == "html":
            # Check if HTML file exists, generate if not
            filename = f"patterniq_report_{report_date.strftime('%Y%m%d')}.html"
            filepath = os.path.join(report_generator.reports_dir, filename)

            if not os.path.exists(filepath):
                json_data = report_generator.generate_json_report(report_date)
                html_content = report_generator.generate_html_report(json_data)
                report_generator.save_html_report(html_content, report_date)

            return FileResponse(filepath, media_type="text/html", filename=filename)

        elif format == "pdf":
            # Check if PDF file exists, generate if not
            filename = f"patterniq_report_{report_date.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(report_generator.reports_dir, filename)

            if not os.path.exists(filepath):
                json_data = report_generator.generate_json_report(report_date)
                html_content = report_generator.generate_html_report(json_data)
                pdf_path = report_generator.generate_pdf_report(html_content, report_date)

                if not pdf_path:
                    raise HTTPException(status_code=503, detail="PDF generation not available")

            return FileResponse(filepath, media_type="application/pdf", filename=filename)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@app.get("/signals/{signal_date}")
async def get_signals(signal_date: date, signal_type: str = Query("combined", regex="^(combined|momentum|meanrev|gap|all)$")):
    """Get trading signals for specific date"""

    try:
        with engine.connect() as conn:
            if signal_type == "all":
                query = """
                    SELECT signal_name, symbol, score, rank
                    FROM signals_daily
                    WHERE d = :signal_date
                    ORDER BY signal_name, rank
                """
            else:
                signal_name_map = {
                    "combined": "combined_ic_weighted",
                    "momentum": "momentum_20_120",
                    "meanrev": "meanrev_bollinger",
                    "gap": "gap_breakaway"
                }

                query = """
                    SELECT signal_name, symbol, score, rank
                    FROM signals_daily
                    WHERE d = :signal_date AND signal_name = :signal_name
                    ORDER BY rank
                """

            result = conn.execute(text(query), {
                "signal_date": signal_date,
                "signal_name": signal_name_map.get(signal_type, signal_type)
            })

            signals = result.fetchall()

        if not signals:
            raise HTTPException(status_code=404, detail=f"No signals found for {signal_date}")

        # Format response
        formatted_signals = []
        for signal_name, symbol, score, rank in signals:
            formatted_signals.append({
                "signal_type": signal_name,
                "symbol": symbol,
                "score": round(float(score), 4),
                "rank": rank,
                "recommendation": _get_recommendation(score),
                "position_size": _calculate_position_size(score)
            })

        return {
            "date": signal_date.isoformat(),
            "signal_type": signal_type,
            "total_signals": len(formatted_signals),
            "signals": formatted_signals
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving signals: {str(e)}")

@app.get("/portfolio/status")
async def get_portfolio_status():
    """Get current portfolio status and performance"""

    try:
        with engine.connect() as conn:
            # Get latest backtest run
            result = conn.execute(text("""
                SELECT run_id, start_date, end_date, labeling, created_at
                FROM backtests
                ORDER BY created_at DESC
                LIMIT 1
            """))

            latest_run = result.fetchone()

        if not latest_run:
            return {"status": "No portfolio data available"}

        run_id, start_date, end_date, strategy, created_at = latest_run

        # Get portfolio positions
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, weight, price_entry, d
                FROM backtest_positions
                WHERE run_id = :run_id
                ORDER BY d DESC, ABS(weight) DESC
                LIMIT 20
            """), {"run_id": run_id})

            positions = result.fetchall()

        # Format positions
        current_positions = []
        total_long_exposure = 0
        total_short_exposure = 0

        for symbol, weight, price_entry, position_date in positions:
            weight_val = float(weight)
            if weight_val > 0:
                total_long_exposure += weight_val
            else:
                total_short_exposure += abs(weight_val)

            current_positions.append({
                "symbol": symbol,
                "weight": f"{weight_val:+.2%}",
                "entry_price": f"${float(price_entry):.2f}",
                "position_date": position_date.isoformat(),
                "direction": "Long" if weight_val > 0 else "Short"
            })

        return {
            "portfolio_id": run_id,
            "strategy": strategy,
            "period": f"{start_date} to {end_date}",
            "last_updated": created_at.isoformat(),
            "exposure": {
                "long_exposure": f"{total_long_exposure:.2%}",
                "short_exposure": f"{total_short_exposure:.2%}",
                "net_exposure": f"{total_long_exposure - total_short_exposure:.2%}",
                "gross_exposure": f"{total_long_exposure + total_short_exposure:.2%}"
            },
            "current_positions": current_positions,
            "position_count": {
                "total": len(current_positions),
                "long": len([p for p in current_positions if p["direction"] == "Long"]),
                "short": len([p for p in current_positions if p["direction"] == "Short"])
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving portfolio status: {str(e)}")

@app.get("/trading/performance")
async def get_trading_performance(days: int = Query(30, ge=1, le=365)):
    """Get trading performance metrics for specified period"""

    try:
        # Get performance data from latest backtest
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT run_id, start_date, end_date, cost_bps, slippage_bps
                FROM backtests
                ORDER BY created_at DESC
                LIMIT 1
            """))

            latest_run = result.fetchone()

        if not latest_run:
            raise HTTPException(status_code=404, detail="No performance data available")

        run_id = latest_run[0]

        # Get position-level performance (simplified)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as total_trades,
                       AVG(weight) as avg_position_size,
                       COUNT(CASE WHEN weight > 0 THEN 1 END) as long_trades,
                       COUNT(CASE WHEN weight < 0 THEN 1 END) as short_trades
                FROM backtest_positions
                WHERE run_id = :run_id
            """), {"run_id": run_id})

            trade_stats = result.fetchone()

        return {
            "performance_period": f"Last {days} days (simulated)",
            "backtest_period": f"{latest_run[1]} to {latest_run[2]}",
            "trading_statistics": {
                "total_trades": int(trade_stats[0]),
                "long_trades": int(trade_stats[2]),
                "short_trades": int(trade_stats[3]),
                "avg_position_size": f"{float(trade_stats[1]):.2%}" if trade_stats[1] else "0%"
            },
            "cost_structure": {
                "trading_cost_bps": float(latest_run[3]),
                "slippage_bps": float(latest_run[4]),
                "total_cost_bps": float(latest_run[3]) + float(latest_run[4])
            },
            "note": "Performance data based on historical backtesting. Live trading performance will be available when automated trading is enabled."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving performance: {str(e)}")

@app.post("/reports/generate/{report_date}")
async def generate_report(report_date: date):
    """Generate fresh report for specified date"""

    try:
        report_paths = report_generator.generate_all_reports(report_date)

        return {
            "status": "success",
            "report_date": report_date.isoformat(),
            "generated_files": {
                "json": report_paths["json"],
                "html": report_paths["html"],
                "pdf": report_paths["pdf"]
            },
            "report_id": report_paths["report_id"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

def _get_recommendation(score: float) -> str:
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

def _calculate_position_size(score: float) -> str:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
