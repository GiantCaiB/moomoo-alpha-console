# AGENTS.md

This document is for coding agents taking over this repository. Read it before making changes.

## Project Name

**Alpha Cockpit**

A read-only trading research cockpit for monitoring a real Moomoo account, reviewing entry signals, managing existing holdings, and checking risk status.

This project is **not** an automated trading bot.

---

## Prime Directive

**Safety first. Read-only first. No live trading.**

Agents must not add, enable, or accidentally re-enable functionality that can place, approve, modify, or cancel real broker orders.

The app may display real Moomoo account data, real positions, and real orders, but all trading actions must remain manual in the Moomoo app.

Do not:

- Place orders
- Cancel orders
- Modify orders
- Approve orders
- Create stop orders
- Auto-sell
- Auto-buy
- Auto-trim positions
- Auto-enter tail mode
- Enable live trading
- Add hidden automation that changes broker state

If in doubt, keep behavior read-only.

---

## High-Level Architecture

```text
Frontend:      Next.js / React / TypeScript
Backend:       FastAPI / Python
Database:      SQLite
Broker:        Moomoo OpenD
Market Data:   yfinance + SQLite K-line cache
Runtime Mode:  Moomoo real account, read-only
```

### Core Responsibilities

```text
Moomoo OpenD
  - Account summary
  - Cash
  - Positions
  - Open orders
  - Broker health
  - Position prices when available

YFinance / K-Line Cache
  - Historical daily bars
  - Benchmark bars, usually SPY
  - Technical indicators
  - Price fallback latest close

FastAPI Backend
  - Broker adapter
  - K-line service
  - Price resolver
  - Entry signal engine
  - Position guidance engine
  - Risk/read-only enforcement

Next.js Frontend
  - Cockpit
  - Entry Signals
  - Portfolio
  - Orders
  - Risk
  - Labs
  - Settings
```

---

## Product Navigation

Preferred UI naming:

| Route Area | UI Name | Purpose |
|---|---|---|
| Dashboard | Cockpit | Overview of account, alerts, risk, and data health |
| Signals | Entry Signals | New position research ideas |
| Positions | Portfolio | Current holdings and position guidance |
| Orders | Orders | Read-only order display from Moomoo |
| Risk | Risk | Read-only safety and broker status |
| Backtests | Labs | Future experiments/backtesting |
| Settings | Settings | Runtime/configuration visibility |

Do not create a separate sidebar item for Position Signals. Position guidance belongs under:

```text
Portfolio -> Position Management
```

---

## Domain Separation

The app has three separate decision domains.

### 1. Entry Signals

Question answered:

```text
Should I consider opening a new position?
```

This uses the Momentum Relative Strength Screener.

Signals:

- `BUY_STARTER`
- `WATCH`
- `AVOID`
- `DATA_ERROR`

Entry Signals scan the configured Trading Universe.

They do **not** manage current holdings.

---

### 2. Position Guidance

Question answered:

```text
How should I manage positions I already own?
```

Position Guidance scans current Moomoo holdings only:

```text
quantity > 0
```

It does not scan the Trading Universe and does not recommend new entries.

Position Guidance includes:

1. Profit Tail logic for winners
2. Loss defense logic for losers/deteriorating positions

All guidance is read-only.

---

### 3. Risk / Safety

Question answered:

```text
Is the system safe, connected, and blocked from trading?
```

Risk must clearly show:

- Read-only mode active
- Live trading disabled
- Order actions blocked
- Broker connection state

---

## Broker and Data Source Rules

### Moomoo Usage

Moomoo OpenD is used for:

- Real account value
- Cash
- Positions
- Orders
- Broker status
- Real-time quote/snapshot when available
- Position current price when available

Moomoo historical K-line API should **not** be used in normal runtime because of quota/availability issues.

### K-Line Data

Historical bars should come from the configured `KLineProvider`, currently yfinance.

Expected source labels:

```text
data_source = moomoo_snapshot_plus_yfinance_kline
price_source = moomoo_snapshot | moomoo_position_current_price | yfinance_cached_latest_close
bar_source = yfinance_cached_daily_bars
is_real_market_data = true
```

### Price Resolver Priority

Use the established priority:

