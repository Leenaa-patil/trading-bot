#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet Trading Bot.

Usage examples:
  # Market BUY
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

  # Limit SELL
  python cli.py --symbol ETHUSDT --side SELL --type LIMIT --qty 0.1 --price 3500

  # Stop-Market BUY (bonus)
  python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --qty 0.001 --stop-price 65000

  # Use env vars for credentials instead of flags:
  export BINANCE_API_KEY=your_key
  export BINANCE_API_SECRET=your_secret
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import OrderManager
from bot.validators import validate_order_inputs

# ──────────────────────────────────────────────
# ANSI colour helpers (gracefully degraded)
# ──────────────────────────────────────────────
_NO_COLOUR = not sys.stdout.isatty() or os.name == "nt"


def _c(text: str, code: str) -> str:
    if _NO_COLOUR:
        return text
    return f"\033[{code}m{text}\033[0m"


GREEN = lambda t: _c(t, "32")
RED = lambda t: _c(t, "31")
CYAN = lambda t: _c(t, "36")
BOLD = lambda t: _c(t, "1")
YELLOW = lambda t: _c(t, "33")


# ──────────────────────────────────────────────
# Argument parsing
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=textwrap.dedent(
            """\
            Binance Futures Testnet – Trading Bot CLI
            ─────────────────────────────────────────
            Place MARKET, LIMIT, or STOP_MARKET orders on the testnet.
            API credentials can be passed as flags or via environment variables
            BINANCE_API_KEY and BINANCE_API_SECRET.
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Credentials (optional flags; fall back to env vars) ──
    creds = parser.add_argument_group("credentials")
    creds.add_argument(
        "--api-key",
        default=os.environ.get("BINANCE_API_KEY", ""),
        metavar="KEY",
        help="Binance Futures Testnet API key (or set BINANCE_API_KEY env var).",
    )
    creds.add_argument(
        "--api-secret",
        default=os.environ.get("BINANCE_API_SECRET", ""),
        metavar="SECRET",
        help="Binance Futures Testnet API secret (or set BINANCE_API_SECRET env var).",
    )

    # ── Order parameters ──
    order = parser.add_argument_group("order parameters")
    order.add_argument(
        "--symbol", "-s", required=True, metavar="SYMBOL",
        help="Trading pair symbol, e.g. BTCUSDT.",
    )
    order.add_argument(
        "--side", required=True, choices=["BUY", "SELL"],
        help="Order side: BUY or SELL.",
    )
    order.add_argument(
        "--type", "-t", required=True,
        dest="order_type",
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        help="Order type: MARKET, LIMIT, or STOP_MARKET.",
    )
    order.add_argument(
        "--qty", "-q", required=True, metavar="QUANTITY",
        help="Order quantity (e.g. 0.001 for BTC).",
    )
    order.add_argument(
        "--price", "-p", default=None, metavar="PRICE",
        help="Limit price (required for LIMIT orders).",
    )
    order.add_argument(
        "--stop-price", default=None, metavar="STOP_PRICE",
        help="Stop trigger price (required for STOP_MARKET orders).",
    )
    order.add_argument(
        "--tif",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time-in-force for LIMIT orders (default: GTC).",
    )

    # ── Misc ──
    misc = parser.add_argument_group("misc")
    misc.add_argument(
        "--log-dir", default="logs", metavar="DIR",
        help="Directory for log files (default: logs/).",
    )
    misc.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (default: INFO).",
    )
    misc.add_argument(
        "--dry-run", action="store_true",
        help="Validate inputs and print the order request without submitting.",
    )

    return parser


# ──────────────────────────────────────────────
# Output helpers
# ──────────────────────────────────────────────

def print_request_summary(params: dict) -> None:
    print()
    print(BOLD("─" * 50))
    print(BOLD(CYAN("  ORDER REQUEST SUMMARY")))
    print(BOLD("─" * 50))
    print(f"  Symbol     : {params['symbol']}")
    print(f"  Side       : {params['side']}")
    print(f"  Type       : {params['order_type']}")
    print(f"  Quantity   : {params['quantity']}")
    if params.get("price"):
        print(f"  Price      : {params['price']}")
    if params.get("stop_price"):
        print(f"  Stop Price : {params['stop_price']}")
    print(BOLD("─" * 50))
    print()


def print_order_result(result) -> None:
    print(BOLD("─" * 50))
    print(BOLD(GREEN("  ORDER RESPONSE DETAILS")))
    print(BOLD("─" * 50))
    for line in result.summary_lines():
        print(line)
    print(BOLD("─" * 50))
    print()


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Initialise logging first so every subsequent step is captured
    logger = setup_logging(log_dir=args.log_dir, log_level=args.log_level)

    # ── 1. Validate inputs ──────────────────────────────────────────
    logger.debug(
        "Raw CLI args: symbol=%s side=%s type=%s qty=%s price=%s stop_price=%s",
        args.symbol, args.side, args.order_type, args.qty, args.price, args.stop_price,
    )

    try:
        params = validate_order_inputs(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.qty,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(RED(f"\n  ✗  Validation error: {exc}\n"), file=sys.stderr)
        logger.error("Input validation failed: %s", exc)
        return 1

    print_request_summary(params)

    # ── 2. Dry-run short-circuit ─────────────────────────────────────
    if args.dry_run:
        print(YELLOW("  ⚡  Dry-run mode – order NOT submitted.\n"))
        logger.info("Dry-run: order not submitted.")
        return 0

    # ── 3. Credentials check ─────────────────────────────────────────
    if not args.api_key or not args.api_secret:
        print(
            RED(
                "\n  ✗  API credentials missing.\n"
                "     Provide --api-key / --api-secret or set env vars\n"
                "     BINANCE_API_KEY and BINANCE_API_SECRET.\n"
            ),
            file=sys.stderr,
        )
        logger.error("Missing API credentials.")
        return 1

    # ── 4. Build client + order manager ──────────────────────────────
    client = BinanceClient(api_key=args.api_key, api_secret=args.api_secret)
    manager = OrderManager(client)

    # ── 5. Place order ────────────────────────────────────────────────
    try:
        if params["order_type"] == "MARKET":
            result = manager.place_market_order(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
            )
        elif params["order_type"] == "LIMIT":
            result = manager.place_limit_order(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                price=params["price"],
                time_in_force=args.tif,
            )
        elif params["order_type"] == "STOP_MARKET":
            result = manager.place_stop_market_order(
                symbol=params["symbol"],
                side=params["side"],
                quantity=params["quantity"],
                stop_price=params["stop_price"],
            )
        else:
            # Should never reach here thanks to argparse choices
            raise ValueError(f"Unsupported order type: {params['order_type']}")

    except BinanceAPIError as exc:
        print(RED(f"\n  ✗  Binance API error [{exc.code}]: {exc.message}\n"), file=sys.stderr)
        logger.error("Order failed with Binance API error: %s", exc)
        return 1
    except Exception as exc:
        print(RED(f"\n  ✗  Unexpected error: {exc}\n"), file=sys.stderr)
        logger.exception("Unexpected error placing order")
        return 1

    # ── 6. Print result ───────────────────────────────────────────────
    print_order_result(result)
    print(GREEN(f"  ✓  Order placed successfully! Order ID: {result.order_id}\n"))
    logger.info("CLI completed successfully. orderId=%s", result.order_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
