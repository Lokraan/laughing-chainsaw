
import asyncio
import aiohttp


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
	return await query_exchange(session, url)


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
	url = "https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName={0}&tickInterval={1}".format(
		market, tick_interval)
	return await self._query_exchange(session, url)


async def _cmc_query(market: str) -> dict:
	"""
	Gets current market information.

	Args:
		market: The market price to ge received

	Returns:
		Current market information

	"""

	url = "https://api.coinmarketcap.com/v1/ticker/{}/".format(market)

	async with asyncio.ClientSession() as sess:
		return await self._query_exchange(sess, url)


async def get_cmc_price(market: str) -> int:

