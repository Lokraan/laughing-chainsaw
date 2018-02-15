
import datetime
import asyncio
import discord
import random
import locale


def get_output(*items: list) -> str:
		"""
		Creates a discord.Embed friendly formatting and returns it.

		Args:
			*items: Items to concatonate together into one output.

		Returns:
			Discord friendly text !

		"""

		return " ".join(*items)


def get_color():
        r = lambda: random.randint(0, 255)
        
        color = (r(), r(), r())
        color = (int("0x%02x%02x%02x" % color, 16))
        
        return color


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

	if not color:
		color = get_color()

	if not text:
		return None

	embed = discord.Embed(
		title=title, type="rich", 
		timestamp=datetime.datetime.now(),
		colour=discord.Colour(color)
		)


	if highlight:
		text = "```{0}\n{1}\n```".format(discord_mark_up, text) 

	#\u200b
	embed.add_field(name="\u200b", value=text, inline=False)

	return embed


def create_cmc_price_embed(info: dict) -> discord.Embed:

	locale.setlocale(locale.LC_ALL, "")

	n = info["name"]
	n2 = info["id"]

	color = 0x21ff3b if float(info["percent_change_24h"]) >= 0 else 0xff0000
	img_url = "https://files.coinmarketcap.com/static/img/coins/32x32/{}.png".format(n2)

	embed = discord.Embed(
		title=n, url="https://coinmarketcap.com/currencies/{}/".format(n2),
		colour=color, timestamp=datetime.datetime.now()
		)

	text = locale.currency(float(info["price_usd"]), grouping=True)\
		+ " / " + info["price_btc"] + " BTC"

	changes = [info["percent_change_1h"], 
		info["percent_change_24h"], info["percent_change_7d"]]

	changes = [i if i else "0.0" for i in changes]

	suffixes = [" 1 hour", " 24 hour", " 1 week"]

	changes = ["{0: <8} - {1}".format(v + "%", suffixes[i]) if float(v) < 0 else 
			"{0: <8}  - {1}".format("+" + v + "%", suffixes[i])
			for i, v in enumerate(changes)]


	embed.set_thumbnail(url=img_url)
	embed.add_field(name="Price", value=text, inline=True)

	mc = float(info["market_cap_usd"]) if info["market_cap_usd"] else 0
	embed.add_field(name="Market Cap - Rank " + info["rank"], value=locale.currency(
		mc, grouping=True), inline=True)

	embed.add_field(name="\u200b", 
		value="```diff\nChange\n\n{}```".format('\n'.join(changes)), inline=False)

	return embed


def create_cmc_cap_embed(info: dict) -> discord.Embed:
        locale.setlocale(locale.LC_ALL, "")

        embed = discord.Embed(
                title="Crypto Market Cap", url="https://coinmarketcap.com/charts/",
                colour=0xc43aff, timestamp=datetime.datetime.now()
                )

        embed.set_thumbnail(
                url="https://files.coinmarketcap.com/static/img/coins/32x32/tether.png"
                )

        mc = locale.currency(float(info["total_market_cap_usd"]), grouping=True)
        embed.add_field(name="Total USD", value=mc, inline=True)

        mc = locale.currency(float(info["total_24h_volume_usd"]), grouping=True)
        embed.add_field(name="24h Volume USD", value=mc+"\n\u200b", inline=True)
        
#        embed.add_field(name="\u200b", value="-", inline=False)
        
        mc = "{}%".format(info["bitcoin_percentage_of_market_cap"])
        embed.add_field(name="Bitcoin Dominance", value=mc, inline=True)

        mc = info["active_currencies"]
        embed.add_field(name="Active Currencies", value=mc, inline=True)
        
        return embed
