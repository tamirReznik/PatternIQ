#!/bin/bash
# setup_scheduling.sh - Setup macOS launchd scheduling for PatternIQ daily runs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_FILE="$PROJECT_DIR/config/com.patterniq.daily.plist"
PLIST_NAME="com.patterniq.daily"

echo "🤖 PatternIQ Daily Scheduling Setup"
echo "===================================="
echo ""

# Check if plist file exists
if [ ! -f "$PLIST_FILE" ]; then
    echo "❌ Error: Plist file not found at $PLIST_FILE"
    exit 1
fi

# Validate plist file
echo "📋 Validating plist file..."
if plutil -lint "$PLIST_FILE" > /dev/null 2>&1; then
    echo "✅ Plist file is valid"
else
    echo "❌ Error: Plist file is invalid"
    plutil -lint "$PLIST_FILE"
    exit 1
fi

# Check if service is already loaded
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "⚠️  Service is already loaded. Unloading first..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    sleep 1
fi

# Load the service
echo "📤 Loading launchd service..."
launchctl load "$PLIST_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Service loaded successfully"
else
    echo "❌ Error: Failed to load service"
    exit 1
fi

# Verify service is loaded
sleep 1
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "✅ Service verified in launchctl"
    
    # Show service status
    echo ""
    echo "📊 Service Status:"
    launchctl list | grep "$PLIST_NAME" || echo "   (Service loaded but not running - this is normal for calendar-based jobs)"
    
    echo ""
    echo "📅 Scheduled Time: 6:00 PM daily"
    echo "📝 Logs: $PROJECT_DIR/logs/patterniq_daily.log"
    echo "📝 Error Logs: $PROJECT_DIR/logs/patterniq_daily_error.log"
    echo ""
    echo "💡 Note: Calendar-based jobs only run when the system is on at the scheduled time."
    echo "   If your Mac is sleeping, the job will run when it wakes up (if within 10 minutes)."
    echo ""
    echo "🧪 To test the service manually:"
    echo "   cd $PROJECT_DIR"
    echo "   python scripts/runners/macos_daily_runner.py"
    echo ""
    echo "✅ Setup complete!"
else
    echo "⚠️  Warning: Service may not be loaded correctly"
    echo "   Check logs for errors"
    exit 1
fi

