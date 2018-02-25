
import datetime
import asyncio
import sys

import ccxt.async as ccxt
import aiohttp

import output_generator as og

sys.path.append("helpers/indicators/")

from rsi import calc_rsi


class Processor:
	def __init__(self, logger, config, mi):
		self._logger = logger

		self._rsi_tick_interval = config["rsi_tick_interval"]
		self._rsi_time_frame = config["rsi_time_frame"]
		self._over_bought = config["over_bought"]
		self._free_fall = config["free_fall"]
		self._over_sold = config["over_sold"]
		self._mooning = config["mooning"]

		self._exchange_market_prices = {}
		self._significant_markets = set()

		self.mi = mi


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
			exchange = getattr(ccxt, exchange)()

			if exchange and exchange not in self._exchange_market_prices:
				await exchange.load_markets()
				
				self._exchange_market_prices[exchange.id] = {}
				storage = self._exchange_market_prices[exchange.id]

				for symbol in exchange.symbols:
					ticker = await exchange.fetch_ticker(symbol)
					storage[symbol] = ticker["last"]


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

		storage = self._exchange_market_prices[exchange.id]
		for symbol in exchange.symbols:

			new_price = exchange.fetch_ticker(symbol)["last_price"]
			old_price = storage[symbol]

			change = self.percent_change(new_price, old_price)

			if change >= self._mooning or change <= self._free_fall:
				price_updates[symbol] = change
				storage[symbol] = new_price

			since = datetime.now() - timedelta(days=500)
			data = exchange.fetch_ohlcv(symbol, since.timestamp()) 
			rsi = calc_rsi()

			if rsi >= self._over_sold or rsi <= self._over_sold:
				if symbol not in self._significant_markets:
					rsi_updates[symbol] = rsi
					self._significant_markets.add(symbol)

			elif rsi in self._significant_markets:
				self._significant_markets.remove(symbol)

		return (price_updates, rsi_updates)


	async def process_exchanges(self, exchanges: list) -> dict:
		embeds = {}
		for exchange in exchanges:
			exchange = getattr(ccxt, exchange)

			if not exchange: continue

			outputs = []
			price_updates, rsi_updates = await self.check_exchange(exchange)

			if price_updates:
				outputs.append(og.create_price_update_embed(price_updates))

			if rsi_updates:
				outputs.append(og.create_rsi_update_embed(rsi_updates))

			embeds[exchange.id] = [
				og.create_price_update_embed(price_updates),
				og.create_rsi_update_embed(rsi_updates)
				]

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