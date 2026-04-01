import apiClient from './client';
import type { CandlestickData, MarketTicker } from '../types';

export const marketApi = {
  getCandles: (exchange: string, symbol: string, timeframe: string, limit = 500) =>
    apiClient
      .get<CandlestickData[]>('/market-data/candles', { params: { exchange, symbol, timeframe, limit } })
      .then((r) => r.data),

  getTicker: (exchange: string, symbol: string) =>
    apiClient
      .get<MarketTicker>('/market-data/ticker', { params: { exchange, symbol } })
      .then((r) => r.data),

  getTickers: (exchange: string, symbols?: string[]) =>
    apiClient
      .get<MarketTicker[]>('/market-data/tickers', { params: { exchange, symbols: symbols?.join(',') } })
      .then((r) => r.data),

  getOrderBook: (exchange: string, symbol: string, limit = 20) =>
    apiClient
      .get('/market-data/orderbook', { params: { exchange, symbol, limit } })
      .then((r) => r.data),

  getExchanges: () =>
    apiClient.get<string[]>('/market-data/exchanges').then((r) => r.data),

  getSymbols: (exchange: string) =>
    apiClient.get<string[]>('/market-data/symbols', { params: { exchange } }).then((r) => r.data),
};
