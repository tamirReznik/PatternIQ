#!/bin/bash
# setup_macos_scheduling.sh - Setup daily PatternIQ execution on macOS

echo "🍎 Setting up PatternIQ Daily Scheduling on macOS"
echo "================================================="

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# Make the runner executable
echo "🔧 Making runner executable..."
chmod +x macos_daily_runner.py

# Copy the plist file to the correct location
echo "📋 Installing launch agent..."
cp com.patterniq.daily.plist ~/Library/LaunchAgents/

# Load the launch agent
echo "⚡ Loading launch agent..."
launchctl load ~/Library/LaunchAgents/com.patterniq.daily.plist

# Check if it's loaded
echo "✅ Checking installation..."
launchctl list | grep patterniq

echo ""
echo "🎯 Setup Complete!"
echo "==================="
echo "📅 PatternIQ will run daily at 6:00 PM"
echo "📊 Reports will be generated automatically"
echo "🌐 Dashboard will be updated after each run"
echo ""
echo "📂 Files to bookmark:"
echo "   Dashboard: file://$(pwd)/dashboard.html"
echo "   Logs:      $(pwd)/logs/"
echo ""
echo "🔧 Management commands:"
echo "   View status:    launchctl list | grep patterniq"
echo "   Stop scheduler: launchctl unload ~/Library/LaunchAgents/com.patterniq.daily.plist"
echo "   Start scheduler: launchctl load ~/Library/LaunchAgents/com.patterniq.daily.plist"
echo "   Test run now:   python3 macos_daily_runner.py"
echo ""
echo "💡 Tip: Keep your MacBook on and awake at 6 PM for automatic execution"
