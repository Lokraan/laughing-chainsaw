
import discord
import ccxt
import re

from exchange_processor import ExchangeProcessor

class MessageProcessor:
	"""
	Class to process messages and repsond to basic ones that don't require
	processing.

	Attributes:
		_client: client used to communicate with discord
		_logger: logger used to log events
		_bot: bot used to process commands
		_db: db used to get server preferences for commands 
	"""
	def __init__(self, client, bot, logger, db):
		self._client = client
		self._logger = logger
		self._bot = bot
		self._db = db

		self._ep = ExchangeProcessor(logger=self._logger)


	def is_admin(self, message: discord.Message) -> bool:
		"""
		Checks if the person who sent the message is an admin.

		Args:
			message: message sent.

		Returns:
			true if admin, false if not

		"""

		chann = message.channel
		permissions = chann.permissions_for(user)

		return premissions.administrator


	async def process_message(self, message: discord.Message) -> None:
		"""
		Processes message based on the message's server's preferences.

		Commands it processed are
		| Command  | Description|
		| :------: | ---------- |
		| `$start <exchanges>`  | Starts checking the exchanges for price/rsi updates in the channel the message was sent. *Uses bittrex by default*| 
		| `$stop <exchanges>`   | Stops checking the exchanges for price/rsi updates in the channel the message was sent.  *Uses bittrex by default*| 
		| `$prefix <prefix>`    | Sets the prefix for the current server to the prefix specified. *Only works for users with admin privileges*      |
		| `$price`  | Gets market data for currency specified after, ie `$price eth` |
		| `$cap`    | Gets the marketcap of cryptocurrencies as a whole.             |
		| `$help`   | Private messages user bot commands and github .                |
		| `$greet`  | Greets whoever wants to be greeted. |
		| `$source` | Prints the link to this repository. |	

		Args:
			message: message sent and to be processed

		"""
		# Default greet

		content = message.content

		prefix = await self._db.get_prefix(message.server.id)

		if prefix == None:
			pass

		if content.startswith(prefix):
			content = content.replace(prefix, "", 1)

			regex = ",?\\s+|,"

			content_split = re.split(regex, content)

			cmd = content_split[0]
			params = content_split[1:]

			if cmd == "greet":
				self._logger.info("Greeted {0.author}".format(message))	
				await self._client.send_message(
					message.channel, "Hello {0.author.mention} !".format(message))

			elif cmd == "help":
				help_message = """
					| Command  | Description|
					| :------: | ---------- |
					| `$start <exchanges>`  | Starts checking the exchanges for price/rsi updates in the channel the message was sent. *Uses bittrex by default*| 
					| `$stop <exchanges>`   | Stops checking the exchanges for price/rsi updates in the channel the message was sent.  *Uses bittrex by default*| 
					| `$prefix <prefix>`    | Sets the prefix for the current server to the prefix specified. *Only works for users with admin privileges*      |
					| `$price`  | Gets market data for currency specified after, ie `$price eth` |
					| `$cap`    | Gets the marketcap of cryptocurrencies as a whole.             |
					| `$help`   | Private messages user bot commands and github .                |
					| `$greet`  | Greets whoever wants to be greeted. |
					| `$source` | Prints the link to this repository. |	
					https://github.com/lokraan/hasami
				"""
				
				self._logger.info("Helped {0.author}".format(message))
				await self._client.send_message(message.author, help_message)

			elif cmd == "start":
				text = "{0.author} asked to start checking exchanges {1}".format(message, params)
				self._logger.info(text)

				await self._bot.add_server_for_signals(message, params)

			elif cmd == "stop":
				text = "{0.author} asked to stop checking exchanges {1}".format(message, params)
				self._logger.info(text)

				await self._bot.stop_sending_signals(message, params)

			elif cmd == "price" or cmd == "p":
				text = "{0.author} asked for the price of markets {1}".format(message, params)
				self._logger.info(text)
				
				await self._bot.price(message, params)

			elif cmd == "cap":
				await self._bot.crypto_cap(message)

			elif cmd == "source":
				await self._client.send_message(message.channel, 
					"https://github.com/lokraan/hasami")

			elif cmd == "prefix":
				if self.is_admin(message) and len(params) > 0:
					await self._bot.change_prefix(message, params[0])

			elif cmd in ccxt.exchanges:
				await self._bot.price(message, markets, exchange=getattr(ccxt, exchange))

			elif await self._ep.find_cmc_ticker(cmd):
				await self._bot.price(message, [cmd])
