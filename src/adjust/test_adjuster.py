# src/adjust/test_adjuster.py - Simple test for adjustment logic

import os
import sys
sys.path.append('/Users/tamirreznik/code/private/PatternIQ')

from src.adjust.adjuster import PriceAdjuster, demo_adjustment_logic

print("🔧 Testing PatternIQ Price Adjuster")
print("=" * 40)

try:
    # Test basic initialization
    adjuster = PriceAdjuster()
    print("✅ PriceAdjuster initialized successfully")

    # Test database connection
    with adjuster.engine.connect() as conn:
        result = conn.execute("SELECT COUNT(*) FROM bars_1d")
        count = result.fetchone()[0]
        print(f"✅ Database connected - found {count} bars")

    adjuster.close()
    print("✅ Connection closed successfully")

    # Now run the full demo
    print("\n" + "="*50)
    print("Running full adjustment demo:")
    print("="*50)
    demo_adjustment_logic()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
