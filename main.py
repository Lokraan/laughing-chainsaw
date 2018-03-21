
import logging
import json
import yaml
import sys
import re

import discord

from bot import Hasami

sys.path.append("helpers/")

from message_processor import MessageProcessor
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
	out_fmt = "[{asctime}] [{levelname:<6}] {name}: {message}"
	logger_fmt = logging.Formatter(out_fmt, dt_fmt, style="{")

	cl_handler.setFormatter(logger_fmt)
	f_handler.setFormatter(logger_fmt)

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

	bot = Hasami(client, logger, config, db)
	message_processor = MessageProcessor(client, bot, config["prefix"], logger, db)

	# client events
	@client.event
	async def on_ready():
		logger.info("logged in as {0}".format(client.user.name))
		await bot.start()


	@client.event
	async def on_message(message):
		await message_processor.process_message(message)


	@client.event
	async def on_server_join(server):
		self._logger.info("Joined {0}".format(server.name))
		db.add_server(server.id, server.name, config["prefix"])	


	token = config["token"]
	client.run(token)
