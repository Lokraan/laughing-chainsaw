
import traceback
import logging
import asyncio
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
from exchange_processor import ExchangeProcessor
from database import ServerDatabase

class Hasami:
	"""
	Bot used to analyze the bittrex and binance markets for significant price changes and
	RSI values.

	These significant markets are then printed out into a discord server.

	Attributes:
		_client: Client used to communicate with the discord server.
		_logger: Logger to be used when logging.
		_db: database used to get and store servre data.
		_interval: Time to wait between each analysis of the markets.
		_prefix: Default prefix used to specify commands.

	"""

	def __init__(self, client: discord.Client, logger: logging.Logger, 
			config: dict, db=None):

		self._client = client
		self._logger = logger
		self._db = db

		self._interval = config["update_interval"]
		self._prefix = config["prefix"]

		self.exchange_processor = ExchangeProcessor(self._logger, config, self._db)

		self._client.loop.create_task(self._set_playing_status())


	async def start(self):
		"""
		Starts the bot by loading the exchange data for any exchanges to be checked
		and then starts sending price/rsi signals.
		"""

		await self._initialize_checker()
		self._client.loop.create_task(self.send_server_price_update_signals())
		self._client.loop.create_task(self.send_server_rsi_update_signals())


	async def _set_playing_status(self):
		"""
		Sets the playing status in disocrd to be the current market cap of
		cryptocurrencies as a whole.
		"""

		locale.setlocale(locale.LC_ALL, "")

		while True:
			await self._client.wait_until_ready()

			data = await self.exchange_processor.get_crypto_mcap()

			mc = int(data["total_market_cap_usd"])
			mc = locale.currency(mc, grouping=True)

			self._logger.info("Setting market cap {0}".format(mc))

			await self._client.change_presence(
				game=discord.Game(name=mc))

			await asyncio.sleep(900)


	async def add_server_for_signals(self, message: discord.Message, 
			exchanges: list) -> None:

		"""
		Swets the output channel and exchanges that the sever wants toget signals for
		and adds it to the database if it already isn't. Uses bittrex as the default
		exchange if none are specified.

		Args:
			message: message used to ask for signals
			exchanges: exchanges the server wants signals for

		"""

		await self._client.send_message(
			message.channel , "Starting {0.author.mention} !".format(message)
			)

		if not exchanges:
			exchanges = ["bittrex"]

		server_id = message.server.id
		server_name = message.server.name
		
		if not await self._db.server_exists(server_id):
			await self._db.add_server(server_id, server_name, self._base_prefix)

		# load markets
		await self.exchange_processor.load_exchanges(exchanges)

		await self._db.update_output_channel(server_id, message.channel.id)
		await self._db.add_exchanges(server_id, exchanges)

		text = "Added {0.server.name}-{0.channel} to rsi/update outputs and checking {1}"
		self._logger.info(text.format(message, exchanges))


	async def _initialize_checker(self) -> None:
		"""
		Loads the exchange data for servers that want signals. This allows for the
		bot to continously get signals without asking again even if bot goes down.
		"""

		for server in self._client.servers:
			if not await self._db.server_exists(server.id):
				await self._db.add_server(server.id, server.name, self._prefix)

			elif await self._db.get_output_channel(server.id):
				exchanges = await self._db.get_exchanges(server.id)

				if not exchanges == None:
					self._logger.info("Loading exchanges {0}".format(exchanges))

					await self.exchange_processor.load_exchanges(exchanges)


	async def send_server_price_update_signals(self) -> None:
		"""
		Goes through all servers that wants price update signals in database 
		and sends them for the exchanges specified.
		"""

		while True:
			servers = await self._db.servers_wanting_signals()

			if not servers:
				await asyncio.sleep(int(self._interval * 60))
				continue

			try: 
				data = self.exchange_processor.yield_exchange_price_updates(servers)
				async for channel, embed in data:
					await self._client.wait_until_ready()
					channel = discord.Object(channel)
					await self._client.send_message(channel, embed=embed)

			except Exception as e:
				self._logger.debug(traceback.print_exc())
				self._logger.warning(e)

			await asyncio.sleep(int(self._interval * 60))


	async def send_server_rsi_update_signals(self) -> None:
		"""
		Goes through all servers that wants rsi update signals in database 
		and sends them for the exchanges specified.
		"""

		while True:
			servers = await self._db.servers_wanting_signals()

			if not servers: 
				await asyncio.sleep(int(self._interval * 60))
				continue

			try:
				data = self.exchange_processor.yield_exchange_rsi_updates(servers)
				async for channel, embed in data:
					await self._client.wait_until_ready()
					channel = discord.Object(channel)
					await self._client.send_message(channel, embed=embed)

			except Exception as e:
				self._logger.debug(traceback.print_exc())
				self._logger.warning(e)

			await asyncio.sleep(int(self._interval * 60))


	async def stop_sending_signals(self, message: discord.Message, exchanges: list) -> None:
		"""
		Stops checking exchanges for the exchanges given, notifies user who called for 
		it of that it's stopping. If no exchanges are specified then it stops
		completely.

		Args:
			message: The message used to ask the bot to stop, used
				to mention the user that it's stopping.
			exchanges: exchanges to remove 

		"""

		chan = message.channel

		await self._client.send_message(
			message.channel, "Stopping {0.author.mention} !".format(message))

		server_id = message.server.id
		await self._db.update_output_channel(server_id, None)
		
		if len(exchanges) == 0:
			text = "Removing {0.server.name}-{1} from update channels"\
				.format(message, chan)

			await self._db.update_exchanges(server_id, None)

		else:
			text = "Removing exchanges {2} from {0.server.name}-{1}"\
				.format(message, chan, exchanges)

			await self._db.remove_exchanges(server_id, exchanges)

		self._logger.info(text)


	async def price(self, message: discord.Message, markets: list) -> None:
		"""
		Sends price for markets given from cmc in a pretty embed.

		Args:
			message: message used to ask for price, sends to message channel
			markets: markets the prices are asked for

		"""

		for market in markets:

			market = await self.exchange_processor.find_cmc_ticker(market)

			if not market:
				continue

			info = await self.exchange_processor.cmc_market_query(market)
			await self._client.send_message(
				message.channel, embed=og.create_cmc_price_embed(info[0]))


	async def crypto_cap(self, message: discord.Message) -> None:
		"""
		Sends the cryptocurrency marketcap in a pretty embed to the message that
		request it's channel.

		Args:
			message: message used to ask for crypto market cap.
		"""

		info = await self.exchange_processor.get_crypto_mcap()

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


	async def source(self, message: discord.Message) -> None:
		"""
		Sends the github link to whoever asked for it.

		Args:
			message: message used to ask for the source
		"""

		await self._client.send_message(message.channel, "https://github.com/lokraan/hasami")


	async def change_prefix(self, message: discord.Message, prefix: str) -> None:
		"""
		Changes the prefix for the message's server to the prefix specified.

		Args:
			message: message used to ask for the prefix change.
			prefix: prefix to change to

		"""
		await self._db.update_prefix(message.server.id, prefix)

		text = "Changed {0.author.mention} prefix to {1}".format(message, prefix)
		await self._client.send_message(message.channel, text)
