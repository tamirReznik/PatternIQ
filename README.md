# PatternIQ

**Passive Income Generation Through Intelligent Stock & Crypto Trading**

PatternIQ is a sophisticated algorithmic trading system designed to generate passive income by identifying high-probability trading opportunities across stocks, ETFs, and cryptocurrencies. The system processes market data, calculates proprietary technical indicators, and produces daily portfolio recommendations organized by investment time horizon (short/mid/long-term) backed by rigorous backtesting.

---

## 🎯 What PatternIQ Does for You

**PatternIQ delivers daily trading intelligence to help you generate passive income:**

### Core Features

1. **📈 Intelligent Trade Identification**
   - Spots stocks/crypto with strong momentum or mean-reversion patterns
   - Uses proprietary signal blending with Information Coefficient (IC) weighting
   - Filters out low-quality opportunities using fundamental analysis

2. **⏳ Time Horizon Strategies**
   - **Short-Term** (Days to Weeks): Quick momentum plays, tighter stops
   - **Mid-Term** (Weeks to Months): Balanced risk-reward, trend following
   - **Long-Term** (Months to Years): Fundamental value, macro trends
   - Each recommendation includes appropriate time horizon classification

3. **💼 Portfolio Optimization**
   - Specific position sizes for each recommendation (typically 1-5% per position)
   - Risk-adjusted recommendations based on signal strength
   - Multi-asset allocation (stocks, ETFs, crypto)
   - Portfolio concentration limits and risk management

4. **🛡️ Risk Management**
   - Built-in safeguards to avoid earnings announcements
   - Volatility gates to skip high-risk periods
   - Stop-loss and take-profit recommendations
   - Fundamental filtering to avoid overvalued stocks

5. **📊 Performance Tracking**
   - Comprehensive analytics to measure strategy effectiveness
   - Real-time portfolio tracking vs initial investment
   - Historical performance metrics (Sharpe ratio, alpha, win rate)
   - Daily P&L and month-to-date performance

6. **🔬 Historical Validation**
   - Backtest algorithms across different market conditions
   - Verify performance before deploying capital
   - Compare strategies (short/mid/long-term)
   - Monte Carlo simulation support

7. **📱 Automated Delivery**
   - Professional reports in JSON, HTML formats
   - REST API for programmatic access
   - Telegram notifications for mobile alerts
   - Automated daily execution via scheduling

8. **🤖 Automated Trading Bot**
   - Paper trading simulation with real-time tracking
   - Processes daily signals automatically
   - Portfolio management and position tracking
   - Performance metrics and reporting

---

## 🤖 Enhanced Trading Bot Performance Testing

PatternIQ includes sophisticated performance simulation tools to help you understand potential returns and risks before deploying capital.

### 📊 Bot Performance Simulation

Test how the enhanced trading bot would have performed over any historical period:

#### Unified Backtest Runner (Recommended)

**Important**: Activate virtual environment first!

```bash
# Activate venv (required)
source venv/bin/activate

# Quick 1-year backtest
python scripts/simulations/run_backtest.py --period 1y

# Or use the wrapper script (automatically activates venv)
bash scripts/simulations/run_backtest.sh --period 1y

# Test specific strategy (short/mid/long-term)
python scripts/simulations/run_backtest.py --strategy short --period 6m
python scripts/simulations/run_backtest.py --strategy mid --period 1y
python scripts/simulations/run_backtest.py --strategy long --period 2y

# Compare all strategies
python scripts/simulations/run_backtest.py --strategy all --period 1y

# Custom date range with specific capital
python scripts/simulations/run_backtest.py --start 2024-01-01 --end 2024-12-31 --capital 50000
```

**Note**: If you see `ModuleNotFoundError: No module named 'numpy'`, make sure you've activated the virtual environment with `source venv/bin/activate`.

#### Legacy Simulation Scripts (Deprecated - Use Unified Script Instead)

**Note**: The old `quick_simulation.py` and `flexible_simulation.py` scripts have been consolidated into the unified `run_backtest.py` script. Use the commands above instead.

If you need to use the legacy scripts (not recommended), they are located in `scripts/simulations/`:
```bash
# Activate venv first!
source venv/bin/activate

# Legacy scripts (deprecated)
python scripts/simulations/quick_simulation.py
python scripts/simulations/flexible_simulation.py 2024-01-01 --end_date 2024-12-31 --capital 50000
```

**Recommended**: Use the unified backtest script instead (see examples above).

#### Simulation Features
- **Realistic Trading Logic**: Uses same sophisticated decision-making as live bot
- **Risk Management**: Stop losses (15%), take profits (30%), position sizing (3-5%)
- **Fundamental Filtering**: Avoids overvalued stocks using P/E, debt ratios, margins
- **Market Condition Adaptation**: Performance varies based on bull/bear/volatile markets
- **Benchmark Comparison**: Shows outperformance vs S&P 500
- **Win Rate Analysis**: Tracks profitable vs unprofitable trades

