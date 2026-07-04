# Moomoo Alpha Console

A local-first, long-running trading dashboard for US stock swing trading, built on top of **moomoo OpenD / Futu OpenAPI**.

> **⚠️ WARNING**
> This software is for research and personal trading workflow automation. It does not guarantee profits. Trading involves risk of loss. Live trading must be enabled explicitly and should only be used after testing with paper mode.

---

## What It Does

- Connects to moomoo OpenD for read-only account display — positions, portfolio, open orders, and quotes
- Displays portfolio value, positions, orders, and risk status in a dark-themed dashboard
- Generates deterministic swing-trading signals using a Momentum + Relative Strength screener
- Enforces hard risk controls before any order can be placed
- Supports **mock**, **paper**, and **moomoo** broker modes
- Logs every action for full auditability
- Runs entirely locally with SQLite (PostgreSQL-ready schema)

## What It Does NOT Do

- ❌ No auto-trading without explicit user approval
- ❌ No market orders (limit orders only)
- ❌ No options trading
- ❌ No crypto
- ❌ No penny stocks
- ❌ No HFT
- ❌ No LLM-based order placement
- ❌ No cloud dependency (optional Docker only)

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- npm

### 1. Backend

```bash
cd backend
pip install -e ".[dev]"
mkdir -p data
python -m uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload
```

The backend starts at `http://localhost:8020`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend starts at `http://localhost:3000`.

The frontend proxies API calls to `localhost:8020` via Next.js rewrites (configured in `next.config.js`).

---

## Docker

```bash
docker compose up --build
```

This starts:
- Backend on `http://localhost:8020`
- Frontend on `http://localhost:3000`

---

## Broker Modes

Set `BROKER_MODE` in `.env` or as an environment variable.

| Mode | Description |
|---|---|---|
| `mock` | **(Default)** Fully local mock data. **Test-only.** No external dependencies. All data is synthetic and should not be used for production analysis. |
| `paper` | Paper trading. Uses mock market data but records orders, fills, and trade log for simulated P&L tracking. **Test-only.** |
| `moomoo` | **MOOMOO_READ_ONLY** — Real moomoo OpenD connection. **Requires OpenD running locally.** Real account data, real market data for signals. Read-only display only — all write operations are blocked. |

### Moomoo Read-Only Mode (Phase 2B)

The moomoo adapter connects to OpenD and reads real account data without placing orders. Signals are generated from real moomoo market data (quotes and historical daily klines), not mock/synthetic data.

