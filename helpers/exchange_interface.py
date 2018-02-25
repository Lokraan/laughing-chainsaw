
import logging
import asyncio
import aiohttp

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception
import ccxt.async as ccxt


# def ExchangeInterface:
# 	def __init__(self, logger):
# 		self._logger = logger
# 		self._retry = retry(
# 			wait=wait_exponential(),
# 			stop=stop_after_attempt(3),
# 			retry=(
# 				retry_if_exception(ccxt.DDosProtection) | 
# 				retry_if_exception(ccxt.RequestTimeout))
# 			)


# 	def _get_exchange(self, exchange: str) -> ccxt.Exchange:
# 		if exchange in ccxxt.exchanges:
# 			return getarr(ccxt, exchange)

# 		return None


# 	@self._retry
# 	async def _valid_symbol(self, symbol: str, exchange: ccxt.Exchange) -> bool:
# 		await exchange.load_markets()

# 		symbol = symbol.lower()
# 		for symb in exchange.symbols:
# 			if symb.lower() == symbol:
# 				return False

# 		return False


# 	@self._retry
# 	async def _valid_pair(self, base: str, quote: str, exchange: ccxt.Exchange) -> str:
# 		quote = quote.lower()
# 		base = base.lower()

# 		markets = await exchange.fetch_markets()

# 		for m in markets:
# 			if m["quote"].lower() == quote:
# 				if m["base"].lower() == base or m["baseId"].lower() == base:
# 					return m["symbol"]

# 		for m in markets:
# 			symbol = m["symbol"]
# 			if symbol.lower().startswith(base):
# 				return symbol

# 		for m in makrets:
# 			symbol = m["symbol"]
# 			if symbol.lower().find(base) > 0:
# 				return symbol

# 		return None


# 	@self._retry
# 	async def fetch_ohlcv(self, exchange: ccxt.Exchange, market: str, dist=200) -> list:
# 		markets = await exchange.load_markets()

# 		market = self._valid_symbol(market, exchange)

# 		if not market:
# 			return None

# 		since = (datetime.now() - timedelta(minutes=dist)).timestamp()

# 		return await exchange.fetch_ohlcv(market, "1d", since=since)


# 	@self._retry
# 	async def fetch_ticker(self, exchange: str, market: str) -> dict:
# 		exchange = getattr(ccxt, exchange)

# 		if not exchange:
# 			return

# 		return exchange.fetch_ticker(market)


def _fetch_exchange(exchange: str) -> ccxt.Exchange:
	if exchange in ccxt.exchanges:
		return getatr(ccxt, exchange)


def fetch_ohlcv(exchange: str = None, existing_exchange: ccxt.Exchange = None) -> dict:
	if existing_exchange:
		exchange = existing_exchange

	else:
		if exchange in ccxt.exchanges:
			exchange = getattr(ccxt, exchange)


		else:
			return None


class ExchangeInterface:
	def __init__(self, logger):
		self._logger = logger


	async def _query_exchange(self, session: aiohttp.ClientSession, url: str, depth: int = 0,
		max_depth: int = 3) -> dict:
		"""
		Tries to GET data from the exchange with url. If it fails it 
		recursively retries max_depth number of times.

		Args:
			url: The url of the server to get data from.
			depth: The current try at getting data
			max_depth: The maximum number of retries the bot will do.

		Returns:
			A json dict from the server specified by url if sucessful, else empty dict.

		"""

		if depth == max_depth: # max tries passed
			self._logger.warning("{0} Failed to GET data. Depth: {1}".format(url, depth))
			return {}

		try:
			async with session.get(url) as resp:
				return await resp.json()
				
		except aiohttp.errors.ServerDisconnectedError: # Disonnect, retry !
			self._logger.warning("{0} ServerDisconnectedError".format(url))
			return await self._query_exchange(session, url, depth=depth + 1)


	async def get_binance_markets(self, session: aiohttp.ClientSession) -> dict:
			"""
			Asynchronously GETS the market summaries from binance and returns
			it as a dictionary.

			Args:
				session: The aiohttp ClientSession to be used to GET data from exchange
				market summaries from binance.

			Returns:
				A dictionary of the market summaries from binance.

			"""
			url = "https://api.binance.com/api/v1/ticker/allPrices"
			return await self._query_exchange(session, url)
			

	async def get_bittrex_markets(self, session: aiohttp.ClientSession) -> dict:
		"""
		Asynchronously GETS the market summaries from bittrex and returns
		it as a dictionary.

		Args:
			session: The aiohttp ClientSession to be used to GET data from exchange
			market summaries from bittrex.

		Returns:
			A dictionary of the market summaries from bittrex.

		"""
		url = "https://bittrex.com/api/v1.1/public/getmarketsummaries"
		return await self._query_exchange(session, url)


	async def get_market_history(self, session:aiohttp.ClientSession, market: str,
		tick_interval: str) -> dict:
		"""
		Asynchronously receives market history from bittrex and returns it as a dict.

		Args:
			session: The aiohttp ClientSession to be used to GET data from exchange
			market history from bittrex.
			market: The market who's history it should receive.
			tick_interval: Tick interval used when querying bittrex.

		Returns:
			Dict of the market history with tick interval of tick interval.

		"""
		url = "https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName={0}&tickInterval={1}"\
			.format(market, tick_interval)

		return await self._query_exchange(session, url)


	async def cmc_market_query(self, market: str) -> list:
		"""
		Gets current market information.

		Args:
			market: The market price to ge received

		Returns:
			Current market information

		"""

		url = "https://api.coinmarketcap.com/v1/ticker/{}/".format(market)

		async with aiohttp.ClientSession() as sess:
			return await self._query_exchange(sess, url)


	async def get_crypto_mcap(self) -> dict:
		url = "https://api.coinmarketcap.com/v1/global/"

		async with aiohttp.ClientSession() as sess:
			return await self._query_exchange(sess, url)


	async def get_cmc_tickers(self) -> list:
		url = "https://api.coinmarketcap.com/v1/ticker/?limit=0"

		async with aiohttp.ClientSession() as sess:
			return await self._query_exchange(sess, url)
