# Alpha Cockpit

**Alpha Cockpit** is a read-only trading research dashboard for monitoring a real Moomoo account, reviewing portfolio exposure, generating entry signals, and managing existing positions with rule-based guidance.

It is designed as a personal trading cockpit: real account visibility, market-data-backed signals, position management alerts, and risk status — without automated trading.

> **Important:** Alpha Cockpit is a research and monitoring tool only. It does not place trades, cancel orders, or execute automated strategies.

---

## Overview

Alpha Cockpit connects to **Moomoo OpenD** for real account data and uses cached market data for research calculations. The goal is to help traders answer three separate questions:

1. **What new opportunities should I watch?**  
   Handled by Entry Signals.

2. **How should I manage positions I already own?**  
   Handled by Position Guidance.

3. **Is my account and system state safe?**  
   Handled by Risk and Broker Health.

The application is intentionally read-only. All trading decisions must be reviewed and executed manually in the broker platform.

---

## Key Features

### Real Account Dashboard

- Portfolio value
- Cash balance
- Current holdings
- Open orders
- Read-only broker status
- Data source health
- Risk status overview

### Entry Signals

Entry Signals evaluate potential new position ideas using a momentum and relative strength model.

Signal categories include:

- `BUY_STARTER`
- `WATCH`
- `AVOID`
- `DATA_ERROR`

The screener uses market data, cached historical bars, and benchmark comparison to score candidates.

### Position Guidance

Position Guidance manages existing holdings only. It does not scan the full trading universe and does not generate new entry ideas.

It combines two concepts:

#### Profit Tail

A staged profit-taking framework designed to avoid selling entire winners too early.

Example guidance:

- Trim partial profit at defined gain thresholds
- Enter tail mode after major gains
- Hold tail positions while long-term trend remains intact
- Trim or exit tail positions when trend deteriorates

#### Loss Defense

A defensive layer that prevents the strategy from becoming a “never stop loss” system.

Example guidance:

- Review deteriorating positions
- Stop adding to losing positions
- Reduce risk when losses deepen
- Review exit when major risk thresholds are breached

All Position Guidance is read-only and advisory.

### Risk & Safety

- Live trading disabled
- Order actions blocked
- Read-only mode enforced
- Broker health monitoring
- Risk limit visibility

### Market Data

- Moomoo OpenD for account, positions, orders, and real-time account context
- yfinance-backed historical K-line data
- SQLite cache for historical bars
- Price fallback logic for more reliable signal generation

---

## Architecture

Alpha Cockpit is built with a modern full-stack architecture:

```text
Frontend:     Next.js / React / TypeScript
Backend:      FastAPI / Python
Database:     SQLite
Broker:       Moomoo OpenD
Market Data:  yfinance + local cache
```

High-level flow:

```text
Moomoo OpenD
   ├── Account summary
   ├── Positions
   ├── Orders
   └── Broker status

yfinance / K-Line Cache
   ├── Historical daily bars
   ├── Benchmark data
   └── Technical indicators

FastAPI Backend
   ├── Entry signal engine
   ├── Position guidance engine
   ├── Risk checks
   └── API routes

Next.js Frontend
   ├── Cockpit
   ├── Entry Signals
   ├── Portfolio
   ├── Orders
   ├── Risk
   └── Settings
```

---

## Pages

### Cockpit

The main overview screen for account status, active alerts, holdings, and system health.

### Entry Signals

Research page for new position ideas.  
This page answers:

> “Should I consider opening a new position?”

### Portfolio

Portfolio holdings and position management guidance.  
This page answers:

> “How should I manage positions I already own?”

### Orders

Read-only view of open and historical Moomoo orders.

### Risk

Safety and broker status panel.

### Settings

Configuration for broker mode, trading universe, market data, risk limits, and read-only state.

### Labs

Experimental area for future backtesting, expectancy analytics, and strategy research.

---

## Signal Philosophy

Alpha Cockpit separates trading research into different domains.

```text
Entry Signals
Evaluate new trade ideas.

Position Guidance
Manage existing holdings.

Risk
Prevent unsafe behavior.
```

This separation avoids mixing “should I buy?” with “how should I manage what I already own?”

A symbol may appear in both Entry Signals and Portfolio, but the meaning is different.

For example:

- Entry Signals may say a stock is not a good new setup.
- Position Guidance may still say to hold it because it is already owned and has not triggered a management action.

These are not conflicts. They answer different questions.

---

## Read-Only Design

Alpha Cockpit is designed to be safe by default.

The application does **not**:

- Place market orders
- Place limit orders
- Cancel existing orders
- Modify broker positions
- Automatically trim positions
- Automatically enter tail mode
- Automatically stop-loss positions
- Run live trading strategies

All guidance is informational only.

Trading actions must be performed manually in Moomoo or another broker platform.

---

## Position Guidance Logic

### Profit Tail

Profit Tail is used for profitable positions.

Example rules:

```text
Gain >= 25%   -> Trim Profit
Gain >= 50%   -> Trim Profit
Gain >= 75%   -> Trim Profit
Gain >= 100%  -> Enter Tail Mode
Tail weakens  -> Trim Tail or Exit Tail
```

The goal is to recover profit gradually while leaving room for exceptional winners.

### Loss Defense

Loss Defense is used for losing or deteriorating positions.

Example rules:

```text
Loss <= -8%   -> Review Position
Loss <= -15%  -> Stop Adding
Loss <= -20%  -> Reduce Risk
Loss <= -30%  -> Exit Review
```

The goal is to avoid unlimited averaging down and prevent small losses from becoming portfolio-damaging losses.

---

## Entry Signal Model

The Entry Signal engine uses a momentum and relative strength score.

Example components:

- Trend strength
- Relative strength vs benchmark
- Volume confirmation
- Entry quality
- Risk / reward
- Market regime

The output is a score from 0 to 100 and a signal classification.

```text
BUY_STARTER  -> potential starter position candidate
WATCH        -> strong enough to monitor, not yet a buy candidate
AVOID        -> no valid setup
DATA_ERROR   -> insufficient or invalid data
```

---

## Data Sources

Alpha Cockpit uses multiple data sources depending on the task.

### Moomoo OpenD

Used for:

- Account value
- Cash
- Positions
- Orders
- Broker status
- Position-level prices when available

### yfinance

Used for:

- Historical daily bars
- Technical indicators
- Benchmark comparison
- Fallback latest close

### SQLite Cache

Used to reduce repeated historical data requests and improve local runtime performance.

---

## Safety Principles

Alpha Cockpit follows these principles:

1. **Read-only first**
2. **No automatic trading**
3. **Separate entry logic from position management**
4. **Use real account data carefully**
5. **Prefer explicit guidance over hidden automation**
6. **Protect against stale or mock data**
7. **Do not silently fall back to invalid trading universes**
8. **Make data sources visible to the user**

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Moomoo OpenD installed and running
- A Moomoo account configured in OpenD
- SQLite

---

## Backend Setup

From the backend directory:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn app.main:app --reload --port 8020
```

The backend will be available at:

```text
http://localhost:8020
```

---

## Frontend Setup

From the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

---

## Configuration

Configuration is managed through environment variables and the Settings page.

Common configuration areas:

- Broker mode
- Moomoo OpenD host and port
- Trading universe
- Risk limits
- Market data provider
- Historical bar lookback
- Cache behavior
- Read-only safety mode

Example environment variables may include:

```env
BROKER_MODE=moomoo
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
READ_ONLY=true
KLINE_PROVIDER=yfinance
```

---

## Running Tests

Backend tests:

```bash
cd backend
python -m pytest tests/ -v
```

Frontend build:

```bash
cd frontend
npm run build
```

---

## Project Status

Alpha Cockpit is currently a personal research project focused on:

- Read-only account visibility
- Entry signal research
- Position management guidance
- Risk monitoring
- UI/UX refinement
- Future expectancy analytics and backtesting

Planned areas:

- Strategy expectancy analytics
- Backtesting lab
- Signal performance tracking
- Better portfolio-level risk analytics
- Manual lifecycle controls for trim and tail state
- More advanced data health monitoring

---

## Disclaimer

This project is for educational and research purposes only.

It is not financial advice.  
It is not an automated trading system.  
It does not guarantee profits.  
Trading and investing involve risk, including the possible loss of capital.

You are responsible for your own trading decisions.

---

## License

This project is currently private/personal.  
Add a license before making it public.