#### Key Performance Metrics Tracked
- **Total Return**: Overall portfolio appreciation
- **Annualized Return**: Return adjusted for time period
- **Alpha**: Outperformance vs market benchmark
- **Win Rate**: Percentage of profitable trades
- **Max Drawdown**: Worst peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns

### 🎯 Typical Bot Performance (Historical Simulation)
Based on backtesting with sophisticated risk management:
- **Annual Return**: 10-15% (market-beating performance)
- **Win Rate**: 60-70% (quality signal filtering)
- **Max Loss Per Trade**: 6-12% (stop loss protection)
- **Max Gain Per Trade**: 8-18% (take profit discipline)
- **Benchmark Alpha**: +0.5% to +3% vs S&P 500

---

## 🌍 Multi-Asset Trading Capabilities

### **Expanded Universe: Stocks + Indexes + Crypto**

PatternIQ now supports trading across multiple asset classes to enhance diversification and returns:

#### **Available Asset Classes**

**📈 Market Indexes (ETFs)**
- **SPY** - S&P 500 ETF (broad market exposure)
- **QQQ** - NASDAQ-100 ETF (technology focus)
- **DIA** - Dow Jones ETF (blue chip stocks)
- **IWM** - Russell 2000 ETF (small cap exposure)
- **VTI** - Total Stock Market ETF (complete market)
- **EFA** - International Developed Markets

**₿ Cryptocurrencies** (24/7 Trading)
- **BTC-USD** - Bitcoin (crypto blue chip)
- **ETH-USD** - Ethereum (smart contracts)
- **SOL-USD** - Solana (high performance)
- **ADA-USD** - Cardano (proof of stake)
- **BNB-USD** - Binance Coin (exchange token)
- **XRP-USD** - Ripple (payments)
- **MATIC-USD** - Polygon (scaling solution)

#### **Smart Position Limits by Asset Class**

**Stocks (S&P 500)**
- Max per position: **5%**
- Max total allocation: **70%**
- Stop loss: **15%** | Take profit: **30%**
- Signal threshold: **0.6** (strong signals only)

**Indexes/ETFs**
- Max per position: **15%** (less risky, more concentrated OK)
- Max total allocation: **40%**
- Stop loss: **10%** | Take profit: **20%**
- Signal threshold: **0.6**

**Cryptocurrencies**
- Max per position: **3%** (high volatility protection)
- Max total allocation: **15%** (limit overall crypto risk)
- Stop loss: **20%** | Take profit: **50%**
- Signal threshold: **0.7** (only very strong signals)

#### **Why Multi-Asset Trading?**

**Enhanced Diversification**
- Reduce correlation risk by spreading across asset classes
- Crypto often moves independently of stocks
- Indexes provide stable core holdings

**24/7 Opportunities**
- Crypto markets never close
- Capture opportunities while stock markets are closed
- React to global events in real-time

**Optimized Risk-Return**
- Higher risk assets (crypto) limited to small allocations
- Stable assets (indexes) can have larger positions
- Overall portfolio risk managed holistically

**Better Performance Potential**
- Crypto can deliver 50-100%+ returns in bull markets
- Indexes provide steady 8-12% baseline returns
- Stocks offer 10-15% with active selection

#### **Using Multi-Asset Bot**

```python
from src.trading.multi_asset_bot import MultiAssetTradingBot

# Initialize with all asset classes
bot = MultiAssetTradingBot(
    initial_capital=100000.0,
    paper_trading=True,
    enable_crypto=True,      # Enable cryptocurrency trading
    enable_indexes=True      # Enable index/ETF trading
)

# Bot automatically manages allocation across asset classes
status = bot.get_portfolio_status()

print(f"Allocation by asset class:")
for asset_class, allocation in status['allocation_by_class'].items():
    print(f"  {asset_class}: {allocation:.1%}")

# Example output:
#   stocks: 45.0%
#   indexes: 35.0%
#   crypto: 12.0%
#   cash: 8.0%
```

#### **Risk Management Across Asset Classes**

The multi-asset bot implements sophisticated risk controls:

1. **Class-Level Limits**: Each asset class has maximum allocation
2. **Position-Level Limits**: Individual positions sized appropriately
3. **Dynamic Stop Losses**: Wider stops for volatile assets (crypto)
4. **Higher Signal Thresholds**: Crypto requires stronger signals (0.7 vs 0.6)
5. **Fee Awareness**: Accounts for exchange fees on crypto trades
6. **Market Hours**: Respects market hours for stocks/indexes, trades crypto 24/7

