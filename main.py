
import logging
import json
import yaml
import sys
import re

import discord

from bot import Hasami

sys.path.append("helpers/")

from command_processor import CommandProcessor
import database

CONFIG_FILE = "config.json"

def get_config() -> dict:
	with open(CONFIG_FILE, "r") as f:
		return json.load(f)


def setup_logging(config: dict) -> None:
	logging.getLogger("discord.http").setLevel(logging.WARNING)
	logging.getLogger("discord").setLevel(logging.INFO)

	logger = logging.getLogger()

	level = logging.DEBUG if config["debug"] else logging.INFO

	f_handler = logging.FileHandler(filename="hasami.log", encoding="utf-8", mode="w")
	cl_handler = logging.StreamHandler()

	dt_fmt = "%Y-%m-%d %H:%M:%S"
	fmt = logging.Formatter("[{asctime}] [{levelname:<6}] {name}: {message}", dt_fmt, style="{")

	cl_handler.setFormatter(fmt)
	f_handler.setFormatter(fmt)

	logger.addHandler(cl_handler)
	logger.addHandler(f_handler)
	logger.setLevel(level)


if __name__ == '__main__':

	# intialize everything
	client = discord.Client()

	config = get_config()
	setup_logging(config)

	logger = logging.getLogger()

	db = database.ServerDatabase(config["dbuser"], config["dbname"], 
		config["dbhost"], config["dbpass"])

	bot = Hasami(client=client, logger=logging.getLogger("bot"), config=config, db=db)
	command_processor = CommandProcessor(client, bot, logger, db)

	# client events
	@client.event
	async def on_ready():
		logger.info("logged in as {0}".format(client.user.name))
		await bot.start()


	@client.event
	async def on_message(message):
		await command_processor.process_message(message)


	@client.event
	async def on_server_join(server):
		self._logger.info("Joined {0}".format(server.name))
		db.add_server(server.id, server.name, config["prefix"])	


	token = config["token"]
	client.run(token)
