# Database setup script - IMPROVED VERSION
# Run this to create tables in your PostgreSQL database

import os
from sqlalchemy import create_engine, text

def setup_patterniq_db():
    """Setup PatternIQ database tables"""

    # Use your actual database URL here
    db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")

    print(f"Setting up database at: {db_url}")

    try:
        engine = create_engine(db_url)

        # Define each table creation statement separately to avoid parsing issues
        table_statements = [
            """
            CREATE TABLE IF NOT EXISTS instruments (
                symbol TEXT PRIMARY KEY,
                cusip TEXT,
                name TEXT,
                primary_exchange TEXT,
                is_active BOOL,
                first_seen DATE,
                last_seen DATE,
                sector TEXT,
                industry TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS universe_membership (
                symbol TEXT,
                universe TEXT,
                effective_from DATE,
                effective_to DATE,
                PRIMARY KEY(symbol, universe, effective_from)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS corporate_actions (
                symbol TEXT,
                action_date DATE,
                type TEXT,
                ratio NUMERIC,
                cash_amount NUMERIC
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS bars_1d (
                symbol TEXT,
                t TIMESTAMP,
                o NUMERIC,
                h NUMERIC,
                l NUMERIC,
                c NUMERIC,
                v BIGINT,
                adj_o NUMERIC,
                adj_h NUMERIC,
                adj_l NUMERIC,
                adj_c NUMERIC,
                adj_v BIGINT,
                vendor TEXT,
                PRIMARY KEY(symbol, t)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS fundamentals_snapshot (
                symbol TEXT,
                asof DATE,
                market_cap NUMERIC,
                ttm_eps NUMERIC,
                ttm_revenue NUMERIC,
                pe NUMERIC,
                ps NUMERIC
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS earnings (
                symbol TEXT,
                event_time TIMESTAMP,
                period TEXT,
                consensus NUMERIC,
                actual NUMERIC,
                surprise NUMERIC,
                before_after TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS features_daily (
                symbol TEXT,
                d DATE,
                feature_name TEXT,
                value NUMERIC,
                PRIMARY KEY(symbol, d, feature_name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS signals_daily (
                symbol TEXT,
                d DATE,
                signal_name TEXT,
                score NUMERIC,
                rank INT,
                explain JSONB
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS backtests (
                run_id UUID PRIMARY KEY,
                created_at TIMESTAMP,
                universe TEXT,
                start_date DATE,
                end_date DATE,
                cost_bps NUMERIC,
                slippage_bps NUMERIC,
                labeling TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS backtest_positions (
                run_id UUID,
                symbol TEXT,
                d DATE,
                weight NUMERIC,
                price_entry NUMERIC,
                price_exit NUMERIC,
                pnl NUMERIC
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id UUID PRIMARY KEY,
                period TEXT,
                path TEXT,
                summary JSONB
            )
            """
        ]

        with engine.connect() as conn:
            for i, statement in enumerate(table_statements, 1):
                try:
                    conn.execute(text(statement))
                    table_name = statement.split("CREATE TABLE IF NOT EXISTS ")[1].split(" (")[0].strip()
                    print(f"✅ Created table {i}/{len(table_statements)}: {table_name}")
                except Exception as e:
                    print(f"❌ Failed to create table {i}: {e}")

            conn.commit()

        print("✅ Database setup completed!")

        # Test connection and list all tables
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
            tables = [row[0] for row in result]
            print(f"✅ Total tables in database: {len(tables)}")
            print(f"Tables: {tables}")

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("Make sure your PostgreSQL container is running and credentials are correct")

if __name__ == "__main__":
    setup_patterniq_db()
