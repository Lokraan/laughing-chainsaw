
import logging.config
import datetime
import logging
import asyncio
import psycopg2
import locale
import random
import yaml
import json
import sys
import re

import discord
import aiohttp

sys.path.append("helpers/")

import output_generator as og
import exchange_interface
import market_processor
import database

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
		self._prefix = config["prefix"]

		self.mi = exchange_interface.ExchangeInterface(self._logger)
		self.mp = market_processor.Processor(self._logger, config, self.mi)

		self._db = database.ServerDatabase("hasami", "hasami", "password")

		self._updating = False

		self._client.loop.create_task(self._set_playing_status())
		self._client.loop.create_task(self._check_exchanges())


	async def _set_playing_status(self):
		locale.setlocale(locale.LC_ALL, "")

		while True:
			await self._client.wait_until_ready()

			data = await self.mi.get_crypto_mcap()

			mc = int(data["total_market_cap_usd"])
			mc = locale.currency(mc, grouping=True)

			self._logger.info("Setting market cap {0}".format(mc))

			await self._client.change_presence(
				game=discord.Game(name=mc))

			await asyncio.sleep(900)


	async def add_server_for_signals(self, message: discord.Message, 
			exchanges: list) -> None:

		await self._client.send_message(
			message.channel , "Starting {0.author.mention} !".format(message)
			)

		if not exchanges:
			exchanges = ["bittrex"]

		server_id = message.server.id
		server_name = message.server.name
		
		if not self._db.server_exists(server_id):
			self._db.add_server(server_id, server_name, self._prefix)

		# load markets
		await self.mp.load_exchanges(exchanges)

		self._db.update_output_channel(server_id, message.channel.id)
		self._db.add_exchanges(server_id, exchanges)

		text = "Added {0.server.name}-{0.channel} to rsi/update outputs and checking {1}"\
			.format(message, exchanges)

		self._logger.info(text)


	async def _check_exchanges(self) -> None:
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

		# initialize updates
		servers = self._db.servers_wanting_signals()

		for server in servers:
			exchanges = server[3].split(" ")
			self._logger.info("Loading exchanges {0}".format(exchanges))
			await self.mp.load_exchanges(exchanges)

		await asyncio.sleep(int(self._interval*60))

		while True:
			await self._client.wait_until_ready()

			processed_exchanges = {}

			servers = self._db.servers_wanting_signals()

			for server in servers:

				server_id = server[0]
				server_name = server[1]

				channel = server[2]
				exchanges = server[3]

				channel = discord.Object(channel)
				exchanges = exchanges.split(" ")

				outputs = {}

				# no need to perform multiple calculations on pre-processed exchanges
				for exchange in exchanges:
					if exchange in processed_exchanges:
						outputs[exchange] = processed_exchanges[exchange]

				# remove duplicate exchanges so they don't get processed
				exchanges = [ex for ex in exchanges if ex not in outputs]

				self._logger.info("Checking exchanges {0} for server {1} ({2})".format(
					exchanges, server_id, server_name))

				outputs.update(await self.mp.process_exchanges(exchanges))
				self._logger.debug(outputs)

				for exchange, embeds in outputs.items():
					processed_exchanges[exchange] = embeds
					for embed in embeds:
						await self._client.send_message(destination=channel, 
							embed=embed)

			await asyncio.sleep(int(self._interval*60))


	async def stop_checking_markets(self, message: discord.Message, exchanges: list) -> None:
		"""
		Stops checking markets, notifies user who called for it of that it's stopping.

		Args:
			message: The message used to ask the bot to stop, used
				to mention the user that it's stopping.

		Returns:
			None

		TODO: 
			If no markets are specified stop completely, else remove exchanges from being
			updated.

		"""
		chan = message.channel

		await self._client.send_message(
			message.channel, "Stopping {0.author.mention} !".format(message))

		server_id = message.server.id
		self._db.update_output_channel(server_id, None)
		
		if len(exchanges) == 0:
			text = "Removing {0.server.name}-{1} from update channels"\
				.format(message, chan)

			self._db.update_exchanges(server_id, None)

		else:
			text = "Removing exchanges {2} from {0.server.name}-{1}"\
				.format(message, chan, exchanges)

			self._db.remove_exchanges(server_id, exchanges)

		self._logger.info(text)


	async def price(self, message: discord.Message, markets: list) -> None:
		for market in markets:

			if market == "":
				continue

			market = await self.mp.find_cmc_ticker(market)

			if not market:
				continue

			info = await self.mi.cmc_market_query(market)
			await self._client.send_message(
				message.channel, embed=og.create_cmc_price_embed(info[0]))


	async def crypto_cap(self, message: discord.Message) -> None:

		info = await self.mi.get_crypto_mcap()

		await self._client.send_message(
			message.channel, embed=og.create_cmc_cap_embed(info))


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


	async def source(self, message: discord.Message) -> None:
		await self._client.send_message(message.channel, "https://github.com/lokraan/hasami")


	async def change_prefix(self, message: discord.Message, params: list) -> None:
		


	def joined_server(server):
		self._logger.info("Joined {0}".format(server.name))

		self._db.add_server(server.id, server.name, self._prefix)