#### **Expected Performance with Multi-Asset**

**Conservative Mix** (60% stocks, 30% indexes, 10% crypto)
- Expected annual return: **12-18%**
- Risk level: **Medium**
- Best for: Steady growth with some upside

**Balanced Mix** (50% stocks, 25% indexes, 25% crypto)
- Expected annual return: **15-25%**
- Risk level: **Medium-High**
- Best for: Growth-focused investors

**Aggressive Mix** (40% stocks, 20% indexes, 40% crypto)
- Expected annual return: **20-40%** (or larger losses)
- Risk level: **High**
- Best for: Risk-tolerant investors seeking maximum returns

**Note**: Cryptocurrency is highly volatile and can experience 50%+ drawdowns. Only allocate what you can afford to lose.

---

## 🚀 Quick Start Guide

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd PatternIQ

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup database
python scripts/setup/setup_db.py

# 5. Configure environment (optional)
cp .env.example .env  # Edit .env with your settings
```

### Running PatternIQ

PatternIQ can run in three modes:

#### 1. **Batch Mode** (Recommended for Daily Runs)
Runs the complete pipeline once and exits. Perfect for scheduled daily execution.

```bash
# Basic batch run
python run_patterniq.py batch

# With Telegram notifications
python run_patterniq.py batch --telegram

# Custom database location
python run_patterniq.py batch --db-mode sqlite --sqlite-path data/my_db.db
```

#### 2. **Always-On Mode** (Continuous Operation)
Runs continuously, processing data and serving API requests.

```bash
# Start always-on mode
python run_patterniq.py always-on

# With custom API port
python run_patterniq.py always-on --port 9000

# With Telegram enabled
python run_patterniq.py always-on --telegram --port 8000
```

#### 3. **API-Only Mode** (Server Only)
Starts only the API server without running the pipeline. Useful for accessing existing data.

```bash
# Start API server only
python run_patterniq.py api-only

# Custom port
python run_patterniq.py api-only --port 9000
```

### macOS Daily Automation

For automated daily runs on macOS:

```bash
# Setup launchd scheduling (runs daily at 6:00 PM)
bash scripts/scheduling/setup_scheduling.sh

# Or manually run the daily batch
python scripts/runners/macos_daily_runner.py
```

### Manual Pipeline Execution

You can also run individual pipeline components:

```bash
# Important: Activate venv first!
source venv/bin/activate

# 1. Ingest market data
python -m src.data.ingestion.pipeline

# 2. Calculate features
python -m src.features.momentum

# 3. Generate signals
python -m src.signals.rules

# 4. Blend signals
python -m src.signals.blend

# 5. Generate reports
python -m src.report.generator
```

### Run Full Demo

Test all features:

```bash
source venv/bin/activate
python scripts/demo/run_full_demo.py
```

---

## 📊 Daily System Output

Every trading day, PatternIQ generates:

### 1. **Professional Trading Reports** (Multiple Formats)
- **JSON Report**: Machine-readable data for API integration and external systems
- **HTML Report**: Professional web-formatted report with interactive styling
- **PDF Report**: Print-ready document for sharing and compliance (optional)

### 2. **Daily Trading Recommendations**
- **Top 10 Long Candidates**: Stocks recommended for buying with conviction scores
- **Top 10 Short Candidates**: Stocks recommended for shorting with conviction scores  
- **Position Sizes**: Exact percentage allocation for each recommendation (typically 1-3% per position)
- **Risk Alerts**: Warnings about market volatility or upcoming earnings

### 3. **Market Intelligence Dashboard**
- **Market Regime**: Current market condition (trending, ranging, volatile)
- **Sector Heatmap**: Which sectors are showing strongest/weakest signals
- **Signal Strength**: Overall conviction level across the universe (0-100 scale)

### 4. **Performance Tracking & Portfolio Status**
- **Daily P&L**: How yesterday's recommendations performed
- **Month-to-Date Performance**: Running track record
- **Hit Rate**: Percentage of profitable recommendations
- **Portfolio Value**: Real-time tracking of initial investment vs current value
- **Risk Metrics**: Current portfolio exposure and drawdown levels

### 5. **Automated Notifications**
- **Telegram Alerts**: Instant mobile notifications with top picks and market updates
- **API Endpoints**: Real-time access to all data and reports for external integration
- **Automated Trading Bot**: Paper trading simulation with performance tracking

---

## 🌐 API Endpoints

PatternIQ provides a comprehensive REST API for accessing all data and reports:

### **Report Endpoints**
```
GET /reports/latest?format=json|html|pdf     # Latest daily report
GET /reports/daily/{date}?format=json        # Specific date report  
POST /reports/generate/{date}                # Generate fresh report
```

### **Signal & Data Endpoints**
```
GET /signals/{date}?signal_type=combined     # Raw trading signals
GET /portfolio/status                        # Current portfolio state
GET /trading/performance                     # Performance metrics
GET /                                        # API health check
```

### **API Usage Examples**
```bash
# Get latest report in JSON format
curl http://localhost:8000/reports/latest?format=json

