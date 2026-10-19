"""Minimal TON receiving helpers.

The demo only accepts incoming TON payments. It does not send TON and therefore
does not need wallet signing code.
"""

from __future__ import annotations

import math
import secrets
import string
import time
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger


_GLOBAL_TON_CACHE: Dict[str, Any] = {"value": 5.2, "timestamp": 0.0}


class TONService:
    """Read TON/USD price and search incoming payments by comment."""

    def __init__(self, wallet_address: str, toncenter_api_key: Optional[str] = None):
        self.wallet_address = wallet_address
        self.toncenter_api_key = toncenter_api_key

    def generate_payment_comment(self, order_id: int) -> str:
        """Create a unique payment comment for a single order."""
        suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        return f"STARS-{order_id}-{suffix}"

    async def get_ton_usd_rate(self) -> float:
        """Return TON/USD rate with a global in-memory cache and non-blocking fallback."""
        global _GLOBAL_TON_CACHE
        now = time.time()
        cached = _GLOBAL_TON_CACHE.get("value")
        if cached and (now - _GLOBAL_TON_CACHE.get("timestamp", 0.0)) < 600:
            return float(cached)

        sources = [
            ("Binance", "https://api.binance.com/api/v3/ticker/price", {"symbol": "TONUSDT"}),
            (
                "CoinGecko",
                "https://api.coingecko.com/api/v3/simple/price",
                {"ids": "the-open-network", "vs_currencies": "usd"},
            ),
        ]
        timeout = aiohttp.ClientTimeout(total=2.0)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for name, url, params in sources:
                    try:
                        async with session.get(url, params=params) as response:
                            if response.status != 200:
                                continue
                            data = await response.json()
                            if name == "Binance":
                                rate = float(data["price"])
                            else:
                                rate = float(data["the-open-network"]["usd"])
                            if 0.1 < rate < 100:
                                _GLOBAL_TON_CACHE = {"value": rate, "timestamp": now}
                                return rate
                    except Exception:
                        continue
        except Exception:
            pass

        # If fetch failed or timed out, use fallback safely
        fallback = float(_GLOBAL_TON_CACHE.get("value") or 5.2)
        _GLOBAL_TON_CACHE["timestamp"] = now
        return fallback

    async def usd_to_ton(self, usd_amount: float) -> float:
        """Convert USD invoice amount to TON and round up to 0.01 TON."""
        rate = await self.get_ton_usd_rate()
        return math.ceil((usd_amount / rate) * 100) / 100

    async def check_transaction(
        self,
        *,
        comment: str,
        min_amount: float,
        since_timestamp: int,
    ) -> Optional[Dict[str, Any]]:
        """Find an incoming transaction to the configured wallet by amount/comment."""
        params = {"address": self.wallet_address, "limit": 20}
        if self.toncenter_api_key:
            params["api_key"] = self.toncenter_api_key

        timeout = aiohttp.ClientTimeout(total=6)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "https://toncenter.com/api/v2/getTransactions",
                    params=params,
                    headers={"User-Agent": "Fragment Stars Demo Bot"},
                ) as response:
                    if response.status != 200:
                        logger.warning("TonCenter вернул HTTP {}", response.status)
                        return None
                    data = await response.json()
        except Exception as exc:
            logger.warning("TonCenter so'rovida tarmoq xatosi: {}", exc)
            return None

        if not data.get("ok"):
            logger.warning("TonCenter error: {}", data)
            return None

        for tx in data.get("result", []):
            if int(tx.get("utime", 0)) < since_timestamp:
                continue
            incoming = tx.get("in_msg") or {}
            amount = int(incoming.get("value") or 0) / 1_000_000_000
            message = incoming.get("message") or ""
            if amount >= min_amount and comment in message:
                return {
                    "hash": tx.get("hash", ""),
                    "amount": amount,
                    "timestamp": tx.get("utime"),
                    "from_address": incoming.get("source"),
                }
        return None

    async def find_incoming_payment(
        self,
        comment: str,
        min_amount: float,
        since_timestamp: int = 0,
    ) -> bool:
        """Helper for checking if payment exists by comment and amount."""
        tx = await self.check_transaction(
            comment=comment,
            min_amount=min_amount,
            since_timestamp=since_timestamp,
        )
        return tx is not None