1. Moomoo quote/snapshot `last_price`
2. Moomoo position `current_price`
3. Latest close from yfinance cached/fetched bars
4. `DATA_ERROR`

Important ordering:

```text
Load/fetch daily bars first.
Then resolve price using those bars as fallback.
Then score/generate signals.
```

Do not reintroduce the old dead loop where price resolution runs before K-line data is available.

---

## Trading Universe Rules

Trading Universe is for Entry Signals only.

Priority:

1. DB `app_settings.trading_universe` if present and valid
2. Config/environment default if DB override is absent
3. If DB override exists but is invalid, fail fast; do not silently fallback

Reserved invalid symbols include:

```text
MOOMOO
YFINANCE
MOCK
PAPER
REAL
SIMULATE
BROKER
ACCOUNT
PORTFOLIO
CASH
NYSE
NASDAQ
AMEX
```

Do not allow a reserved word like `MOOMOO` to become a universe symbol.

---

## Entry Signal Logic

The Entry Signal engine is a Momentum Relative Strength Screener.

Score components:

```text
Trend:                 25
Relative Strength:     20
Volume Confirmation:   10
Entry Quality:         15
Risk / Reward:         15
Market Regime:         15
Total:                100
```

Signal classification should separate valid weak setups from data failures.

Rules:

- `DATA_ERROR` only for missing/invalid data
- `AVOID` can still have a non-zero score
- Hard filter failures should preserve computed score and explain failed filters
- Do not set valid AVOID signals to score 0

UI sections:

- Buy Candidates
- Watchlist Candidates
- Avoid / No Setup
- Data Issues

Important UI copy:

```text
Entry Signals evaluate new position ideas. Existing holdings are managed under Portfolio -> Position Management.
```

---

## Position Guidance Logic

Position Guidance is read-only and applies only to current holdings.

Execution order:

1. Read current Moomoo positions
2. Filter `quantity > 0`
3. Load or create lifecycle state
4. Load daily K-line bars via `KLineService.get_cached_or_fetch_daily_bars(symbol)`
5. Resample daily bars to weekly bars
6. Resolve current price via `PriceResolver.resolve(symbol, bars=daily_bars)`
7. Generate guidance from `avg_cost`, `current_price`, bars, trend, and lifecycle state
8. Store results
9. Do not mutate broker state
10. Do not automatically mutate trim flags or tail mode

---

## Position Guidance Signals

Existing/proposed signal set:

```text
HOLD
TRIM_PROFIT
ENTER_TAIL_MODE
HOLD_TAIL
TRIM_TAIL
EXIT_TAIL
REVIEW_POSITION
STOP_ADDING
REDUCE_RISK
EXIT_POSITION
DATA_ERROR
```

Human-readable UI labels:

| Raw Signal | UI Label |
|---|---|
| HOLD | Hold |
| TRIM_PROFIT | Trim Profit |
| ENTER_TAIL_MODE | Enter Tail Mode |
| HOLD_TAIL | Hold Tail |
| TRIM_TAIL | Trim Tail |
| EXIT_TAIL | Exit Tail |
| REVIEW_POSITION | Review |
| STOP_ADDING | Stop Adding |
| REDUCE_RISK | Reduce Risk |
| EXIT_POSITION | Exit Review |
| DATA_ERROR | Data Issue |

Do not expose raw enum names in the UI unless in debug/details.

---

## Profit Tail Rules

Profit Tail manages winning positions.

Current rules:

```text
If tail_mode = false:
  gain >= 100% -> ENTER_TAIL_MODE
  gain >= 75% and trim_75_done = false -> TRIM_PROFIT, trim 20%
  gain >= 50% and trim_50_done = false -> TRIM_PROFIT, trim 15%
  gain >= 25% and trim_25_done = false -> TRIM_PROFIT, trim 10%
  otherwise -> HOLD

If tail_mode = true:
  weekly_close >= weekly_sma20 -> HOLD_TAIL
  weekly_close < weekly_sma20 and weekly_close >= weekly_sma30 -> TRIM_TAIL
  weekly_close < weekly_sma30 -> EXIT_TAIL
  drawdown_from_high >= 35% -> EXIT_TAIL
```