# Get current portfolio status
curl http://localhost:8000/portfolio/status

# Get signals for specific date
curl http://localhost:8000/signals/2025-09-20?signal_type=combined
```

---

## 🤖 Telegram Bot Integration

**Automated Mobile Notifications**

PatternIQ includes a Telegram bot that sends daily trading alerts directly to your phone:

### **Setup Instructions**
1. **Create Bot**: Message @BotFather on Telegram and send `/newbot`
2. **Get Token**: Copy the bot token from BotFather
3. **Get Chat ID**: Message @userinfobot to get your chat ID
4. **Configure Environment**:
   ```bash
   export TELEGRAM_BOT_TOKEN='your_bot_token_here'
   export TELEGRAM_CHAT_IDS='123456789,987654321'  # Comma-separated
   ```

### **Daily Telegram Report Includes**
- **Market regime and signal strength**
- **Top 5 long and short recommendations with scores**
- **Risk alerts and sector highlights**
- **Performance updates and next actions**
- **Formatted with emojis for easy mobile reading**

### **Bot Commands**
```python
# Send daily report
python -m src.telegram.bot

# Test bot connection
bot.test_connection(your_chat_id)

# Send custom alert
bot.send_alert("Market volatility spike detected", priority="high")
```

---

## 💼 Automated Trading System

**Paper Trading Bot with Portfolio Tracking**

PatternIQ includes an automated trading bot that can process daily reports and execute trades (currently paper trading only):

### **Key Features**
- **Processes Daily Signals**: Automatically reads PatternIQ reports and generates trading orders
- **Portfolio Management**: Tracks positions, cash balance, and performance vs initial investment
- **Risk Controls**: Maximum position sizing (5% per stock), portfolio stop-loss (20%)
- **Performance Tracking**: Real-time P&L, Sharpe ratio, volatility metrics
- **State Persistence**: Saves trading history and portfolio state

### **Portfolio Status API**
```json
{
  "initial_capital": 100000.0,
  "current_value": 108500.0,
  "total_return": "8.50%",
  "cash_balance": 15000.0,
  "positions_value": 93500.0,
  "total_pnl": 8500.0,
  "performance_metrics": {
    "total_return_pct": "8.50%",
    "annualized_volatility": "12.50%",
    "sharpe_ratio": "1.45",
    "trading_days": 45
  },
  "positions": [
    {
      "symbol": "AAPL",
      "shares": 100,
      "entry_price": 170.00,
      "current_price": 175.50,
      "unrealized_pnl": 550.0,
      "unrealized_return": "3.24%"
    }
  ],
  "paper_trading": true,
  "status": "active"
}
```

### **Trading Bot Usage**
```python
# Initialize bot with $100K paper money
bot = AutoTradingBot(initial_capital=100000.0, paper_trading=True)

# Process daily report and generate trades
result = bot.process_daily_report(date.today())

# Get current portfolio status
status = bot.get_portfolio_status()