1. Install moomoo SDK: `pip install -e ".[moomoo]"` (installs `moomoo-api`)
2. Download and run [Futu OpenD](https://www.futunn.com/opend/) on `127.0.0.1:11111`
3. Unlock your trade password in OpenD
4. Configure environment variables:

```bash
BROKER_MODE=moomoo
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
MOOMOO_TRD_ENV=SIMULATE   # or REAL for live account view
```

The dashboard shows distinct banners and badges:
- **Moomoo Simulate Read-Only** — reads simulated account data (no real money)
- **Moomoo Real Read-Only** — reads real account data (display only)

Signals show a **MOOMOO DATA** badge when generated from real market data.

#### Trading Universe

The Trading Universe is editable from the **Settings** page:
- Add or remove symbols
- Save changes — they persist in the database
- After saving, run the screener — the updated universe is used immediately
- Universe precedence: app_settings.trading_universe → env/default universe

#### Signal Generation

- In moomoo mode, signals are generated using real moomoo quotes and historical daily klines
- Data failure for a symbol results in a **DATA_ERROR** record, not a fabricated AVOID signal
- If fewer than 200 daily bars are available, the symbol is marked as DATA_ERROR
- Mock/local data is never used in moomoo runtime
- Signal metadata: `data_source="moomoo"`, `is_real_market_data=true`, `is_tradeable=false`

> **❗ Order placement and cancellation always raise `RuntimeError("Read-only mode")` in moomoo mode, regardless of `TRADING_ENABLED` setting.**

`MOOMOO_TRD_ENV=SIMULATE` maps to `TrdEnv.SIMULATE` (simulated trading environment).  
`MOOMOO_TRD_ENV=REAL` maps to `TrdEnv.REAL` (real trading environment).  
Both are read-only in this phase. Live trading (MOOMOO_LIVE) is not implemented.

---

## Risk Controls

Every order passes through the **Risk Engine** which checks:

| Rule | Configuration |
|---|---|
| Global kill switch | `POST /api/v1/risk/kill-switch` |
| Broker disconnected | Auto-detected |
| Stale quote | `MAX_QUOTE_AGE_SECONDS` (default: 10s) |
| Missing stop loss | Required for BUY orders |
| Order type not LIMIT | Only `LIMIT` allowed |
| Symbol not in universe | `UNIVERSE_SYMBOLS` |
| Position size exceeds max | `MAX_POSITION_PCT` of portfolio |
| Single trade risk exceeds max | `MAX_RISK_PER_TRADE_PCT` of portfolio |
| Daily loss exceeded | `DAILY_LOSS_LIMIT_PCT` |
| Max drawdown exceeded | `MAX_DRAWDOWN_SOFT_PCT` / `MAX_DRAWDOWN_HARD_PCT` |
| Duplicate open order | Same symbol + same direction |

---

## Tests

```bash
cd backend
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_risk_engine.py -v
```

---

## Order Flow

1. Signal generated by screener
2. User clicks **Preview** on the frontend
3. Backend evaluates the order against all risk rules
4. UI displays allowed/blocked decision
5. User clicks **Approve**
6. Backend checks risk again
7. If passed: submits order to broker (mock/paper/moomoo)
8. Everything is logged to the audit log

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/broker/health` | Broker connection health |
| GET | `/api/v1/config` | App configuration |
| GET | `/api/v1/portfolio/summary` | Portfolio summary |
| GET | `/api/v1/positions` | Open positions |
| GET | `/api/v1/orders` | All orders |
| POST | `/api/v1/orders/preview` | Preview order (risk check) |
| POST | `/api/v1/orders/approve` | Approve and submit order |
| POST | `/api/v1/orders/cancel` | Cancel order |
| GET | `/api/v1/signals` | Generated signals |
| POST | `/api/v1/signals/run` | Run screener |
| GET | `/api/v1/risk/status` | Risk status |
| POST | `/api/v1/risk/kill-switch` | Toggle kill switch |
| GET | `/api/v1/watchlist` | Get watchlist |
| POST | `/api/v1/watchlist` | Add to watchlist |
| DELETE | `/api/v1/watchlist/{symbol}` | Remove from watchlist |
| GET | `/api/v1/settings/trading-universe` | Get trading universe (DB-first) |
| PUT | `/api/v1/settings/trading-universe` | Save trading universe (persisted to DB) |
| WS | `/api/v1/ws` | WebSocket live events |

---

## Project Structure

```
moomoo-alpha-console/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes + WebSocket
│   │   ├── core/          # Config, logging, time utils
│   │   ├── db/            # SQLAlchemy models, session, migrations
│   │   ├── models/        # Database models (14 tables)
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── broker/    # Mock, Paper, Moomoo adapters
│   │   │   ├── risk/      # Risk engine (13 rules)
│   │   │   ├── research/  # Research provider interfaces
│   │   │   ├── execution/ # Order service
│   │   │   ├── market_data/
│   │   │   ├── portfolio/
│   │   │   └── audit/
│   │   ├── strategies/    # Momentum Relative Strength screener
│   │   ├── workers/       # APScheduler jobs
│   │   └── main.py        # FastAPI app factory
│   ├── tests/             # pytest tests (57+ tests)
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages (Dashboard, Signals, Positions, Orders, Risk, Settings, Backtests)
│   │   ├── components/    # Layout, shared UI components
│   │   └── lib/           # API client, WebSocket, Zustand store, types
│   ├── package.json
│   └── next.config.js
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Roadmap

| Phase | Status |
|---|---|
| Backend MVP (FastAPI, mock broker, risk engine, signals) | ✅ Done |
| Database (SQLAlchemy models, SQLite, Alembic) | ✅ Done |
| API routes (health, config, portfolio, positions, orders, signals, risk, watchlist) | ✅ Done |
| Frontend MVP (Dashboard, Signals, Positions, Orders, Risk, Settings) | ✅ Done |
| Tests (risk engine, signal scoring, broker, API) | ✅ Done |
| Docker Compose | ✅ Done |
| Moomoo OpenD read-only display (Phase 2A) | ✅ Done |
| Moomoo market data signals + editable Trading Universe (Phase 2B) | ✅ Done |
| WebSocket live event broadcasting | ⬜ TODO (skeleton ready) |
| Postgres support | ⬜ TODO |
| Redis caching | ⬜ TODO |
| Research adapters (Vibe-Trading, OpenBB, Backtrader) | ⬜ TODO (placeholders ready) |
| Strategy backtesting engine | ⬜ TODO |
| Live trading (MOOMOO_LIVE) | ⬜ TODO (future phase) |

---

## Safety Model

1. **Kill switch**: Global on/off for all trading
2. **Risk checks**: 13 deterministic rules evaluated before every order
3. **Dual approval**: Preview + Approve; risk checked both times
4. **Audit trail**: Every order, approval, rejection, and error logged to DB
5. **Broker isolation**: All broker access through adapter interface
6. **Moomoo fallback**: Adapter fails closed if SDK is missing or OpenD unavailable
7. **Limit-only**: No market orders permitted in MVP