`ENTER_TAIL_MODE` should suggest recovering cost basis and keeping a remaining profit tail.

Do not automatically set `tail_mode = true` just because the signal appears. The user must manually confirm lifecycle state in a future UI/control flow.

---

## Loss Defense Rules

Loss Defense is part of the same Position Guidance logic. It prevents a dangerous “never stop loss” behavior.

Do not create a separate module/page unless explicitly requested.

Simple v1 rules:

```text
If data invalid:
  DATA_ERROR

If gain > -8%:
  HOLD

If gain <= -8%:
  REVIEW_POSITION
  reason: Position down more than 8%; review thesis and risk.

If gain <= -15%:
  STOP_ADDING
  reason: Position down more than 15%; do not add until thesis/trend improves.

If gain <= -20%:
  REDUCE_RISK
  reason: Position down more than 20%; consider reducing exposure manually.

If gain <= -30%:
  EXIT_POSITION
  reason: Position down more than 30%; major risk threshold breached. Review exit manually.
```

Technical tightening:

```text
If price < SMA200 and gain <= -15% -> STOP_ADDING
If price < SMA200 and gain <= -20% -> REDUCE_RISK
If price < SMA200 and gain <= -30% -> EXIT_POSITION
If drawdown_from_high >= 35% -> EXIT_POSITION
```

Guidance must remain advisory:

```text
Guidance only. No trades are placed.
```

---

## Position Guidance Priority

Use highest severity / most relevant signal.

Recommended priority:

```text
DATA_ERROR
EXIT_POSITION
REDUCE_RISK
STOP_ADDING
REVIEW_POSITION
EXIT_TAIL
TRIM_TAIL
ENTER_TAIL_MODE
TRIM_PROFIT
HOLD_TAIL
HOLD
```

Notes:

- Loss defense should prevent losing positions from being permanent HOLD.
- Profit Tail applies to profitable positions.
- Tail-specific rules apply when `tail_mode = true`.
- Do not let normal HOLD override defense guidance.

---

## Lifecycle State

Position lifecycle state tracks local management metadata:

- original entry price
- original quantity
- original cost basis
- highest price since entry
- trim flags
- tail mode
- tail start state
- notes

Current behavior:

- `highest_price_since_entry` may update with current price
- `trim_*_done` should not auto-update from signal generation
- `tail_mode` should not auto-update from signal generation

Future UI may add manual buttons:

- Mark 25% trim done
- Mark 50% trim done
- Mark 75% trim done
- Mark as tail mode
- Reset lifecycle state

These must only update local lifecycle state, never broker state.

---

## Dashboard / Cockpit Rules

Cockpit should be an overview, not a raw data dump.

Show:

- Portfolio value
- Cash
- Day P&L
- Open order count
- Read-only status
- Entry Signal Highlights
- Position Action Alerts
- Risk Status
- Data Health
- Holdings preview

Do not show normal HOLD rows as alerts.

Position Action Alerts should include:

```text
TRIM_PROFIT
ENTER_TAIL_MODE
TRIM_TAIL
EXIT_TAIL
REVIEW_POSITION
STOP_ADDING
REDUCE_RISK
EXIT_POSITION
```

If none:

```text
No active position management alerts.
```

Dashboard currently should not auto-generate signals unless explicitly implemented and requested. Prefer manual refresh actions.

---

## Orders Page Rules

Orders are read-only.

Display orders from Moomoo, grouped by status:

- Pending
- Filled
- Cancelled

Recommended columns:

```text
Symbol | Side | Status | Qty | Limit Price | Filled | Action
```

Do not repeat long read-only text in every row.

Use top banner:

```text
Read-only: manage or cancel orders in the Moomoo app.
```

Each row can show a small lock icon or muted `Locked` text.

---

## Table / Row Alignment Rules

Use semantic tables or CSS grid with explicit column templates. Avoid loose flex rows for tabular data.

Rules:

- Text columns left aligned
- Numeric columns right aligned
- Header and body columns must align exactly
- Use `font-variant-numeric: tabular-nums` for numbers
- Use consistent row height, about 44px to 52px
- Add subtle separators and hover states
- Expanded rows should span all columns

### Portfolio Holdings Columns

