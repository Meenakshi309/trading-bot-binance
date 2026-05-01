#!/usr/bin/env python3
"""
cli.py – Command-line interface for the Binance Futures trading bot.

Usage examples:
  # Market buy
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

  # Limit sell
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 70000

  # Stop-Market (bonus order type)
  python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 60000

  # Set credentials via env vars (recommended):
  export BINANCE_API_KEY=your_key
  export BINANCE_API_SECRET=your_secret
  python cli.py ...
"""

import argparse
import os
import sys
import textwrap

import requests

from bot.client import BinanceClient, BinanceAPIError
from bot.orders import place_order
from bot.logging_config import setup_logging, get_logger

# ── Bootstrap logging ────────────────────────────────────────────────────────
setup_logging()
logger = get_logger("cli")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_credentials() -> tuple[str, str]:
    """
    Resolve API credentials.
    Priority: CLI flags (--api-key / --api-secret) > environment variables.
    """
    api_key    = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    return api_key, api_secret


def _print_request_summary(args: argparse.Namespace) -> None:
    print()
    print("┌─────────────────────────────────────────────┐")
    print("│           ORDER REQUEST SUMMARY              │")
    print("├─────────────────────────────────────────────┤")
    print(f"│  Symbol     : {args.symbol:<30}│")
    print(f"│  Side       : {args.side:<30}│")
    print(f"│  Type       : {args.type:<30}│")
    print(f"│  Quantity   : {str(args.quantity):<30}│")
    price_str = str(args.price) if args.price else "N/A"
    print(f"│  Price      : {price_str:<30}│")
    stop_str  = str(args.stop_price) if args.stop_price else "N/A"
    print(f"│  Stop Price : {stop_str:<30}│")
    print("└─────────────────────────────────────────────┘")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI definition
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Binance Futures Testnet Trading Bot
            ────────────────────────────────────
            Place MARKET, LIMIT, or STOP_MARKET orders on the USDT-M testnet.

            Credentials are read from environment variables:
              BINANCE_API_KEY
              BINANCE_API_SECRET
            """
        ),
    )

    # ── Credentials (optional override) ──────────────────────────────────────
    creds = parser.add_argument_group("credentials (override env vars)")
    creds.add_argument(
        "--api-key",
        metavar="KEY",
        default=None,
        help="Binance API key (default: $BINANCE_API_KEY)",
    )
    creds.add_argument(
        "--api-secret",
        metavar="SECRET",
        default=None,
        help="Binance API secret (default: $BINANCE_API_SECRET)",
    )

    # ── Order parameters ──────────────────────────────────────────────────────
    order = parser.add_argument_group("order parameters")
    order.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT",
    )
    order.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        help="Order side: BUY or SELL",
    )
    order.add_argument(
        "--type",
        required=True,
        dest="type",
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        metavar="TYPE",
        help="Order type: MARKET | LIMIT | STOP_MARKET",
    )
    order.add_argument(
        "--quantity",
        required=True,
        metavar="QTY",
        help="Order quantity (e.g. 0.01)",
    )
    order.add_argument(
        "--price",
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT orders)",
    )
    order.add_argument(
        "--stop-price",
        default=None,
        metavar="STOP_PRICE",
        dest="stop_price",
        help="Stop trigger price (required for STOP_MARKET orders)",
    )
    order.add_argument(
        "--tif",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        metavar="TIF",
        help="Time-in-force for LIMIT orders: GTC | IOC | FOK  (default: GTC)",
    )
    order.add_argument(
        "--reduce-only",
        action="store_true",
        default=False,
        help="Flag order as reduce-only",
    )

    # ── Misc ──────────────────────────────────────────────────────────────────
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="Console log verbosity (default: INFO)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate inputs and print summary WITHOUT sending the order",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="Simulate orders without real API credentials (demo mode)",
    )

    return parser


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Re-configure log level if user changed it
    setup_logging(args.log_level)

    # ── Resolve credentials ───────────────────────────────────────────────────
    api_key    = args.api_key    or os.getenv("BINANCE_API_KEY",    "").strip()
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET", "").strip()

    if not args.mock and (not api_key or not api_secret):
        print(
            "\n[ERROR] API credentials not found.\n"
            "  Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables,\n"
            "  or pass --api-key / --api-secret flags.\n"
            "  Tip: use --mock to run in demo mode without credentials.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Print request summary ─────────────────────────────────────────────────
    logger.info("CLI invoked with: %s", vars(args))
    _print_request_summary(args)

    if args.dry_run:
        print("[DRY RUN] Input validation only — no order was sent.\n")
        # Still run validators so the user sees any errors
        try:
            from bot.validators import (
                validate_symbol, validate_side, validate_order_type,
                validate_quantity, validate_price, validate_stop_price,
            )
            validate_symbol(args.symbol)
            validate_side(args.side)
            validate_order_type(args.type)
            validate_quantity(args.quantity)
            validate_price(args.price, args.type)
            validate_stop_price(args.stop_price, args.type)
            print("[DRY RUN] All inputs are valid. ✓\n")
        except ValueError as exc:
            print(f"[DRY RUN] Validation error: {exc}\n", file=sys.stderr)
            sys.exit(1)
        return

    # ── Build client & place order ────────────────────────────────────────────
    if getattr(args, 'mock', False):
        print("[MOCK MODE] Simulating orders - no real API calls will be made.\n")
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret, mock=getattr(args, 'mock', False))
        result = place_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.tif,
            reduce_only=args.reduce_only,
        )
        print(result.summary())
        print("\n✅  Order placed successfully!\n")
        logger.info("Order flow completed successfully.")

    except ValueError as exc:
        print(f"\n❌  Input validation error: {exc}\n", file=sys.stderr)
        logger.error("Validation error: %s", exc)
        sys.exit(1)

    except BinanceAPIError as exc:
        print(f"\n❌  Binance API error [{exc.code}]: {exc.message}\n", file=sys.stderr)
        logger.error("Binance API error: code=%s message=%s", exc.code, exc.message)
        sys.exit(2)

    except requests.exceptions.ConnectionError:
        print("\n❌  Network error: Could not connect to Binance Testnet. Check your internet connection.\n", file=sys.stderr)
        logger.error("Connection error reaching %s", "https://testnet.binancefuture.com")
        sys.exit(3)

    except requests.exceptions.Timeout:
        print("\n❌  Network error: Request timed out.\n", file=sys.stderr)
        logger.error("Request timed out.")
        sys.exit(3)

    except requests.exceptions.RequestException as exc:
        print(f"\n❌  Network error: {exc}\n", file=sys.stderr)
        logger.error("Unexpected network error: %s", exc)
        sys.exit(3)

    except Exception as exc:
        print(f"\n❌  Unexpected error: {exc}\n", file=sys.stderr)
        logger.exception("Unexpected error: %s", exc)
        sys.exit(4)


if __name__ == "__main__":
    main()
