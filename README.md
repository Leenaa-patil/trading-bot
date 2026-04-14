# Binance Futures Testnet – Trading Bot

A clean, well-structured Python CLI application for placing orders on the
**Binance Futures Testnet (USDT-M)**. Supports MARKET, LIMIT, and STOP_MARKET
orders with full input validation, structured logging, and robust error handling.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (signing, retries, error handling)
│   ├── orders.py          # Order placement logic + OrderResult dataclass
│   ├── validators.py      # Input validation (all cross-field rules)
│   └── logging_config.py  # Structured logging to file + console
├── cli.py                 # CLI entry point (argparse)
├── logs/
│   └── trading_bot_YYYYMMDD.log
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Python version

Requires **Python 3.9+**.

```bash
python --version
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Testnet credentials

1. Visit <https://testnet.binancefuture.com>
2. Log in (or register) and click **API Key** in the top menu.
3. Generate a key pair and copy both values.

### 5. Set credentials

**Option A – environment variables (recommended)**

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

**Option B – CLI flags** (see examples below)

---

## How to Run

### General syntax

```
python cli.py [credentials] --symbol SYMBOL --side BUY|SELL \
              --type MARKET|LIMIT|STOP_MARKET --qty QUANTITY \
              [--price PRICE] [--stop-price STOP_PRICE] [--tif GTC|IOC|FOK]
```

### Examples

#### MARKET BUY

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --qty 0.001
```

#### LIMIT SELL

```bash
python cli.py \
  --symbol ETHUSDT \
  --side SELL \
  --type LIMIT \
  --qty 0.1 \
  --price 3500
```

#### LIMIT BUY with IOC time-in-force

```bash
python cli.py \
  --symbol SOLUSDT \
  --side BUY \
  --type LIMIT \
  --qty 1 \
  --price 145 \
  --tif IOC
```

#### STOP_MARKET BUY (bonus order type)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type STOP_MARKET \
  --qty 0.001 \
  --stop-price 66000
```

#### Dry-run (validate inputs, do not submit)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --qty 0.001 \
  --dry-run
```

#### Pass credentials via flags (alternative to env vars)

```bash
python cli.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --qty 0.001
```

#### Verbose debug logging

```bash
python cli.py --log-level DEBUG --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

---

## Sample Output

```
──────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
──────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
──────────────────────────────────────────────────

──────────────────────────────────────────────────
  ORDER RESPONSE DETAILS
──────────────────────────────────────────────────
  Order ID       : 4751823649
  Client OID     : x-testbot-mkt-001
  Symbol         : BTCUSDT
  Side           : BUY
  Type           : MARKET
  Status         : FILLED
  Orig Qty       : 0.001
  Executed Qty   : 0.001
  Avg Price      : 65312.40
  Price          : 0
  Time In Force  : GTC
──────────────────────────────────────────────────

  ✓  Order placed successfully! Order ID: 4751823649
```

---

## Logging

Logs are written to `logs/trading_bot_YYYYMMDD.log` (one file per day).

- **File**: always at DEBUG level – captures every request, response body preview, and error.
- **Console**: at the level specified by `--log-level` (default INFO).
- API signatures are redacted in all log output.

Example log file is included at `logs/trading_bot_20250714.log`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing required fields (e.g. price for LIMIT) | Validation error printed, exit code 1 |
| Invalid symbol / quantity / side | Validation error printed, exit code 1 |
| Missing API credentials | Clear error message, exit code 1 |
| Binance API error (e.g. -1121 invalid symbol) | Error code + message printed and logged |
| Network failure | Retried 3× with backoff; error logged on final failure |
| Unexpected exception | Full traceback logged to file; friendly message to stderr |

---

## Assumptions

1. **Testnet only** – the base URL is hardcoded to `https://testnet.binancefuture.com`.  
   Change `TESTNET_BASE_URL` in `bot/client.py` to point at production (at your own risk).
2. Quantity precision is passed as-is; for production use you should query
   `/fapi/v1/exchangeInfo` to enforce symbol-specific lot-size filters.
3. STOP_MARKET orders use `workingType=CONTRACT_PRICE` (Binance default).
4. No position-mode handling – assumes **One-way mode** on the testnet account.
   If your account is in Hedge mode, add `positionSide=BOTH` to order params.

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP client for REST API calls |
| `urllib3` | Retry / backoff adapter (bundled with requests) |

All standard library – no heavy third-party trading SDKs required.
