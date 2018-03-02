
import discord
import ccxt
import re


class CommandProcessor:
	def __init__(self, bot, logger, db):
		self._logger = logger
		self._bot = bot
		self._db = db

	async def process_message(self, message: discord.Message):
		# Default greet

		content = message.content

		print(content)
		prefix = self._db.get_prefix(message.server.id)

		if content.startswith(prefix):
			content = content.strip(prefix)

			regex = "\\s+|,?"

			content_split = re.split(regex, content)

			print(content_split)

			cmd = content_split[0]
			params = content_split[1:]

			if cmd == "greet":
				self._logger.info("Greeted {0.author}".format(message))	
				await self._bot.greet(message)

			elif cmd == "help":
				self._logger.info("Helped {0.author}".format(message))
				await self._bot.help(message)

			elif cmd == "start":
				text = "{0.author} asked to start checking exchanges {1}".format(message, params)
				self._logger.info(text)

				await self._bot.add_server_for_signals(message, params)

			elif cmd == "stop":
				text = "{0.author} asked to stop checking exchanges {1}".format(message, params)
				self._logger.info(text)

				await self._bot.stop_sending_signals(message, params)

			elif cmd == "price" or cmd == "p":
				text = "{0.author} asked for the price of markets {0}".format(message, params)
				self._logger.info(text)
				
				await self._bot.price(message, params)

			elif cmd == "cap":
				await self._bot.crypto_cap(message)

			elif cmd == "source":
				await self._bot.source(message)

			elif cmd == "prefix":
				user = message.author
				
				chann = message.channel
				permissions = chann.permissions_for(user)

				if permissions.administrator:
					if len(params) > 0:
						await self._bot.change_prefix(message, params)

			elif cmd in ccxt.exchanges:
				await self._bot.price(message, markets, exchange=getattr(ccxt, exchange))
