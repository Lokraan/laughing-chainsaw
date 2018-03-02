
import logging.config
import logging
import json
import yaml
import sys
import re

import discord

import hasami

sys.path.append("helpers/")

from command_processor import CommandProcessor
import database

CONFIG_FILE = "bot io/config.json"
LOGGING_CONFIG = "bot io/log_conf.yaml"


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

	db = database.ServerDatabase("hasami", "hasami", "password")
	bot = hasami.Bot(client=client, logger=logging.getLogger("bot"), config=config, db=db)

	command_processor = CommandProcessor(bot, logger, db)

	# client events
	@client.event
	async def on_ready():
		logger.info("logged in as {0}".format(client.user.name))


	@client.event
	async def on_message(message):
		await command_processor.process_message(message)

	@client.event
	async def on_server_join(server):
		self._logger.info("Joined {0}".format(server.name))
		
		bot.joined_server(server)

	# start
	token = config["token"]
	client.run(token)
