#!/usr/bin/env python3
# Simple test for adjustment logic

print("🔧 PatternIQ Price Adjustment Test")
print("=" * 40)

try:
    import os
    from datetime import date
    from sqlalchemy import create_engine, text

    # Test database connection first
    db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
    print(f"Connecting to: {db_url}")

    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check if we have data
        result = conn.execute(text("SELECT COUNT(*) FROM bars_1d"))
        bars_count = result.fetchone()[0]
        print(f"✅ Found {bars_count} bars in database")

        # Add a test corporate action
        conn.execute(text("""
            INSERT INTO corporate_actions (symbol, action_date, type, ratio, cash_amount)
            VALUES ('MMM', '2024-01-05', 'split', 2.0, NULL)
            ON CONFLICT DO NOTHING
        """))
        conn.commit()
        print("✅ Added test corporate action")

        # Check adjustment factors calculation
        result = conn.execute(text("""
            SELECT action_date, type, ratio FROM corporate_actions 
            WHERE symbol = 'MMM'
        """))
        actions = result.fetchall()
        print(f"✅ Found {len(actions)} corporate actions for MMM")

        for action_date, action_type, ratio in actions:
            print(f"   {action_date}: {action_type} (ratio: {ratio})")

        # Show sample price data before and after adjustment
        result = conn.execute(text("""
            SELECT t, o, c, adj_o, adj_c FROM bars_1d 
            WHERE symbol = 'MMM' 
            ORDER BY t 
            LIMIT 3
        """))
        bars = result.fetchall()

        if bars:
            print("\n📈 Sample MMM price data:")
            print("Date       | Raw Open | Raw Close | Adj Open | Adj Close")
            print("-" * 55)
            for t, o, c, adj_o, adj_c in bars:
                adj_o_val = adj_o if adj_o else o
                adj_c_val = adj_c if adj_c else c
                print(f"{t.strftime('%Y-%m-%d')} | ${o:8.2f} | ${c:9.2f} | ${adj_o_val:8.2f} | ${adj_c_val:9.2f}")

        print("\n✅ Adjustment logic test completed!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