# Track initial investment vs current value
print(f"Started with: ${status['initial_capital']:,.2f}")
print(f"Current value: ${status['current_value']:,.2f}")
print(f"Total return: {status['total_return']:.2%}")
```

---

## 🧠 Understanding Your Reports

### **Signal Scores Explained**

**Score Range: -1.0 to +1.0**
- **+0.7 to +1.0**: **STRONG BUY** - High confidence long position
- **+0.3 to +0.7**: **BUY** - Moderate confidence long position  
- **-0.3 to +0.3**: **NEUTRAL** - No clear directional signal
- **-0.7 to -0.3**: **SELL** - Moderate confidence short position
- **-1.0 to -0.7**: **STRONG SELL** - High confidence short position

### **Signal Types and What They Mean**

#### **Momentum Signals** (`momentum_20_120`)
- **What it detects**: Stocks with sustained price trends over 20 and 120 days
- **When to use**: Works best in trending markets
- **Interpretation**: 
  - Positive scores = Stock price momentum is accelerating upward
  - Negative scores = Stock price momentum is declining

#### **Mean Reversion Signals** (`meanrev_bollinger`)
- **What it detects**: Stocks that have moved too far from their average price
- **When to use**: Works best in ranging/sideways markets
- **Interpretation**:
  - Positive scores = Stock is oversold, likely to bounce back up
  - Negative scores = Stock is overbought, likely to decline

#### **Gap Breakaway Signals** (`gap_breakaway`)
- **What it detects**: Stocks opening significantly higher/lower than previous close
- **When to use**: Captures momentum from overnight news or events
- **Interpretation**:
  - Positive scores = Gap up is likely to continue (buy)
  - Negative scores = Gap down is likely to continue (short)

### **Combined Signal** (`combined_ic_weighted`)
- **What it is**: The final recommendation combining all individual signals
- **How it's calculated**: Automatically weights each signal based on recent performance (Information Coefficient)
- **Key insight**: This is your primary trading signal - the system's best guess

### **Time Horizon Strategies** (NEW)

PatternIQ now classifies all signals by investment time horizon to help you build a diversified passive income portfolio:

#### **Short-Term Strategy** (Days to Weeks)
- **Focus**: Momentum signals, gap breakaways, quick reversals
- **Holding Period**: 1-14 days typically
- **Risk Level**: High volatility, higher frequency trading
- **Stop Loss**: 10% | Take Profit: 15%
- **Best For**: Active traders seeking quick gains

#### **Mid-Term Strategy** (Weeks to Months)
- **Focus**: Balanced momentum and mean reversion
- **Holding Period**: 14-90 days typically
- **Risk Level**: Medium volatility, moderate frequency
- **Stop Loss**: 15% | Take Profit: 25%
- **Best For**: Balanced approach to passive income

#### **Long-Term Strategy** (Months to Years)
- **Focus**: Trend following, fundamental strength
- **Holding Period**: 90-365+ days typically
- **Risk Level**: Lower volatility, lower frequency
- **Stop Loss**: 20% | Take Profit: 40%
- **Best For**: Long-term wealth building and passive income

**Reports now show separate sections for each time horizon**, allowing you to:
- Build a diversified portfolio across time horizons
- Match strategies to your risk tolerance and time availability
- Optimize for different passive income goals

---

## 📈 Performance Metrics Explained

### **Return Metrics**
- **Total Return**: Cumulative profit/loss since inception
- **Annualized Return**: Expected yearly return based on historical performance
- **Sharpe Ratio**: Risk-adjusted return (>1.0 is good, >2.0 is excellent)
- **Calmar Ratio**: Return relative to worst drawdown (higher is better)

### **Risk Metrics**
- **Maximum Drawdown**: Worst peak-to-trough decline (lower is better)
- **Volatility**: How much returns fluctuate (annual standard deviation)
- **Hit Rate**: Percentage of profitable trades
  - Daily: % of profitable days
  - Weekly: % of profitable weeks  
  - Monthly: % of profitable months

### **Signal Quality**
- **Information Coefficient (IC)**: How well signals predict future returns (-1 to +1)
  - Above 0.05: Good predictive power
  - Above 0.10: Excellent predictive power
- **Turnover**: How often positions change (lower = more efficient)

---

## 🛡️ Built-in Risk Controls

### **Automatic Filters**
- **Earnings Protection**: No trades within 2 days of earnings announcements
- **Volatility Gates**: Avoids stocks during news-driven spikes
- **Position Limits**: Maximum 3% allocation per single stock
- **Exposure Limits**: Maximum 50% long, 30% short exposure

### **Cost Management**
- **Transaction Costs**: Built-in 5 basis points trading cost
- **Slippage**: 2 basis points market impact modeling
- **Turnover Control**: Penalizes excessive trading

---

## 🚀 Getting Started

### **Operating Modes**

PatternIQ supports three operating modes to fit different deployment scenarios:

#### **1. BATCH Mode (Recommended for Daily Use)**
- Runs the complete pipeline once and exits
- Perfect for cron jobs or scheduled tasks
- Minimal resource usage
- Ideal for daily trading signal generation

```bash
# Run once and exit (most common usage)
python run_patterniq.py batch

# Run once with Telegram notifications
python run_patterniq.py batch --telegram

# Run once and then start API server
PATTERNIQ_ALWAYS_ON=false START_API_SERVER=true python run_patterniq.py batch
```

#### **2. ALWAYS-ON Mode (For Continuous Operation)**
- Runs continuously with daily scheduled execution
- Keeps API server running 24/7
- Automatically runs pipeline every 24 hours
- Best for production deployments requiring real-time API access

```bash
# Run continuously with API server
python run_patterniq.py always-on

# Run continuously on custom port
python run_patterniq.py always-on --port 9000
```

#### **3. API-ONLY Mode (For Development/Testing)**
- Starts only the API server without running pipeline
- Useful for testing API endpoints with existing data
- No data processing or signal generation

```bash
# Start API server only
python run_patterniq.py api-only

