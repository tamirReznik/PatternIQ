#!/usr/bin/env python3
"""
Test Telegram bot with proper environment loading
"""
import os
import asyncio
import sys
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    env_file = Path('.env')
    if env_file.exists():
        print("📁 Loading environment variables from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"   {key} = {value[:10]}..." if len(value) > 10 else f"   {key} = {value}")

async def test_telegram_bot():
    print("🤖 Testing PatternIQ Telegram Bot")
    print("=" * 40)

    # Load environment
    load_env_file()

    # Add src to path
    sys.path.insert(0, 'src')

    try:
        from src.telegram.bot import PatternIQBot

        # Initialize bot
        bot = PatternIQBot()

        if not bot.bot:
            print("❌ Bot not initialized - check token")
            return False

        if not bot.chat_ids:
            print("❌ No chat IDs configured")
            return False

        print(f"✅ Bot initialized successfully")
        print(f"📱 Chat IDs: {bot.chat_ids}")

        # Test connection first
        print("\n🧪 Testing connection...")
        for chat_id in bot.chat_ids:
            try:
                success = await bot.test_connection(chat_id)
                if success:
                    print(f"✅ Test message sent to chat {chat_id}")
                else:
                    print(f"❌ Failed to send to chat {chat_id}")
            except Exception as e:
                print(f"❌ Error testing chat {chat_id}: {e}")

        # Test daily report
        print("\n📊 Testing daily report...")
        try:
            report_success = await bot.send_daily_report()
            if report_success:
                print("✅ Daily report sent successfully!")
                print("📱 Check your Telegram for the PatternIQ daily report!")
            else:
                print("❌ Failed to send daily report")
        except Exception as e:
            print(f"❌ Error sending daily report: {e}")

        return True

    except Exception as e:
        print(f"❌ Error initializing bot: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_telegram_bot())
