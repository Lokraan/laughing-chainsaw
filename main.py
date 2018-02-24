
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

	prefix = config["prefix"]
	command_processor = CommandProcessor(bot, logger, prefix)

	# client events
	@client.event
	async def on_ready():
		logger.info("logged in")
		logger.debug("logged in as {0}".format(client.user.name))


	@client.event
	async def on_message(message):
		await command_processor.process_message(command)

	# start
	token = config["token"]
	client.run(token)