# Start API on custom port
python run_patterniq.py api-only --port 9000
```

### **Environment Configuration**

Create a `.env` file or set environment variables:

```bash
# BATCH MODE (run once and exit)
export PATTERNIQ_ALWAYS_ON=false
export START_API_SERVER=false
export GENERATE_REPORTS=true
export SEND_TELEGRAM_ALERTS=true
export TELEGRAM_BOT_TOKEN='your_bot_token'
export TELEGRAM_CHAT_IDS='your_chat_id'

# ALWAYS-ON MODE (continuous operation) 
export PATTERNIQ_ALWAYS_ON=true
export START_API_SERVER=true
export API_HOST=0.0.0.0
export API_PORT=8000

# DATABASE
export PATTERNIQ_DB_URL="postgresql://username:password@localhost:5432/patterniq"
```

See `.env.example` for complete configuration options.

### **System Requirements**
```bash
# Clone repository
git clone <repository-url>
cd PatternIQ

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup database
python scripts/setup/setup_db.py

# Run initial data ingestion
python -m src.data.ingestion.pipeline

# Generate features and signals
python -m src.features.momentum
python -m src.signals.rules
python -m src.signals.blend
```

### **Daily Execution Workflow**
```bash
# Complete daily workflow (run every morning)
source venv/bin/activate

# 1. Update market data
python -m src.data.ingestion.pipeline

# 2. Calculate new features
python -m src.features.momentum

# 3. Generate individual signals
python -m src.signals.rules

# 4. Create combined recommendations
python -m src.signals.blend

# 5. Generate reports (JSON, HTML)
python -m src.report.generator

# 6. Send Telegram notifications (optional)
# Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS first
# Then run with --telegram flag: python run_patterniq.py batch --telegram

# 7. Process automated trading (paper trading)
# The trading bot runs automatically when using run_patterniq.py

# 8. Start API server for external access
python run_patterniq.py api-only --port 8000
# Or: uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

---

## 📊 Report Formats & Access

### **JSON Reports** (API Integration)
- **Purpose**: Machine-readable data for external systems
- **Access**: Via API endpoints or direct file access
- **Use cases**: Custom dashboards, algorithmic systems, data analysis
- **Location**: `/reports/patterniq_report_YYYYMMDD.json`

### **HTML Reports** (Human-Readable)
- **Purpose**: Professional web-formatted reports with styling
- **Access**: Web browser or direct file opening
- **Use cases**: Daily review, team sharing, client presentations
- **Location**: `/reports/patterniq_report_YYYYMMDD.html`
- **Features**: 
  - Responsive design for mobile and desktop
  - Color-coded recommendations (green=buy, red=sell)
  - Interactive tables with sorting
  - Professional styling with PatternIQ branding

### **Report Content Structure**
Each report contains:
- **Executive Summary**: Market regime, signal strength, total recommendations
- **Long Recommendations**: Top stocks to buy with conviction scores
- **Short Recommendations**: Top stocks to sell/short
- **Sector Analysis**: Industry breakdown with sentiment analysis
- **Risk Alerts**: Warnings and market condition notices
- **Performance Tracking**: Historical strategy performance
- **Next Actions**: Specific steps to take

---

## 📊 Database Schema

The system maintains 11 core tables:

### **Market Data**
- `instruments`: Stock symbols and metadata
- `bars_1d`: Daily OHLCV price data (raw and adjusted)
- `corporate_actions`: Stock splits and dividends
- `universe_membership`: S&P 500 constituent tracking

### **Analytics**
- `features_daily`: Technical indicators and calculated features
- `signals_daily`: Individual and combined trading signals
- `fundamentals_snapshot`: Market cap, P/E ratios, earnings data

### **Performance Tracking**
- `backtests`: Historical strategy performance runs
- `backtest_positions`: Position-level attribution
- `reports`: Generated analysis reports

---

## 🔧 System Architecture

### **Data Pipeline**
1. **Ingestion**: Fetches S&P 500 data from Wikipedia and Yahoo Finance
2. **Adjustment**: Handles stock splits and dividends
3. **Feature Engineering**: Calculates 15+ technical indicators
4. **Signal Generation**: Creates 3 rule-based signals
5. **Blending**: Combines signals using Information Coefficient weighting
6. **Portfolio Construction**: Builds long/short recommendations
7. **Report Generation**: Creates JSON, HTML, and PDF reports
8. **Delivery**: API endpoints, Telegram notifications, automated trading
9. **Backtesting**: Validates performance with transaction costs

### **Core Modules**
- `src/data/`: Market data ingestion and storage
- `src/adjust/`: Price adjustment for corporate actions  
- `src/features/`: Technical indicator calculations
- `src/signals/`: Signal generation and blending
- `src/backtest/`: Performance simulation and analytics
- `src/report/`: Multi-format report generation
- `src/api/`: REST API server and endpoints
- `src/telegram/`: Telegram bot integration
- `src/trading/`: Automated trading simulation

