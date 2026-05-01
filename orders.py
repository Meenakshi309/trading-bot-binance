"""
High-level order placement logic.
"""

from typing import Any, Dict, Optional

from .client import BinanceClient
from .validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)
from .logging_config import get_logger


logger = get_logger("orders")


class OrderResult:
    """Lightweight wrapper around a raw Binance order response."""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.order_id = raw.get("orderId", 0)
        self.client_order_id = raw.get("clientOrderId", "")
        self.symbol = raw.get("symbol", "")
        self.side = raw.get("side", "")
        self.order_type = raw.get("type", "")
        self.status = raw.get("status", "")
        self.price = raw.get("price", "0")
        self.avg_price = raw.get("avgPrice", "0")
        self.orig_qty = raw.get("origQty", "0")
        self.executed_qty = raw.get("executedQty", "0")
        self.time_in_force = raw.get("timeInForce", "")
        self.update_time = raw.get("updateTime", 0)

    def summary(self) -> str:
        lines = [
            "=" * 52,
            "ORDER RESPONSE DETAILS",
            "=" * 52,
            f"Order ID      : {self.order_id}",
            f"Client OID    : {self.client_order_id}",
            f"Symbol        : {self.symbol}",
            f"Side          : {self.side}",
            f"Type          : {self.order_type}",
            f"Status        : {self.status}",
            f"Orig Qty      : {self.orig_qty}",
            f"Executed Qty  : {self.executed_qty}",
            f"Avg Price     : {self.avg_price}",
            f"Limit Price   : {self.price}",
            f"Time-in-Force : {self.time_in_force}",
            "=" * 52,
        ]
        return "\n".join(lines)


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> OrderResult:
    sym = validate_symbol(symbol)
    sid = validate_side(side)
    ot = validate_order_type(order_type)
    qty = validate_quantity(quantity)
    prc = validate_price(price, ot)
    stp = validate_stop_price(stop_price, ot)

    logger.info(
        "Order request: symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
        sym,
        sid,
        ot,
        qty,
        prc or "N/A",
        stp or "N/A",
    )

    raw = client.place_order(
        symbol=sym,
        side=sid,
        order_type=ot,
        quantity=str(qty),
        price=str(prc) if prc else None,
        stop_price=str(stp) if stp else None,
        time_in_force=time_in_force,
        reduce_only=reduce_only,
    )

    result = OrderResult(raw)

    logger.info(
        "Order confirmed: orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )

    return result

