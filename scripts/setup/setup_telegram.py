#!/usr/bin/env python3
"""
Telegram Bot Setup Wizard for PatternIQ

Interactive setup to configure Telegram bot for daily report notifications.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.telegram.bot import PatternIQBot, TELEGRAM_AVAILABLE


def print_header():
    """Print setup header"""
    print("=" * 60)
    print("🤖 PatternIQ Telegram Bot Setup")
    print("=" * 60)
    print()


def check_telegram_package():
    """Check if python-telegram-bot is installed"""
    if not TELEGRAM_AVAILABLE:
        print("❌ python-telegram-bot package not installed")
        print()
        print("Install it with:")
        print("  pip install python-telegram-bot")
        print()
        return False
    return True


def get_bot_token():
    """Get bot token from user"""
    print("Step 1: Bot Token")
    print("-" * 40)
    print("1. Open Telegram and message @BotFather")
    print("2. Send: /newbot")
    print("3. Follow instructions to create your bot")
    print("4. Copy the token provided by BotFather")
    print()
    
    current_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if current_token:
        print(f"Current token: {current_token[:10]}...{current_token[-5:]}")
        use_current = input("Use current token? (y/n): ").strip().lower()
        if use_current == 'y':
            return current_token
    
    token = input("Enter your bot token: ").strip()
    if not token:
        print("❌ Token is required")
        return None
    return token


def get_chat_id():
    """Get chat ID from user"""
    print()
    print("Step 2: Chat ID")
    print("-" * 40)
    print("1. Open Telegram and message @userinfobot")
    print("2. Send any message to @userinfobot")
    print("3. It will reply with your chat ID (a number)")
    print()
    
    current_chats = os.getenv("TELEGRAM_CHAT_IDS", "")
    if current_chats:
        print(f"Current chat IDs: {current_chats}")
        use_current = input("Use current chat IDs? (y/n): ").strip().lower()
        if use_current == 'y':
            return current_chats
    
    chat_id = input("Enter your chat ID (or comma-separated for multiple): ").strip()
    if not chat_id:
        print("❌ Chat ID is required")
        return None
    return chat_id


async def test_connection(bot_token: str, chat_id: str):
    """Test bot connection and send test message"""
    print()
    print("Step 3: Testing Connection")
    print("-" * 40)
    
    try:
        bot = PatternIQBot()
        if not bot.bot:
            print("❌ Failed to initialize bot. Check your token.")
            return False
        
        # Test sending message
        chat_id_int = int(chat_id.split(',')[0].strip())
        success = await bot.test_connection(chat_id_int)
        
        if success:
            print("✅ Test message sent successfully!")
            print(f"   Check your Telegram - you should have received a test message")
            return True
        else:
            print("❌ Failed to send test message")
            print("   Check your chat ID and bot token")
            return False
            
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False


def save_to_env(bot_token: str, chat_ids: str):
    """Save configuration to .env file"""
    print()
    print("Step 4: Saving Configuration")
    print("-" * 40)
    
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    # Read existing .env if it exists
    env_lines = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add Telegram config
    updated = False
    new_lines = []
    
    for line in env_lines:
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            new_lines.append(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
            updated = True
        elif line.startswith("TELEGRAM_CHAT_IDS="):
            new_lines.append(f"TELEGRAM_CHAT_IDS={chat_ids}\n")
            updated = True
        elif line.startswith("SEND_TELEGRAM_ALERTS="):
            new_lines.append("SEND_TELEGRAM_ALERTS=true\n")
            updated = True
        else:
            new_lines.append(line)
    
    # Add if not found
    if not any("TELEGRAM_BOT_TOKEN" in line for new_lines):
        new_lines.append(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
    if not any("TELEGRAM_CHAT_IDS" in line for new_lines):
        new_lines.append(f"TELEGRAM_CHAT_IDS={chat_ids}\n")
    if not any("SEND_TELEGRAM_ALERTS" in line for new_lines):
        new_lines.append("SEND_TELEGRAM_ALERTS=true\n")
    
    # Write .env file
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Configuration saved to {env_file}")
    print()
    print("To use this configuration:")
    print("  1. Load environment variables:")
    print("     source .env  # or: export $(cat .env | xargs)")
    print()
    print("  2. Or run with --telegram flag:")
    print("     python run_patterniq.py batch --telegram")
    print()
    print("  3. Or set manually:")
    print(f"     export TELEGRAM_BOT_TOKEN='{bot_token}'")
    print(f"     export TELEGRAM_CHAT_IDS='{chat_ids}'")
    print("     export SEND_TELEGRAM_ALERTS=true")


async def main():
    """Main setup wizard"""
    print_header()
    
    # Check package
    if not check_telegram_package():
        sys.exit(1)
    
    # Get bot token
    bot_token = get_bot_token()
    if not bot_token:
        print("❌ Setup cancelled")
        sys.exit(1)
    
    # Get chat ID
    chat_ids = get_chat_id()
    if not chat_ids:
        print("❌ Setup cancelled")
        sys.exit(1)
    
    # Set environment for testing
    os.environ["TELEGRAM_BOT_TOKEN"] = bot_token
    os.environ["TELEGRAM_CHAT_IDS"] = chat_ids
    
    # Test connection
    test_success = await test_connection(bot_token, chat_ids)
    
    if not test_success:
        retry = input("\nRetry setup? (y/n): ").strip().lower()
        if retry == 'y':
            return await main()
        else:
            print("❌ Setup incomplete")
            sys.exit(1)
    
    # Save configuration
    save_to_env(bot_token, chat_ids)
    
    print()
    print("=" * 60)
    print("✅ Telegram bot setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Load environment variables")
    print("   source .env")
    print()
    print("  2. Run PatternIQ with Telegram enabled:")
    print("   python run_patterniq.py batch --telegram")
    print()


if __name__ == "__main__":
    asyncio.run(main())
