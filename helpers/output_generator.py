
import datetime
import asyncio
import discord
import random

def get_output(*items: list) -> str:
		"""
		Creates a discord.Embed friendly formatting and returns it.

		Args:
			*items: Items to concatonate together into one output.

		Returns:
			Discord friendly text !

		"""

		return " ".join(*items)


def create_embed(title: str, text: str, highlight: bool = True, 
	discord_mark_up: str ='ini', color: int = None) -> discord.Embed: 
	"""
	Generates a pretty embed for discord consisting of two groups,
	the significant price changes / RSI vals.

	Args:
		outputs: Tuple of what the data is called and the data.

	Returns:
		a discord.Embed of items inside the list

	"""

	r = lambda: random.randint(0, 255)
	color = (r(), r(), r())

	if not text:
		return None

	embed = discord.Embed(
		title=title, type="rich", 
		timestamp=datetime.datetime.now(),
		colour=discord.Colour(color)
		)

	if highlight:
		text = "```{0}\n{1}\n```".format(discord_mark_up, text) 
		print(text, len(list(text)))

	#\u200b
	embed.add_field(name="\u200b", value=text, inine=False)

	return embed
