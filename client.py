"""
Low-level Binance Futures Testnet REST client.
Supports real API calls and mock mode.
"""

import hashlib
import hmac
import random
import time
import urllib.parse
from typing import Any, Dict

import requests

from .logging_config import get_logger


logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10


class BinanceAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


def _mock_order_response(
    symbol,
    side,
    order_type,
    quantity,
    price=None,
    stop_price=None,
    time_in_force="GTC",
):
    order_id = random.randint(4000000000, 4999999999)
    ts = int(time.time() * 1000)

    base_prices = {
        "BTCUSDT": 96500.0,
        "ETHUSDT": 3200.0,
        "BNBUSDT": 580.0,
    }

    market_price = base_prices.get(symbol, 100.0)

    if order_type == "MARKET":
        status = "FILLED"
        avg_price = str(round(market_price * random.uniform(0.9995, 1.0005), 2))
        executed_qty = str(quantity)
        order_price = "0"
    elif order_type == "LIMIT":
        status = "NEW"
        avg_price = "0"
        executed_qty = "0"
        order_price = str(price or "0")
    else:
        status = "NEW"
        avg_price = "0"
        executed_qty = "0"
        order_price = "0"

    return {
        "orderId": order_id,
        "symbol": symbol,
        "status": status,
        "clientOrderId": f"mockbot_{ts}",
        "price": order_price,
        "avgPrice": avg_price,
        "origQty": str(quantity),
        "executedQty": executed_qty,
        "cumQuote": str(round(float(executed_qty or 0) * float(avg_price or 0), 4)),
        "timeInForce": time_in_force,
        "type": order_type,
        "reduceOnly": False,
        "side": side,
        "positionSide": "BOTH",
        "stopPrice": str(stop_price) if stop_price else "0",
        "origType": order_type,
        "updateTime": ts,
    }


class BinanceClient:
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        mock: bool = False,
    ):
        self.mock = mock

        if not mock and (not api_key or not api_secret):
            raise ValueError("api_key and api_secret must not be empty.")

        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        if not mock:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "X-MBX-APIKEY": self.api_key,
                    "Content-Type": "application/x-www-form-urlencoded",
                }
            )

        logger.debug("BinanceClient initialised. mode=%s", "MOCK" if mock else "LIVE")

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = urllib.parse.urlencode(params)
        return hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _handle_response(self, response: requests.Response):
        logger.debug(
            "HTTP response: url=%s status=%s body=%s",
            response.request.url,
            response.status_code,
            response.text[:500],
        )

        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(
                code=data["code"],
                message=data.get("msg", "Unknown error"),
            )

        response.raise_for_status()
        return data

    def place_order(
        self,
        symbol,
        side,
        order_type,
        quantity,
        price=None,
        stop_price=None,
        time_in_force="GTC",
        reduce_only=False,
    ):
        logger.info(
            "Placing order: symbol=%s side=%s type=%s qty=%s price=%s",
            symbol,
            side,
            order_type,
            quantity,
            price or "N/A",
        )

        if self.mock:
            logger.debug("[MOCK] Simulating order. No real API call made.")
            time.sleep(0.3)
            result = _mock_order_response(
                symbol,
                side,
                order_type,
                quantity,
                price,
                stop_price,
                time_in_force,
            )
            logger.info(
                "[MOCK] Order simulated: orderId=%s status=%s",
                result["orderId"],
                result["status"],
            )
            return result

        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "timestamp": self._timestamp(),
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force

        if order_type == "STOP_MARKET":
            params["stopPrice"] = stop_price

        if reduce_only:
            params["reduceOnly"] = "true"

        params["signature"] = self._sign(params)

        logger.debug(
            "POST %s/fapi/v1/order params=%s",
            self.base_url,
            {k: v for k, v in params.items() if k != "signature"},
        )

        response = self._session.post(
            f"{self.base_url}/fapi/v1/order",
            data=params,
            timeout=self.timeout,
        )

        result = self._handle_response(response)

        logger.info(
            "Order placed successfully: orderId=%s status=%s",
            result.get("orderId"),
            result.get("status"),
        )

        return result

    def cancel_order(self, symbol, order_id):
        if self.mock:
            return {
                "orderId": order_id,
                "symbol": symbol,
                "status": "CANCELED",
            }

        params = {
            "symbol": symbol,
            "orderId": order_id,
            "timestamp": self._timestamp(),
        }
        params["signature"] = self._sign(params)

        response = self._session.delete(
            f"{self.base_url}/fapi/v1/order",
            params=params,
            timeout=self.timeout,
        )

        return self._handle_response(response)

