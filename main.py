
import logging.config
import logging
import json
import yaml
import re

import discord

import hasami

CONFIG_FILE = "config.json"
LOGGING_CONFIG = "log_conf.yaml"


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
	bot = hasami.Bot(client=client, logger=logging.getLogger("bot"), config=config)

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
				 prints the significant changes.\n```")

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

		elif content.startswith("%scap" % prefix):
			await bot.crypto_cap(message)

		elif content.startswith("%ssource" % prefix):
			await client.send_message(message.channel, "https://github.com/lokraan/hasami")

	# start
	token = config["token"]
	client.run(token)
