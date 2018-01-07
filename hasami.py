
import logging.config
import datetime
import logging
import asyncio
import random
import yaml
import json
import sys

import discord
import aiohttp


CONFIG_FILE = "config.json"
LOGGING_CONFIG = "log_conf.yaml"


class Bot:
	"""
	Bot used to analyze the bittrex and binance markets for significant price changes and
	RSI values.

	These significant markets are then printed out into a discord server.

	Attributes:
		client: Client used to communicate with the discord server
		config: configuration to edit the bot.
		logger: Logger to be used when logging.
		_mooning: High significant price change.
		_free_fall: Low significant price change.
		_over_bought: High significant RSI val.
		_over_sold: Low significant RSI val.
		_interval: Time to wait between each analysis of the markets.
		_rsi_tick_interval: Interval between each price update used to calculate the markets.
		_rsi_time_frame: Number of candles used to calculate RSI.

	"""
	def __init__(self, client: discord.Client, config: dict, logger: logging.Logger):
		self._client = client
		self._logger = logger
	
		# config stuff
		self._mooning = config["mooning"]
		self._free_fall = config["free_fall"]
		self._over_sold = config["over_sold"]
		self._over_bought = config["over_bought"]
		self._interval = config["update_interval"]
		self._update_channel = config["update_channel"]
		self._rsi_time_frame = config["rsi_time_frame"]
		self._rsi_tick_interval = config["rsi_tick_interval"]

		# Data for processing markets
		self._markets = {}
		self._significant_markets = set() # used for rsi to prevent spam printing
		self._updating = False


	def _percent_change(self, new_price: int, old_price: int) -> float:
		"""
		Calculates and returns change in value between new_price and old_price
	
		Args:
			new_price: new price to be compared to old price.
			old_price: old price to be compared to new price.

		Returns:
			Float of the percent change rounded to 4 sig figs. IE 60.49

		"""
		return round(((new_price - old_price) / old_price) * 100, 2)


	def _create_embed(self, outputs: dict) -> discord.Embed: 
		"""
		Generates a pretty embed for discord consisting of two groups,
		the significant price changes / RSI vals.

		Args:
			outputs: Dictionary of rsi and price update outputs

		Returns:
			a discord.Embed of price/rsi updates

		"""

		r = lambda: random.randint(0, 255)
		color = (r(), r(), r())
		hex_color = (int("0x%02x%02x%02x" % color, 16))

		embed = discord.Embed(
			title="Updates @ {}".format(datetime.datetime.now().strftime("%H:%M")), type="rich", 
			colour=discord.Colour(hex_color), 
			)

		if outputs["rsi"]:
			embed.add_field(name="RSI", value="".join(outputs["rsi"]))

		if outputs["price_updates"]:
			embed.add_field(name="Price Updates", value="".join(outputs["price_updates"]))

		return embed

	def _get_output(self, *items: list) -> str:
		"""
		Creates a discord.Embed friendly formatting and returns it.

		Args:
			*items: Items to concatonate together into one output.

		Returns:
			Discord friendly text !

		"""

		return " ".join(*items) + "\n\n"


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

		if depth == max_depth:
			self._logger.warning("{0} Failed to GET data. Depth: {1}".format(url, depth))
			return {}

		try:
			async with session.get(url) as resp:
				return await resp.json()
		except aiohttp.errors.ServerDisconnectedError:
			self._logger.warning("{0} ServerDisconnectedError".format(url))
			return await self._query_exchange(session, url, depth=depth+1)


	async def _load_markets(self, session: aiohttp.ClientSession) -> None:
		"""
		Asynchronously loads the markets from bittrex and binance markets.
		This loaded data is used to check percent change.

		Args:
			session: The aiohttp session to be used to query the markets

		Returns:
			None
		
		"""
		self._markets["Binance"] = await self._get_binance_markets(session)
		self._markets["Bittrex"] = await self._get_bittrex_markets(session)


	async def _get_binance_markets(self, session: aiohttp.ClientSession) -> dict:
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
		

	async def _get_bittrex_markets(self, session: aiohttp.ClientSession) -> dict:
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


	async def _get_market_history(self, session:aiohttp.ClientSession, market: str,
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


	async def _calc_rsi(self, session: aiohttp.ClientSession, market: str) -> int:
		"""	
		Calculates & Returns the RSI of market according to the RSI formula
		
		RSI = 100 - ( 100 / ( 1 + RS ) )
	
		RS = Average Gains / Average Losses
	
		Average Gains
			1st avg gain = sum of gains over past n periods / n
			Everything after = (Prev Avg Gain * n-1 + current gain) / n
	
		Average Loss
			1st avg loss = sum of losses over past n period / n
			Everything after = (Prev Avg Gain * n-1 + current loss) / n
		
		Args:
			session: The aiohttp ClientSession to be used to GET data from exchanges.
			market: The market to calculate RSI for.

		Returns:
			The RSI of market.
	

		"""

		interval = self._rsi_time_frame
		history = await self._get_market_history(
			session, market, self._rsi_tick_interval
			)

		res = history["result"]
		closing_prices = [buy["C"] for buy in res]

		# sort first interval prices
		losses = []
		gains = []

		for i in range(1, interval):
			change = closing_prices[i] - closing_prices[i-1]
			if change < 0:
				losses.append(abs(change))
			elif change > 0:
				gains.append(change)


		# calc intial avg changes / losses
		avg_gain = sum(gains) / interval
		avg_loss = sum(losses) / interval

		# smooth calc avg change / losses
		for i in range(interval, len(closing_prices)):
			change = closing_prices[i] - closing_prices[i-1]

			# sort loss and gain
			loss = abs(change) if change < 0 else 0
			gain = change if change > 0 else 0

			avg_gain = (avg_gain * (interval - 1) + gain) / interval
			avg_loss = (avg_loss * (interval - 1) + loss) / interval

		RS = avg_gain / avg_loss
		RSI = int ( 100 - ( 100 / ( 1 + RS ) ) )

		return RSI
	

	async def _process_market(self, session: aiohttp.ClientSession, market_info: dict) -> list:
		"""
		Asynchronously processes market_info from any market following protocol.
		Generates outputs for significant RSIs/price changes.
		 
		market_info = {
			"exchange": str,
			"market_name": str,
			"old_price": double,
	 		"new_price": double,
			"1h": double,
			"24h": double,
		}
	
		Args:
			session: The aiohttp ClientSession to be used to GET data from exchange
			market_info: Market info, follows format {
				"exchange": str,
				"market_name": str,
				"old_price": double,
		 		"new_price": double,
				"1h": double,
				"24h": double,
			}

		Returns:
			List of all outputs from signifcant price changes / RSIs

		"""
		exchange = market_info["exchange"]
		name = market_info["market_name"]
		old_price = market_info["old_price"]
		new_price = market_info["new_price"]

		# self._logger.debug("Processing {0}".format(name))

		change = self._percent_change(new_price, old_price)
		self._logger.debug("{0} Change {1} old_price {2} new_price {3}".
			format(name, change, old_price, new_price)
			)

		outs = {"rsi": [], "price_updates": []}

		# Calculating RSI only works for bittrex rn
		if exchange == "Bittrex":
			rsi = await self._calc_rsi(session, name)
			self._logger.debug("RSI {0}".format(rsi))
			if rsi >= self._over_bought or rsi <= self._over_sold:

				# make sure that rsi hasn't been significant yet
				if name not in self._significant_markets:
					self._logger.debug("Not significant yet, creating output")

					outs["rsi"].append(self._get_output([name, "RSI:", str(rsi)]))

					self._significant_markets.add(name)

			elif name in self._significant_markets:
				self._logger.debug(
					"Previously significant, no longer significant, removing."
					)
				self._significant_markets.remove(name)



		if change >= self._mooning or change <= self._free_fall:
			self._logger.debug("Change significant, creating output")
			outs["price_updates"].append( 
				self._get_output([name, "changed by", str(change), "on", exchange])
				)

		self._logger.debug("Outputs: {0}".format(outs))
		return outs


	async def _check_binance_markets(self, session: aiohttp.ClientSession) -> tuple:
		"""
		Checks binance markets for significant price/rsi updates.

		Args:
			session: The aiohttp ClientSession to be used to GET data from binance
		
		Returns:
			tuple of outputs & price updates
		
		"""
		outputs = {"rsi": [], "price_updates": []}
		price_updates = {}

		new_markets = await self._get_binance_markets(session)

		old_markets = self._markets["Binance"]

		for i, old_market in enumerate(old_markets):

			new_market = new_markets[i]

			symb1 = old_market["symbol"]
			symb2 = new_market["symbol"]

			if symb1 == symb2:
				try:
					old_price = float(old_market["price"])
					new_price = float(new_market["price"])
				except:
					continue

				info = {
					"exchange": "Binance",
					"market_name": symb1,
					"old_price": old_price,
					"new_price": new_price,
				}

				out = await self._process_market(session, info)
				for key, val in out.items(): outputs[key].extend(val)

				# make sure price updates
				change = self._percent_change(new_price, old_price)
				if change >= self._mooning or change <= self._free_fall:
					price_updates[i] = new_price

		return (outputs, price_updates)


	async def _check_bittrex_markets(self, session: aiohttp.ClientSession) -> tuple:
		"""
		Checks bittrex markets for significant price/rsi updates.

		Args:
			session: The aiohttp ClientSession to be used to GET data from bittrex
		
		Returns:
			tuple of outputs & price updates
		
		"""
		self._logger.debug("Checking bittrex markets")

		outputs = {"rsi": [], "price_updates": []}
		price_updates = {}

		new_markets = await self._get_bittrex_markets(session)

		old_markets = self._markets["Bittrex"]

		# get percent change through all the marketspyt
		for i, old_market in enumerate(old_markets["result"]):
			try:
				new_market = new_markets["result"][i]

				old_market_name = old_market["MarketName"]
				new_market_name = new_market["MarketName"]
			except IndexError: #idk
				continue 

			if old_market_name == new_market_name:
				try: 
					old_price = float(old_market["Last"])
					new_price = float(new_market["Last"])
				except:
					continue

				info = {
					"exchange": "Bittrex",
					"market_name": old_market_name,
					"old_price": old_price,
					"new_price": new_price,
					"1h": None,
					"24h": None,
				}

				out = await self._process_market(session, info)
				for key, val in out.items(): outputs[key].extend(val)

				# make sure price updates
				change = self._percent_change(new_price, old_price)
				if change >= self._mooning or change <= self._free_fall:
					price_updates[i] = new_price

		return (outputs, price_updates)


	def _update_prices(self, price_updates: dict) -> None:
		"""
		Updates prices in market dictionary. This is used to prevent
		price update spam. Only updates price if it was significant.

		Args:
			price_updates: Prices and their exchange to update,
				follows format. {
					"Bittrex": {
						0: price,
						1: price,
						etc, etc !
					}
					"Binance": {
						Same thing!
					}
				}
		
		Returns:
			None

		"""

		self._logger.debug("Updating prices: {0}".format(price_updates))
		
		# update bittrex markets
		bittrex_markets = self._markets["Bittrex"]["result"]
		for i, price in price_updates["Bittrex"].items():

			self._logger.debug("Market: {0} Last: {1} New: {2}".format(
				bittrex_markets[i]["MarketName"], bittrex_markets[i]["Last"], price)
			)

			bittrex_markets[i]["Last"] = price

		# Update binance markets
		binance_markets = self._markets["Binance"]
		for i, price in price_updates["Binance"].items():

			self._logger.debug("Market: {0} Last: {1} New: {2}".format(
				binance_markets[i]["symbol"], binance_markets[i]["price"], price)
			)

			binance_markets[i]["price"] = price


	async def check_markets(self) -> None:
		"""
		Processes bittrex and binance markets for signifcant price/rsi updates 
		and sends outputs to discord.
		
		Does while self._updating is true every interval minutes. 

		Args:
			None

		Returns:
			None
		
		"""
		async with aiohttp.ClientSession() as session:

			# load markets
			await self._load_markets(session)

			# loop through at least once
			while self._updating:
				price_updates = {}

				self._logger.info("Checking markets")

				outputs, price_updates["Bittrex"] = await self._check_bittrex_markets(
					session
					)

				outputs2, price_updates["Binance"] = await self._check_binance_markets(
					session
					)

				for key, val in outputs2.items(): outputs[key].extend(val)
				self._logger.debug("Outputs: {0}".format(outputs))

				self._update_prices(price_updates)

				embed = self._create_embed(outputs)
				await self._client.send_message(
					destination=discord.Object(id=self._update_channel), embed=embed
					)

				self._logger.debug("Async sleeping {0}".format(str(self._interval * 60)))
				await asyncio.sleep(int(self._interval*60))


	async def start_checking_markets(self, message: discord.Message) -> None:
		"""
		Begins checking markets, notifies user who called for it of that it's starting.

		Args:
			message: The message used to ask the bot to start, used
				to mention the user that it's starting.

		Returns:
			None

		"""
		self._updating = True
		await self._client.send_message(
			message.channel , "Starting {0.author.mention} !".format(message)
			)
		self._logger.info("Starting to check markets.")
		await self.check_markets()


	async def stop_checking_markets(self, message: discord.Message) -> None:
		"""
		Stops checking markets, notifies user who called for it of that it's stopping.

		Args:
			message: The message used to ask the bot to stop, used
				to mention the user that it's stopping.

		Returns:
			None

		"""
		self._logger.info("Stopping checking markets")
		await self._client.send_message(
			message.channel, "Stopping {0.author.mention} !".format(message)
			)
		self._updating = False


	async def greet(self, message: discord.Message) -> None:
		"""
		Greets whoever wants to be greeted !

		Args:
			message: message used to ask for a greet from the bot.
				Used to mention the user for greet.

		Returns:
			None

		"""
		await self._client.send_message(
			message.channel, "Hello {0.author.mention} !".format(message)
			)

	async def exit(self, message: discord.Message) -> None:
		"""
		Shutsdown the bot, logs it, and notifies user who called for it of the exit

		Args:
			message: Discord message used to call for exit.

		Returns:
			None

		"""

		await self._client.send_message(
			message.channel, "Bye {0.author.mention}!".format(message)
			)
		sys.exit()


def get_config() -> dict:
	with open(CONFIG_FILE, "r") as f:
		return json.load(f)


def setup_logging(config: dict) -> None:
	with open(LOGGING_CONFIG, "r") as f:
		log_config = yaml.load(f)

		logging.config.dictConfig(log_config)

		level = logging.INFO if config["debug"] == 0 else logging.DEBUG
		
		console_logger = logging.getLogger("main")
		console_logger.setLevel(level)

		bot_logger = logging.getLogger("bot")
		bot_logger.setLevel(level)

		console_logger.debug("Set up logging")


if __name__ == '__main__':

	# intialize everything
	client = discord.Client()

	config = get_config()
	setup_logging(config)

	logger = logging.getLogger("main")
	bot = Bot(client=client, config=config, logger=logging.getLogger("bot"))

	prefix = config["command_prefix"]
	
	# client events
	@client.event
	async def on_ready():
		logger.info("logged in")
		logger.debug("logged in as {0}".format(client.user.name))

	@client.event
	async def on_message(message):
		content = message.content

		# Default greet
		if content.startswith("%sgreet" % prefix):
			await bot.greet(message)

		elif content.startswith("%shelp" % prefix):
			await client.send_message(
				message.channel, "```Starts checking bittrex and binance markets and\
				 prints the significant changes.\n")

		elif content.startswith("%sstart" % prefix):
			await bot.start_checking_markets(message)

		elif content.startswith("%sstop" % prefix):
			await bot.stop_checking_markets(message)

		elif content.startswith("%sexit" % prefix):
			await bot.exit(message)

	# start
	token = config["token"]
	client.run(token)
