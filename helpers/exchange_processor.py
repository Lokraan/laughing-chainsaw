
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
	def __init__(self, logger, config, db):
		self._logger = logger

		self._rsi_timeframe = config["rsi_timeframe"]
		self._interval = config["update_interval"]
		self._over_bought = config["over_bought"]
		self._rsi_period = config["rsi_period"]
		self._free_fall = config["free_fall"]
		self._over_sold = config["over_sold"]
		self._mooning = config["mooning"]

		self._db = db

		self._exchange_market_prices = {}
		self._significant_markets = set()

		self._aretry = tenacity.AsyncRetrying(
			wait=tenacity.wait_exponential(),
			retry=(
				tenacity.retry_if_exception(ccxt.DDoSProtection) | 
				tenacity.retry_if_exception(ccxt.RequestTimeout) |
				tenacity.retry_if_exception(aiohttp.errors.ServerDisconnectedError)
				)
			)


	def _get_exchange(self, exchange: str) -> ccxt.Exchange:
		if exchange in ccxt.exchanges:
			return getattr(ccxt, exchange)()

		return None


	async def _fetch_all_tickers(self, exchange: ccxt.Exchange) -> list:
		await self._aretry.call(exchange.load_markets)

		# gathers tickers in parallel 
		tickers = await asyncio.gather(*[
			self._aretry.call(exchange.fetch_ticker, symbol)
			for symbol in exchange.symbols
			])

		return tickers


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
				prices = {}
				tickers = await self._fetch_all_tickers(exchange)

				# puts the prices for each exchange in data
				for ticker in tickers:
					symbol = ticker["symbol"]
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


	async def check_exchange_price_updates(self, exchange: ccxt.Exchange) -> tuple:
		price_updates = {}

		old_prices = self._exchange_market_prices[exchange.id]

		tickers = await self._fetch_all_tickers(exchange)

		for ticker in tickers:
			symbol = ticker["symbol"]
			new_price = ticker["last"]
			old_price = old_prices[symbol]

			change = self.percent_change(new_price, old_price)

			if change >= self._mooning or change <= self._free_fall:
				price_updates[symbol] = change
				old_prices[symbol] = new_price

		return price_updates


	async def _acalc_rsi(self, exchange, symbol, since) -> int:
		data = await self._aretry.call(
			exchange.fetch_ohlcv, symbol, self._rsi_timeframe, since.timestamp()
			)

		return {symbol: calc_rsi(data, self._rsi_period)}


	async def check_exchange_rsi_updates(self, exchange: ccxt.Exchange) -> tuple:
		if not exchange.has['fetchOHLCV']: return {}

		old_prices = self._exchange_market_prices[exchange.id]
		rsi_updates = {}

		await self._aretry.call(exchange.load_markets)

		since = datetime.now() - timedelta(days=500)

		rsi_data = await asyncio.gather(*[
			self._acalc_rsi(exchange, symbol, since)
			for symbol in exchange.symbols
			])

		for symbol, rsi in rsi_data.items():
			if rsi >= self._over_sold or rsi <= self._over_sold:
				if symbol not in self._significant_markets:
					rsi_updates[symbol] = rsi
					self._significant_markets.add(symbol)

			elif rsi in self._significant_markets:
				self._significant_markets.remove(symbol)

		return rsi_updates


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


	async def yield_exchange_price_updates(self) -> None:
		servers = self._db.servers_wanting_signals()

		processed_exchanges = {}

		self._logger.debug("Yielding exchange rsi updates for servers {0}".format(servers))

		for server in servers:

			server_id = server[0]
			server_name = server[1]

			channel = server[2]
			exchanges = server[3].split(" ")

			outputs = []

			self._logger.info("Checking exchanges {0} price updates for server {1} ({2})".format(
				exchanges, server_id, server_name))

			for exchange in exchanges:
				# if exchange has already been procesed, use processed data
				if exchange in processed_exchanges:
					outputs.append(processed_exchanges[exchange])

				# else generate it and store it as processed
				elif self._get_exchange(exchange):
					ccxt_exchange = self._get_exchange(exchange)
					if ccxt_exchange:

						updates = await self.check_exchange_price_updates(
							ccxt_exchange)

						self._logger.debug("Price Updates: {0}".format(updates))
						if updates:
							embeds = og.create_price_update_embed(updates)

							processed_exchanges[exchange] = embeds
							outputs.append(embeds)
						
			self._logger.debug(outputs)

			# prob can re write this and keep it inside exchange filtering loop
			for embed in outputs:
				yield [channel, embeds]


	async def yield_exchange_rsi_updates(self) -> None:
		servers = self._db.servers_wanting_signals()

		processed_exchanges = {}

		self._logger.debug("Yielding exchange rsi updates for servers {0}".format(servers))

		for server in servers:

			server_id = server[0]
			server_name = server[1]

			channel = server[2]
			exchanges = server[3].split(" ")

			outputs = []

			self._logger.info("Checking exchanges {0} rsi updates for server {1} ({2})".format(
				exchanges, server_id, server_name))

			for exchange in exchanges:
				# if exchange has already been procesed, use processed data
				if exchange in processed_exchanges:
					outputs.append(processed_exchanges[exchange])

				# else generate it and store it as processed
				elif self._get_exchange(exchange):
					ccxt_exchange = self._get_exchange(exchange)
					if ccxt_exchange:

						updates = await self.check_exchange_rsi_updates(ccxt_exchange)

						self._logger.debug("RSI Updates: {0}".format(updates))

						if updates:	
							embed = og.create_rsi_update_embed(updates)

							processed_exchanges[exchange] = embed
							outputs.append(embeds)
						
			self._logger.debug(outputs)

			# prob can re write this and keep it inside exchange filtering loop
			for embed in outputs:
				yield [channel, embeds]



	async def _fetch_data(self, url: str) -> dict:
		"""
		gets data from exchange

		Args:
			url: The url of the server to get data from.
			depth: The current try at getting data

		Returns:
			A json dict from the server specified by url if sucessful, else empty dict.

		"""

		async with aiohttp.ClientSession() as sess:
			async with sess.get(url) as resp:
				return await resp.json()
				

	async def cmc_market_query(self, market: str) -> list:
		"""
		Gets current market information.

		Args:
			market: The market price to ge received

		Returns:
			Current market information

		"""

		url = "https://api.coinmarketcap.com/v1/ticker/{}/".format(market)

		self._logger.debug("Getting cmc market tickers")
		return await self._aretry.call(self._fetch_data, url)


	async def get_crypto_mcap(self) -> dict:
		url = "https://api.coinmarketcap.com/v1/global/"


		self._logger.debug("Getting crypto marketcap ticker")
		return await self._aretry.call(self._fetch_data, url)


	async def get_cmc_tickers(self) -> list:
		url = "https://api.coinmarketcap.com/v1/ticker/?limit=0"

		self._logger.debug("Getting cmc tickers")

		return await self._aretry.call(self._fetch_data, url)


	async def find_cmc_ticker(self, ticker) -> str:

		tickers = await self.get_cmc_tickers()

		ticker = ticker.lower()

		self._logger.debug("Finding cmc ticker for {0}".format(ticker))

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
