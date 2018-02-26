
from datetime import datetime, timedelta
import asyncio
import sys

import ccxt.async as ccxt
import tenacity
import aiohttp

import output_generator as og

sys.path.append("helpers/indicators/")

from rsi import calc_rsi


class Processor:
	def __init__(self, logger, config, mi):
		self._logger = logger

		self._rsi_timeframe = config["rsi_timeframe"]
		self._over_bought = config["over_bought"]
		self._rsi_period = config["rsi_period"]
		self._free_fall = config["free_fall"]
		self._over_sold = config["over_sold"]
		self._mooning = config["mooning"]

		self._exchange_market_prices = {}
		self._significant_markets = set()

		self._aretry = tenacity.AsyncRetrying(
			wait=tenacity.wait_exponential(),
			retry=(
				tenacity.retry_if_exception(ccxt.DDoSProtection) | 
				tenacity.retry_if_exception(ccxt.RequestTimeout))
			)

		self.mi = mi


	def _get_exchange(self, exchange: str) -> ccxt.Exchange:
		if exchange in ccxt.exchanges:
			return getattr(ccxt, exchange)()

		return None


	async def load_exchanges(self, exchanges: list) -> None:
		"""
		Asynchronously loads the markets from bittrex and binance markets.
		This loaded data is used to check percent change.

		Args:
			exchanges: exchanges to load and create

		Returns:
			None
		
		"""

		for exchange in exchanges:
			exchange = self._get_exchange(exchange)

			# ensure it hasn't been loaded yet
			if exchange and exchange.id not in self._exchange_market_prices:
				await exchange.load_markets()
				
				prices = {}
				for symbol in exchange.symbols:
					ticker = await self._aretry.call(exchange.fetch_ticker, symbol)
					prices[symbol] = ticker["last"]

					self._exchange_market_prices[exchange.id] = prices


	def percent_change(self, new_price: int, old_price: int) -> float:
		"""
		Calculates and returns change in value between new_price and old_price

		Args:
			new_price: new price to be compared to old price.
			old_price: old price to be compared to new price.

		Returns:
			Float of the percent change rounded to 4 sig figs. IE 60.49

		"""
		return round(((new_price - old_price) / old_price) * 100, 2)


	async def check_exchange(self, exchange: ccxt.Exchange) -> tuple:
		price_updates = {}
		rsi_updates = {}

		old_prices = self._exchange_market_prices[exchange.id]

		await self._aretry.call(exchange.load_markets)
		for symbol in exchange.symbols:

			ticker = await self._aretry.call(exchange.fetch_ticker, symbol)

			new_price = ticker["last"]
			old_price = old_prices[symbol]

			change = self.percent_change(new_price, old_price)

			if change >= self._mooning or change <= self._free_fall:
				price_updates[symbol] = change
				old_prices[symbol] = new_price

			# if exchange.hasFetchOHLCV:
			# 	since = datetime.now() - timedelta(days=500)

			# 	data = await self._aretry.call(
			# 		exchange.fetch_ohlcv, symbol, "1h", since.timestamp())

			# 	rsi = calc_rsi(data, self._rsi_period)

			# 	if rsi >= self._over_sold or rsi <= self._over_sold:
			# 		if symbol not in self._significant_markets:
			# 			rsi_updates[symbol] = rsi
			# 			self._significant_markets.add(symbol)

			# 	elif rsi in self._significant_markets:
			# 		self._significant_markets.remove(symbol)

		return (price_updates, rsi_updates)


	async def process_exchanges(self, exchanges: list) -> dict:
		embeds = {}
		for exchange in exchanges:
			exchange = self._get_exchange(exchange)

			if not exchange: continue

			outputs = []
			price_updates, rsi_updates = await self.check_exchange(exchange)

			if price_updates:
				outputs.append(og.create_price_update_embed(price_updates))

			if rsi_updates:
				outputs.append(og.create_rsi_update_embed(rsi_updates))

			embeds[exchange.id] = outputs

		return embeds	


	async def find_cmc_ticker(self, ticker) -> str:

		tickers = await self.mi.get_cmc_tickers()

		ticker = ticker.lower()

		for t in tickers:
			if t["symbol"].lower() == ticker or \
				t["id"].lower() == ticker or \
				t["name"] == ticker:

				return t["id"]

		for t in tickers:
			if t["name"].lower().startswith(ticker):
				return t["id"]

		for t in tickers:
			if t["name"].lower().find(ticker) > 0:
				return t["id"]

		return None
