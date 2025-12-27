#!/usr/bin/env python3
"""
Telegram setup helper for PatternIQ
Helps you configure Telegram bot and get chat IDs
"""

import asyncio
import os
import json
from pathlib import Path

async def setup_telegram_bot():
    """Interactive setup for Telegram bot"""
    print("🤖 PatternIQ Telegram Bot Setup")
    print("=" * 40)

    print("\n📋 Step 1: Create a Telegram Bot")
    print("1. Message @BotFather on Telegram")
    print("2. Send /newbot")
    print("3. Choose a name for your bot (e.g., 'PatternIQ Daily Reports')")
    print("4. Choose a username (e.g., 'patterniq_reports_bot')")
    print("5. Copy the bot token")

    bot_token = input("\n🔑 Enter your bot token: ").strip()

    if not bot_token:
        print("❌ Bot token is required!")
        return False

    # Save bot token to environment
    print(f"\n💾 Saving bot token...")

    # Create or update .env file
    env_file = Path(".env")
    env_lines = []

    if env_file.exists():
        with open(env_file, 'r') as f:
            env_lines = f.readlines()

    # Remove existing TELEGRAM_BOT_TOKEN if present
    env_lines = [line for line in env_lines if not line.startswith('TELEGRAM_BOT_TOKEN=')]

    # Add new token
    env_lines.append(f'TELEGRAM_BOT_TOKEN={bot_token}\n')

    with open(env_file, 'w') as f:
        f.writelines(env_lines)

    # Set for current session
    os.environ['TELEGRAM_BOT_TOKEN'] = bot_token

    print("✅ Bot token saved to .env file")

    print("\n📋 Step 2: Get Chat ID")
    print("1. Start a chat with your bot on Telegram")
    print("2. Send any message to your bot")
    print("3. Or add the bot to a channel/group and send a message")

    chat_id_input = input("\n🆔 Enter your chat ID (or 'auto' to detect): ").strip()

    chat_ids = []

    if chat_id_input.lower() == 'auto':
        print("🔍 Attempting to detect chat ID...")
        try:
            # Import here to avoid issues if telegram lib not installed
            from telegram import Bot

            bot = Bot(token=bot_token)

            # Get updates to find chat ID
            updates = await bot.get_updates()

            if updates:
                for update in updates[-5:]:  # Check last 5 updates
                    if update.message:
                        chat_id = update.message.chat_id
                        chat_title = update.message.chat.title or update.message.chat.first_name or "Private Chat"
                        print(f"Found chat: {chat_title} (ID: {chat_id})")

                        if chat_id not in chat_ids:
                            chat_ids.append(chat_id)

            if not chat_ids:
                print("❌ No recent messages found. Please send a message to your bot first.")
                return False

        except Exception as e:
            print(f"❌ Error detecting chat ID: {e}")
            return False
    else:
        try:
            chat_id = int(chat_id_input)
            chat_ids = [chat_id]
        except ValueError:
            print("❌ Invalid chat ID format!")
            return False

    # Save chat IDs
    chat_config = {
        "chat_ids": chat_ids,
        "last_updated": "2025-10-04T19:55:00",
        "description": "PatternIQ Daily Reports"
    }

    with open("telegram_chats.json", 'w') as f:
        json.dump(chat_config, f, indent=2)

    print(f"✅ Saved {len(chat_ids)} chat ID(s) to telegram_chats.json")

    # Test the bot
    print("\n🧪 Testing bot connection...")
    try:
        from telegram import Bot

        bot = Bot(token=bot_token)

        for chat_id in chat_ids:
            test_message = "🤖 *PatternIQ Bot Setup Complete!*\n\nYou will now receive daily trading reports automatically at 6 PM EST.\n\n_Test message sent successfully!_"

            await bot.send_message(
                chat_id=chat_id,
                text=test_message,
                parse_mode='Markdown'
            )

            print(f"✅ Test message sent to chat {chat_id}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    print("\n🎉 Telegram bot setup complete!")
    print("\n📱 What happens next:")
    print("• Daily reports will be sent automatically at 6 PM")
    print("• Reports include market analysis and trading recommendations")
    print("• You can add more chats by editing telegram_chats.json")

    return True

async def test_existing_setup():
    """Test existing Telegram setup"""
    print("🧪 Testing existing Telegram setup...")

    # Check for bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ No bot token found. Run setup first.")
        return False

    # Check for chat IDs
    if not Path("telegram_chats.json").exists():
        print("❌ No chat configuration found. Run setup first.")
        return False

    try:
        with open("telegram_chats.json", 'r') as f:
            config = json.load(f)

        chat_ids = config.get("chat_ids", [])
        if not chat_ids:
            print("❌ No chat IDs configured.")
            return False

        print(f"✅ Found {len(chat_ids)} configured chat(s)")

        # Test connection
        from telegram import Bot

        bot = Bot(token=bot_token)

        for chat_id in chat_ids:
            test_message = "🧪 *PatternIQ Connection Test*\n\nTelegram integration is working correctly!\n\n_Daily reports will be sent automatically._"

            await bot.send_message(
                chat_id=chat_id,
                text=test_message,
                parse_mode='Markdown'
            )

            print(f"✅ Test message sent to chat {chat_id}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main setup interface"""
    print("🤖 PatternIQ Telegram Setup")
    print("=" * 30)
    print("1. Setup new Telegram bot")
    print("2. Test existing setup")
    print("3. Exit")

    choice = input("\nChoose an option (1-3): ").strip()

    if choice == "1":
        asyncio.run(setup_telegram_bot())
    elif choice == "2":
        asyncio.run(test_existing_setup())
    elif choice == "3":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice!")

if __name__ == "__main__":
    main()
