"""
validators.py – Input validation helpers for trading bot CLI.
All validators raise ValueError with a human-readable message on failure.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}   # extended for bonus
MIN_QUANTITY = Decimal("0.000001")


def validate_symbol(symbol: str) -> str:
    """Return upper-cased symbol or raise ValueError."""
    s = symbol.strip().upper()
    if not s.isalnum():
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must be alphanumeric (e.g. BTCUSDT)."
        )
    if len(s) < 3:
        raise ValueError(f"Symbol '{symbol}' is too short.")
    return s


def validate_side(side: str) -> str:
    """Return upper-cased side or raise ValueError."""
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return s


def validate_order_type(order_type: str) -> str:
    """Return upper-cased order type or raise ValueError."""
    ot = order_type.strip().upper()
    if ot not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return ot


def validate_quantity(quantity: str) -> Decimal:
    """Parse and validate quantity; return Decimal or raise ValueError."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0 (got {quantity}).")
    if qty < MIN_QUANTITY:
        raise ValueError(
            f"Quantity {quantity} is below minimum allowed ({MIN_QUANTITY})."
        )
    return qty


def validate_price(price: Optional[str], order_type: str) -> Optional[Decimal]:
    """
    Validate price field.
      - Required (and must be > 0) for LIMIT and STOP_MARKET orders.
      - Ignored for MARKET orders.
    Returns Decimal or None.
    """
    ot = order_type.strip().upper()

    if ot == "MARKET":
        if price is not None:
            # Accept but ignore – just warn caller via return None
            pass
        return None

    # Only LIMIT requires a limit price; STOP_MARKET uses stop_price instead
    if ot == "STOP_MARKET":
        return None
    if price is None or str(price).strip() == "":
        raise ValueError(f"Price is required for {ot} orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than 0 (got {price}).")
    return p


def validate_stop_price(stop_price: Optional[str], order_type: str) -> Optional[Decimal]:
    """Validate stop price for STOP_MARKET orders."""
    if order_type.upper() != "STOP_MARKET":
        return None
    if stop_price is None or str(stop_price).strip() == "":
        raise ValueError("--stop-price is required for STOP_MARKET orders.")
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Invalid stop price '{stop_price}'.")
    if sp <= 0:
        raise ValueError(f"Stop price must be > 0 (got {stop_price}).")
    return sp