```text
Symbol | Status | Qty | Avg Cost | Last Price | Unrealized P&L | Day P&L | Stop | Weight
```

Split Symbol and Status into separate columns.

### Orders Columns

```text
Symbol | Side | Status | Qty | Limit Price | Filled | Action
```

### Entry Signal Collapsed Row Columns

```text
Symbol | Signal Badge | Source Badge | Factor Chips | Score | Info Icon
```

Scores should display like:

```text
Score 71 / 100
```

---

## UI / Visual Design Rules

Design direction:

```text
Dark glass trading cockpit with subtle neon accents.
```

Use colors consistently:

- Green: connected, positive P&L, valid data, buy candidate
- Red: danger, negative P&L, avoid, exit
- Amber: warning, read-only, watch, trim
- Purple: position guidance / Profit Tail
- Blue/Cyan: market data / technical info

Avoid:

- Bright green everywhere
- Over-glowing panels
- Raw enum names in UI
- Fake precision
- Huge empty panels
- Misaligned tables
- All-caps long text

Use readable names:

| Avoid | Prefer |
|---|---|
| Signals | Entry Signals |
| Positions | Portfolio |
| Position Signals | Position Management / Position Guidance |
| BUY SIGNALS | Buy Candidates |
| WATCH LIST | Watchlist Candidates |
| AVOID / NO SIGNAL | Avoid / No Setup |
| Run Screener | Run Entry Screener |
| Run Position Signals | Refresh Position Guidance |

---

## Stale Signals

Stale signals can mean more than local/mock data.

A stale signal may be:

- local/mock data
- `is_real_market_data = false`
- outside the current Trading Universe

Do not hardcode UI copy saying stale always means local/mock.

Better copy:

```text
1 signal outside current universe hidden.
```

or:

```text
1 stale/mock signal hidden.
```

The delete action should align with the stale-count definition.

---

## Testing Commands

Backend:

```bash
cd backend
python -m pytest tests/ -v
```

Frontend:

```bash
cd frontend
npm run build
```

Run both after meaningful changes.

---

## Required Test Coverage For Strategy Changes

When changing Position Guidance, add/update tests for:

- gain -5% -> HOLD
- gain -8% -> REVIEW_POSITION
- gain -15% -> STOP_ADDING
- gain -20% -> REDUCE_RISK
- gain -30% -> EXIT_POSITION
- price below SMA200 + gain <= -20% -> REDUCE_RISK
- drawdown_from_high >= 35% -> EXIT_POSITION
- gain +25% still TRIM_PROFIT
- gain +100% still ENTER_TAIL_MODE
- no orders placed
- no cancel attempted
- read-only safety unchanged

When changing Entry Signals, add/update tests for:

- DATA_ERROR only for invalid/missing data
- AVOID can preserve non-zero score
- WATCH is not treated as BUY
- Moomoo/yfinance real-market labels are correct
- no local/mock rows generated in Moomoo runtime

---

## Common Pitfalls

Do not reintroduce these problems:

1. Moomoo historical K-line requests in normal runtime
2. Mock/local generated signals appearing in Moomoo runtime
3. `MOOMOO` or other reserved words becoming universe symbols
4. PriceResolver running before bars are loaded
5. Valid AVOID signals getting score 0
6. Position Guidance mixed into Entry Signals
7. HOLD rows shown as dashboard alerts
8. UI saying stale means local/mock when stale is out-of-universe
9. Tables built with loose flex rows causing misalignment
10. Any order action becoming enabled

---

## Agent Workflow

Before changing code:

1. Identify whether the request is backend, frontend, strategy, or UX-only.
2. Preserve read-only guarantees.
3. Keep Entry Signals and Position Guidance separate.
4. Prefer small scoped changes over large refactors.
5. Avoid new architecture unless explicitly requested.

After changing code:

1. Run relevant backend tests.
2. Run frontend build if UI changed.
3. Confirm no trading actions were added.
4. Summarize files changed and behavior changed.
5. Mention any skipped tests honestly.

---

## One-Sentence Project Summary

Alpha Cockpit is a read-only trading research cockpit: Entry Signals find new ideas, Position Guidance manages existing holdings, and Risk ensures the system never trades automatically.
