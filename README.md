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
<img width="1898" height="1355" alt="image" src="https://github.com/user-attachments/assets/30fc880d-b6eb-492a-984c-b38af8783e88" />


- Portfolio value
- Cash balance
- Current holdings
- Open orders
- Read-only broker status
- Data source health
- Risk status overview

### Entry Signals

Entry Signals evaluate potential new position ideas using a momentum and relative strength model.
<img width="1889" height="1411" alt="image" src="https://github.com/user-attachments/assets/38b33e61-144f-476b-8e5e-070488c364e2" />


Signal categories include:

- `BUY_STARTER`
- `WATCH`
- `AVOID`
- `DATA_ERROR`

The screener uses market data, cached historical bars, and benchmark comparison to score candidates.

### Position Guidance

Position Guidance manages existing holdings only. It does not scan the full trading universe and does not generate new entry ideas.
<img width="1865" height="1414" alt="image" src="https://github.com/user-attachments/assets/5d545331-5329-4b02-ad52-9e0030a79c5e" />


### Current Holding Filtering

Position Guidance evaluates only current broker holdings with `quantity > 0`. Old, test, or inactive symbols that exist in the database but are no longer held are hidden from the default view. This prevents stale or test rows (e.g., a symbol you no longer own) from appearing in Action Alerts, Hold Positions, or Data Issues sections.

The `GET /api/v1/position-signals` endpoint fetches current broker positions before returning results. If the broker cannot be reached, the endpoint returns an empty list rather than silently falling back to all database records.

An `include_inactive=true` query parameter is available for debugging and history views.

### Per-Symbol Batch Behavior

Each position is evaluated independently. If one symbol fails (e.g., due to a K-line cache write error), that symbol produces a `DATA_ERROR` signal while the remaining symbols continue normally. A single failure does not block the entire batch.

### Profit Tail

A staged profit-taking framework designed to avoid selling entire winners too early.

Example guidance:

- Trim partial profit at defined gain thresholds
- Enter tail mode after major gains
- Hold tail positions while long-term trend remains intact
- Trim or exit tail positions when trend deteriorates

### Loss Defense

A defensive layer that prevents the strategy from becoming a "never stop loss" system.

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

Experimental area for future analytics and strategy research.

Planned modules:

- **Expectancy Lab** — Track and analyze realized entry and exit performance over time. Compute average risk/reward, win rate, and expectancy per strategy profile.
- **Backtesting** — Run strategy profiles against historical data to simulate how signals would have performed. Compare different parameter sets.
- **Strategy Comparison** — Side-by-side comparison of multiple strategy profiles and their signal outputs.
- **Tail Winner Analysis** — Review positions that entered tail mode and their subsequent performance. Analyze drawdown triggers and tail exit quality.
- **Loss Defense Impact** — Analyze how loss defense rules would have affected historical portfolio drawdown and recovery.

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

## Strategy Profiles

Alpha Cockpit supports configurable strategy profiles for both Entry Signals and Position Guidance. Profiles are stored in SQLite and managed via the Settings page or API.

### Entry Signal Profile

- **Name:** Momentum Relative Strength v1
- **Type:** `entry_signal`
- Evaluates new position ideas using trend strength, relative strength vs benchmark, volume confirmation, entry quality, risk/reward, and market regime scoring.
- Configurable via `parameters_json` in the database.

### Position Guidance Profile

- **Name:** Profit Tail + Loss Defense v1
- **Type:** `position_guidance`
- Evaluates current broker holdings for profit-taking and loss-defense signals.
- Configurable thresholds: trim thresholds, tail entry threshold, loss defense percentages, tail exit SMA periods, drawdown exit percentage.

### Profile Metadata

Each profile stores:

| Field | Description |
|---|---|
| `id` | UUID primary key |
| `name` | Human-readable name |
| `type` | `entry_signal` or `position_guidance` |
| `version` | Semver version string |
| `parameters_json` | JSON blob with tunable strategy parameters |
| `rules_summary` | Human-readable explanation of the strategy rules |
| `is_default` | Whether this profile is used when no explicit profile is specified |
| `created_at` / `updated_at` | Timestamps |

### Signal Storage

Generated signals store the active profile's `strategy_profile_id`, `strategy_version`, and a `parameters_snapshot_json` of the parameters used at generation time. This allows reconstructing which strategy version and parameters produced a given signal, even if the profile is later modified.

---

## Current vs Historical Records

All generated signals (entry signals and position management signals) are persisted in SQLite as historical records. The default UI and API views filter to the current context to avoid showing stale or irrelevant data.

### Entry Signals Context Filtering

- Default view includes only signals whose symbols are in the current **Trading Universe** and use real market data.
- Signals for symbols no longer in the universe, or produced from local/mock data, are considered "stale" and are hidden by default.
- Stale signals can be reviewed via `include_local` or stale-count endpoints.

### Position Guidance Context Filtering

- Default view includes only signals for symbols currently held in the broker account (`quantity > 0`).
- Old or test signals for symbols no longer held (e.g., a research symbol like ZXCV) are hidden.
- Debug/history views via `include_inactive=true` may show old records.

### Stale Cleanup

- **Entry Signals:** `DELETE /api/v1/signals/stale` removes signals that are local/mock, out-of-universe, or not real market data.
- **Position Guidance:** `DELETE /api/v1/position-signals/stale` removes signals for symbols no longer in current holdings. Supports `?dry_run=true` to preview deletions.

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

Historical daily bars from yfinance are cached in the `bars_1d` table to reduce repeated requests and improve runtime performance.

Key behaviors:

- Cached rows store the `source` provider (e.g., `"yfinance"`) so the origin of the data is traceable.
- The cache is updated lazily: on cache miss, bars are fetched from upstream, written to SQLite, and returned.
- Cache write failures are isolated per symbol. A failed write for one symbol does not poison the session or affect other symbols in the same batch run.
- A `begin_nested()` savepoint is used for cache writes so that a write failure rolls back only the cache insert, not the outer transaction.
- Before each K-line cache write, the `source` column is explicitly set to `"yfinance"` to satisfy the NOT NULL constraint.

---

## API Overview

Key backend endpoints for signal generation and strategy profiles:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/strategy-profiles` | List all strategy profiles, optionally filtered by `type` |
| `GET` | `/api/v1/strategy-profiles/{id}` | Get a single strategy profile by ID |
| `POST` | `/api/v1/signals/run` | Run Entry Signal screener (evaluates Trading Universe symbols) |
| `GET` | `/api/v1/signals` | List current entry signals (filters by Trading Universe + real market data) |
| `GET` | `/api/v1/signals/stale-count` | Count stale/local/out-of-universe signals |
| `DELETE` | `/api/v1/signals/stale` | Remove stale entry signals |
| `POST` | `/api/v1/position-signals/run` | Run Position Guidance (evaluates current broker holdings) |
| `GET` | `/api/v1/position-signals` | List latest position signals (filters by current broker holdings by default; use `?include_inactive=true` for all) |
| `DELETE` | `/api/v1/position-signals/stale` | Remove position signals for symbols no longer held (`?dry_run=true` to preview) |

All endpoints are read-only except signal generation and stale cleanup, which write to the local SQLite database only. No broker orders are ever placed or cancelled.

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
