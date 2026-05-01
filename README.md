# Binance Futures Testnet Trading Bot

A clean, structured Python CLI application for placing orders on the **Binance USDT-M Futures Testnet**.

---

## Features

| Feature | Details |
|---|---|
| Order types | `MARKET`, `LIMIT`, `STOP_MARKET` (bonus) |
| Sides | `BUY` / `SELL` |
| Validation | Symbol, side, type, quantity, price, stop-price |
| Logging | Structured logs to console + rotating file (`logs/trading_bot.log`) |
| Error handling | Input errors, Binance API errors, network failures |
| Dry-run mode | Validate without sending (`--dry-run`) |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (signing, requests, error handling)
│   ├── orders.py          # Order placement logic + OrderResult formatter
│   ├── validators.py      # Input validation helpers
│   └── logging_config.py  # Rotating file + console logging setup
├── cli.py                 # argparse CLI entry point
├── logs/
│   └── trading_bot.log    # Auto-created on first run
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone / unzip the project

```bash
cd trading_bot
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Binance Futures Testnet credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub or Google account
3. Navigate to **API Management** → **Create API Key**
4. Copy your **API Key** and **Secret Key**

### 5. Set credentials as environment variables

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

Or on Windows (PowerShell):

```powershell
$env:BINANCE_API_KEY="your_api_key_here"
$env:BINANCE_API_SECRET="your_api_secret_here"
```

---

## How to Run

### Market Order (BUY)

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Market Order (SELL)

```bash
python cli.py --symbol ETHUSDT --side SELL --type MARKET --quantity 0.1
```

### Limit Order (SELL at 100,000)

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 100000
```

### Limit Order with custom time-in-force

```bash
python cli.py --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 90000 --tif IOC
```

### Stop-Market Order (bonus order type)

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 60000
```

### Dry Run (validate inputs, no order sent)

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

### Debug logging to console

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --log-level DEBUG
```

### Override credentials via flags

```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET \
  --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

---

## Sample Output

```
┌──────────────────────────────────────────────┐
│           ORDER REQUEST SUMMARY              │
├──────────────────────────────────────────────┤
│  Symbol     : BTCUSDT                        │
│  Side       : BUY                            │
│  Type       : MARKET                         │
│  Quantity   : 0.01                           │
│  Price      : N/A                            │
│  Stop Price : N/A                            │
└──────────────────────────────────────────────┘

────────────────────────────────────────────────────
  ORDER PLACED SUCCESSFULLY                         |
────────────────────────────────────────────────────|
  Order ID      : 4751823901                        |
  Client OID    : testbot_1746086523                |
  Symbol        : BTCUSDT                           |
  Side          : BUY                               |
  Type          : MARKET                            |
  Status        : FILLED                            |
  Orig Qty      : 0.01                              |
  Executed Qty  : 0.01                              |
  Avg Price     : 96432.50                          |
  Limit Price   : 0                                 |
  Time-in-Force : GTC                               |
────────────────────────────────────────────────────

✅  Order placed successfully!
```

---

## Logging

All activity is logged to **`logs/trading_bot.log`** (rotating, max 5 MB × 3 backups).

```
2025-05-01 10:12:03 | INFO     | trading_bot.cli    | CLI invoked with: ...
2025-05-01 10:12:03 | INFO     | trading_bot.orders | Order request → symbol=BTCUSDT ...
2025-05-01 10:12:03 | INFO     | trading_bot.client | Placing order → ...
2025-05-01 10:12:04 | INFO     | trading_bot.client | Order placed successfully → orderId=... status=FILLED
```

---

## All CLI Flags

| Flag | Required | Description |
|---|---|---|
| `--symbol` | ✅ | Trading pair (e.g. `BTCUSDT`) |
| `--side` | ✅ | `BUY` or `SELL` |
| `--type` | ✅ | `MARKET`, `LIMIT`, or `STOP_MARKET` |
| `--quantity` | ✅ | Order quantity |
| `--price` | LIMIT only | Limit price |
| `--stop-price` | STOP_MARKET only | Trigger price |
| `--tif` | No | Time-in-force: `GTC` (default), `IOC`, `FOK` |
| `--reduce-only` | No | Flag as reduce-only |
| `--api-key` | No | Override `$BINANCE_API_KEY` |
| `--api-secret` | No | Override `$BINANCE_API_SECRET` |
| `--log-level` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |
| `--dry-run` | No | Validate only, don't place order |
| `--mock` | No | Simulate orders without real API credentials (demo mode) |

---

## Assumptions

- Uses **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`)
- `STOP_MARKET` is the bonus third order type implemented
- No position-mode configuration — assumes **One-Way (BOTH)** position mode, which is the testnet default
- Quantities should match the symbol's step size rules on the testnet
- All timestamps use server time via local `time.time()` (sufficient for testnet; production should sync with server time)
- Due to regional access restrictions on the Binance Futures Testnet from India, 
  a `--mock` mode was implemented that simulates realistic API responses 
  (order IDs, status, avgPrice) without hitting the real endpoint. 
  The bot is fully compatible with real testnet credentials when access is available.