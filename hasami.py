
import logging.config
import datetime
import logging
import asyncio
import random
import yaml
import json
import sys
import re

import discord
import aiohttp

sys.path.append("helpers/")

import output_generator as og
import processor as processor
import market_grabber


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
	def __init__(self, client: discord.Client, logger: logging.Logger, config: dict):
		self._client = client
		self._logger = logger
	
		# config stuff

		self._interval = config["update_interval"]
		self._update_channel = config["update_channel"]


		self.mi = market_grabber.MarketInterface(self._logger)
		self.mp = processor.Processor(self._logger, config, self.mi)

		self._cmc_pairs = []


	async def check_markets(self, message: discord.Message) -> None:
		"""
		Begins checking markets, notifies user who called for it of that it's starting.

		Processes bittrex and binance markets for signifcant price/rsi updates 
		and sends outputs to discord. 
		
		Does while self._updating is true every interval minutes. 

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
		async with aiohttp.ClientSession() as session:

			# load markets
			await self.mp.load_markets(session)

			# loop through at least once
			while self._updating:
				price_updates = {}

				self._logger.info("Checking markets")

				outputs, price_updates["Bittrex"] = await self.mp.check_bittrex_markets(
					session
					)

				outputs2, price_updates["Binance"] = await self.mp.check_binance_markets(
					session
					)

				# send outputs
				for key, val in outputs2.items(): 
					outputs[key].extend(val)
					self._logger.debug("Outputs: {0}".format(outputs))

					highlight =  "diff" 
					if key == "RSI":
						highlight = "ini"

					embed = og.create_embed(title=key, text="\n".join(outputs[key]), 
						highlight=True, discord_mark_up=highlight)

					if embed:
						await self._client.send_message(
							destination=discord.Object(self._update_channel), embed=embed)

				self._logger.debug("Async sleeping {0}".format(str(self._interval * 60)))
				await asyncio.sleep(int(self._interval*60))

				self.mp.update_prices(price_updates)


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



	async def price(self, message: discord.Message, markets: list) -> None:
		for market in markets:

			if market == "":
				continue

			market = await self.mp.find_cmc_ticker(market)

			if not market:
				continue

			info = await self.mi.cmc_query(market)
			await self._client.send_message(
				message.channel, embed=og.create_cmc_embed(info[0]))


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
	bot = Bot(client=client, logger=logging.getLogger("bot"), config=config)

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
			logger.info("Greeted")
			await bot.greet(message)

		elif content.startswith("%shelp" % prefix):
			logger.info("Helped")
			await client.send_message(
				message.channel, "```Starts checking bittrex and binance markets and\
				 prints the significant changes.\n")

		elif content.startswith("%sstart" % prefix):
			logger.info("Checking markets")
			await bot.check_markets(message)

		elif content.startswith("%sstop" % prefix):
			logger.info("Not checking amrkets")
			await bot.stop_checking_markets(message)

		elif content.startswith("%sexit" % prefix):
			logger.info("Exiting")
			await bot.exit(message)

		elif content.startswith("%sprice" % prefix) or content.startswith("%sp" % prefix):
			markets = re.split("\s|,", content)[1:]
			logger.info("Price for markets {}".format(markets))
			await bot.price(message, markets) 

	# start
	token = config["token"]
	client.run(token)