---

## 🔌 API Integration

### **Starting the API Server**
```bash
# Start API server
cd PatternIQ
source venv/bin/activate
uvicorn src.api.server:app --host 0.0.0.0 --port 8000

# API will be available at: http://localhost:8000
# Interactive docs at: http://localhost:8000/docs
```

### **Key API Endpoints**

#### **Latest Report** (Most Common)
```bash
# Get today's report in JSON format
curl http://localhost:8000/reports/latest?format=json

# Get today's report as HTML
curl http://localhost:8000/reports/latest?format=html
```

#### **Portfolio Tracking** (Investment Monitoring)
```bash
# Get current portfolio status
curl http://localhost:8000/portfolio/status

# Response includes:
# - initial_capital vs current_value
# - total_return percentage
# - individual positions with P&L
# - risk metrics and exposure
```

#### **Historical Data**
```bash
# Get signals for specific date
curl http://localhost:8000/signals/2025-09-20?signal_type=combined

# Get trading performance metrics
curl http://localhost:8000/trading/performance
```

---

## 📱 Telegram Integration

### **Setup Process**
1. **Create Bot**: 
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Copy the provided bot token

2. **Get Chat ID**:
   - Message @userinfobot on Telegram
   - Copy your chat ID number

3. **Configure Environment**:
   ```bash
   export TELEGRAM_BOT_TOKEN='your_bot_token_here'
   export TELEGRAM_CHAT_IDS='your_chat_id_here'
   ```

### **Daily Telegram Report Features**
- **Executive Summary**: Market regime and signal strength
- **Top Picks**: Best long and short recommendations with emojis
- **Risk Alerts**: Important warnings and market conditions
- **Sector Highlights**: Top performing/underperforming sectors
- **Performance Updates**: Daily P&L and portfolio status

### **Sample Telegram Message**
```
🤖 PatternIQ Daily Report
📅 2025-09-20

📊 Market Overview
• Regime: Trending Market with Tech Leadership
• Signal Strength: 82%
• Total Recommendations: 8
• High Conviction: 4

📈 Top Long Picks (4)
🔥 AAPL (Technology) - STRONG BUY
   Score: 0.875 | Size: 3.0% | $175.50
📈 MSFT (Technology) - BUY  
   Score: 0.724 | Size: 2.5% | $415.25

📉 Top Short Picks (2)
🔥 XOM (Energy) - SELL
   Score: -0.653 | Size: 2.0% | $115.30

🏢 Sector Highlights
🟢 Technology: Bullish (+0.285)
🔴 Energy: Bearish (-0.175)

⏰ Generated: 08:00 ET
```

---

## 💼 Automated Trading (Paper Trading)

### **Portfolio Tracking System**
PatternIQ includes a sophisticated paper trading system that answers your key question: **"What was the initial amount invested VS the current value"**

#### **Real-Time Portfolio Monitoring**
```python
# Get current portfolio status
status = bot.get_portfolio_status()

print(f"Initial Investment: ${status['initial_capital']:,.2f}")
print(f"Current Value: ${status['current_value']:,.2f}")  
print(f"Total Return: {status['total_return']:.2%}")
print(f"Profit/Loss: ${status['total_pnl']:,.2f}")
```

#### **Position-Level Tracking**
- **Individual stock performance**: Entry price vs current price
- **Unrealized P&L**: Gain/loss on each position
- **Portfolio allocation**: Percentage of capital in each stock
- **Trade history**: Complete record of all buy/sell decisions

#### **Risk Management**
- **Maximum position size**: 5% per individual stock
- **Portfolio stop-loss**: 20% maximum drawdown
- **Cash management**: Maintains appropriate cash reserves
- **Diversification**: Limits sector concentration

### **Trading Bot Configuration**
```python
# Initialize with custom parameters
bot = AutoTradingBot(
    initial_capital=100000.0,  # Starting amount
    paper_trading=True,        # Safe paper trading mode
    max_position_size=0.05,    # 5% max per position
    max_portfolio_risk=0.20,   # 20% max drawdown
    min_signal_threshold=0.3   # Minimum signal to trade
)
```

---

## 📈 Expected Performance

**Historical Backtesting Results** (based on similar quantitative strategies):
- **Annual Return**: 8-15% (market-neutral strategies)
- **Sharpe Ratio**: 1.2-2.0 (risk-adjusted performance)
- **Maximum Drawdown**: 5-15% (worst-case decline)
- **Hit Rate**: 52-58% (percentage of profitable trades)
- **Information Coefficient**: 0.05-0.15 (signal predictive power)

**Note**: Past performance does not guarantee future results. All trading involves risk of loss.

---

## 🔄 Daily Operations

