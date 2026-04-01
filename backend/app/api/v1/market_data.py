import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
import ccxt.async_support as ccxt_async

from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.market_data import CandlestickData, MarketTicker, OrderBook
from app.core.exceptions import ExchangeException, ValidationException

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_EXCHANGES = ["binance", "coinbase", "kraken", "bybit", "okx", "huobi", "kucoin"]


def _get_exchange(exchange_id: str):
    exchange_class = getattr(ccxt_async, exchange_id, None)
    if exchange_class is None:
        raise ValidationException(f"Unsupported exchange: {exchange_id}")
    return exchange_class({"enableRateLimit": True})


@router.get("/candles", response_model=List[CandlestickData])
async def get_candles(
    exchange: str = Query(...),
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
):
    exc = _get_exchange(exchange)
    try:
        ohlcv = await exc.fetch_ohlcv(symbol, timeframe, limit=limit)
        candles = []
        for bar in ohlcv:
            ts = datetime.fromtimestamp(bar[0] / 1000, tz=timezone.utc)
            candles.append(CandlestickData(
                timestamp=ts,
                open=Decimal(str(bar[1])),
                high=Decimal(str(bar[2])),
                low=Decimal(str(bar[3])),
                close=Decimal(str(bar[4])),
                volume=Decimal(str(bar[5])),
            ))
        return candles
    except ccxt_async.BadSymbol:
        raise ValidationException(f"Invalid symbol: {symbol}")
    except Exception as e:
        logger.error(f"Failed to fetch candles: {e}")
        raise ExchangeException(f"Failed to fetch candles: {str(e)}")
    finally:
        await exc.close()


@router.get("/ticker", response_model=MarketTicker)
async def get_ticker(
    exchange: str = Query(...),
    symbol: str = Query(...),
    current_user: User = Depends(get_current_active_user),
):
    exc = _get_exchange(exchange)
    try:
        ticker = await exc.fetch_ticker(symbol)
        return MarketTicker(
            exchange=exchange,
            symbol=symbol,
            last=Decimal(str(ticker.get("last") or 0)),
            bid=Decimal(str(ticker.get("bid") or 0)),
            ask=Decimal(str(ticker.get("ask") or 0)),
            high=Decimal(str(ticker.get("high") or 0)),
            low=Decimal(str(ticker.get("low") or 0)),
            volume=Decimal(str(ticker.get("baseVolume") or 0)),
            change=Decimal(str(ticker.get("change") or 0)),
            change_pct=float(ticker.get("percentage") or 0),
            timestamp=datetime.fromtimestamp(
                (ticker.get("timestamp") or 0) / 1000, tz=timezone.utc
            ),
        )
    except Exception as e:
        logger.error(f"Failed to fetch ticker: {e}")
        raise ExchangeException(f"Failed to fetch ticker: {str(e)}")
    finally:
        await exc.close()


@router.get("/orderbook", response_model=OrderBook)
async def get_orderbook(
    exchange: str = Query(...),
    symbol: str = Query(...),
    depth: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    exc = _get_exchange(exchange)
    try:
        book = await exc.fetch_order_book(symbol, depth)
        bids = [[Decimal(str(p)), Decimal(str(q))] for p, q in book.get("bids", [])]
        asks = [[Decimal(str(p)), Decimal(str(q))] for p, q in book.get("asks", [])]
        return OrderBook(
            exchange=exchange,
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Failed to fetch order book: {e}")
        raise ExchangeException(f"Failed to fetch order book: {str(e)}")
    finally:
        await exc.close()


@router.get("/exchanges")
async def list_exchanges(current_user: User = Depends(get_current_active_user)):
    return {"exchanges": SUPPORTED_EXCHANGES}


@router.get("/symbols")
async def list_symbols(
    exchange: str = Query(...),
    current_user: User = Depends(get_current_active_user),
):
    exc = _get_exchange(exchange)
    try:
        markets = await exc.load_markets()
        symbols = list(markets.keys())[:200]  # Limit to 200 symbols
        return {"exchange": exchange, "symbols": sorted(symbols)}
    except Exception as e:
        logger.error(f"Failed to fetch symbols: {e}")
        raise ExchangeException(f"Failed to fetch symbols: {str(e)}")
    finally:
        await exc.close()