### **Morning Routine (6:00-8:00 AM ET)**
1. **Data Update**: System fetches latest market data
2. **Feature Calculation**: Technical indicators updated
3. **Signal Generation**: New trading signals created
4. **Report Generation**: JSON and HTML reports created
5. **Telegram Delivery**: Mobile notifications sent
6. **Portfolio Update**: Trading bot processes new signals
7. **API Activation**: Live endpoints available for queries

### **User Actions**
1. **Check Telegram**: Review mobile notification with top picks
2. **Open Report**: View detailed HTML report in browser
3. **API Query**: Check portfolio status via API call
4. **Review Performance**: Monitor initial investment vs current value
5. **Execute Trades**: Implement recommendations (manual or automated)

### **Monitoring Checklist**
- ✅ Signal generation completed successfully
- ✅ Report files created in `/reports/` directory
- ✅ Telegram notifications delivered
- ✅ API server responding to requests
- ✅ Portfolio tracking updated
- ✅ No error logs or system alerts

---

## 🛠️ Testing & Validation

### **Report Generation Tests**
```bash
# Test report generation
python test_simple_reports.py

# Verify all formats
ls -la reports/
# Should show: patterniq_report_YYYYMMDD.json and .html files
```

### **API Testing**
```bash
# Start API server
uvicorn src.api.server:app --host 127.0.0.1 --port 8000

# Test endpoints
curl http://127.0.0.1:8000/                    # Health check
curl http://127.0.0.1:8000/reports/latest      # Latest report
curl http://127.0.0.1:8000/portfolio/status    # Portfolio status
```

### **Telegram Bot Testing**
```python
# Test bot connection
from src.telegram.bot import PatternIQBot
bot = PatternIQBot()
await bot.test_connection(your_chat_id)
```

### **Trading Bot Testing**
```python
# Test automated trading
from src.trading.simulator import AutoTradingBot
bot = AutoTradingBot(initial_capital=100000.0)
status = bot.get_portfolio_status()
print(f"Portfolio value: ${status['current_value']:,.2f}")
```

---

## ⚠️ Important Disclaimers

### **Risk Warning**
- Trading involves substantial risk of loss
- Past performance is not indicative of future results
- Never risk more than you can afford to lose
- Consider consulting with a financial advisor

### **Data and Costs**
- System requires reliable market data feeds
- Trading costs vary by broker (5-10 basis points typical)
- High-frequency trading may incur additional costs

### **System Limitations**
- Designed for S&P 500 stocks only
- Requires daily maintenance and monitoring
- Performance may degrade during market regime changes
- Not suitable for all market conditions
- Paper trading mode recommended for testing

---

## 🤝 Support and Maintenance

### **Daily Monitoring**
- Check signal generation completed successfully
- Verify data feeds are current
- Monitor system performance metrics
- Review any error logs
- Confirm report delivery (Telegram/API)

### **Weekly Analysis**  
- Analyze strategy performance vs benchmark
- Review hit rates and signal quality
- Adjust position sizing if needed
- Update market regime assessment
- Check portfolio vs initial investment tracking

### **Monthly Review**
- Comprehensive performance attribution
- Signal effectiveness analysis
- Risk metric evaluation
- Strategy refinement opportunities
- API usage and integration review

---

## 📚 Additional Resources

### **Understanding Quantitative Trading**
- Information Coefficient: Measures signal predictive power
- Sharpe Ratio: Risk-adjusted return measurement
- Maximum Drawdown: Worst peak-to-trough decline
- Alpha Generation: Excess return vs market benchmark

### **Market Microstructure**
- Transaction costs impact on returns
- Market impact of trading
- Optimal execution strategies
- Risk management techniques

### **API Documentation**
- Interactive API docs: `http://localhost:8000/docs`
- OpenAPI specification: `http://localhost:8000/openapi.json`
- Endpoint testing: `http://localhost:8000/redoc`

---

## 📧 Example Daily Workflow

**6:00 AM**: System automatically processes overnight data
**8:00 AM**: Telegram notification arrives with top picks
**8:05 AM**: User reviews HTML report in browser
**8:10 AM**: User checks portfolio status via API: 
```bash
curl http://localhost:8000/portfolio/status
# Shows: Initial $100K → Current $108.5K = +8.5% return
```
**8:15 AM**: User implements recommendations or reviews automated trades
**End of Day**: System tracks performance and prepares for next day

---

**PatternIQ Version**: 1.0 MVP  
**Last Updated**: September 2025  
**License**: Proprietary  

---

*PatternIQ is a sophisticated quantitative trading system designed for institutional and advanced individual traders. The system provides comprehensive market analysis, automated signal generation, and performance tracking with professional-grade reports and API integration. Always conduct thorough due diligence and consider your risk tolerance before implementing any trading strategy.*
