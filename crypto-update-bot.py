
from collections import deque
import requests
import json
import time
import discord
import asyncio

client = discord.Client()

CLIENT_TOKEN = "YOUR_TOKEN_HERE"
CHANNEL_ID = "YOUR_CHANNEL_ID"
MOONING = 4
FREE_FALL = -10	

def get_percent_change(old_price, new_price):
	return round( float ( ( (new_price - old_price ) / old_price ) * 100 ) 	, 2)


def get_output(market, percent_change, exchange):
	prefix = "increased by"
	if(percent_change < 0):
		prefix = "decreased by"

	everything = ["```\n", market, prefix, str(percent_change) + "%", "on" + exchange, "\n```"]
	return " ".join(everything)


def check_bittrex_markets(old_markets):

	outputs = []
	price_updates = {}

	new_markets = json.loads(requests.get("https://bittrex.com/api/v1.1/public/getmarketsummaries").text)

	# get percent change through all the markets
	for i, old_market in enumerate(old_markets["result"]):

		# print(i)
		try:
			new_market = new_markets["result"][i]

			old_market_name = old_market["MarketName"]
			new_market_name = new_market["MarketName"]
		except IndexError:
			continue 

		if old_market_name == new_market_name:
			try: 
				old_price = float(old_market["Last"])
				new_price = float(new_market["Last"])
			except:
				continue

			percent_change = get_percent_change(old_price, new_price)
			
			if percent_change > MOONING or percent_change < FREE_FALL:
				output = get_output(new_market_name, percent_change, "Bittrex")
				outputs.append(output)
				price_updates[i] = new_price	
				
			else:
				pass

	return (outputs, price_updates)


def check_binance_markets(old_markets):
	outputs = []
	price_updates = {}

	new_markets = json.loads(requests.get("https://api.binance.com/api/v1/ticker/allPrices").text)
	for i, old_market in enumerate(old_markets):

			new_market = new_markets[i]

			symb1 = old_market["symbol"]
			symb2 = new_market["symbol"]

			if symb1 == symb2:
				try:
					old_price = float(old_market["price"])
					new_price = float(new_market["price"])
				except:
					continue

				percent_change = get_percent_change(old_price, new_price)
	 			
				if percent_change > MOONING or percent_change < FREE_FALL:
					output = get_output(symb2, percent_change, "Binance")
					outputs.append(output)

					price_updates[i] = new_price	

				else:
					pass

	return (outputs, price_updates)

def update_market_history(history, market, change):
	if market not in history:
		history[market] = {"gains": deque(), "losses": deque()}
	else:
		m_hist = history["market"]
		if change > 0:
			m_hist["gains"].append(change)
			m_hist["losses"].append(0)
		else:	
			m_hist["losses"].append(change)
			m_hist["gains"].append(0)
	
	return history

@client.event
async def on_ready():
	target_channel = client.get_channel(CHANNEL_ID)
	print("Logged in? ?? ")

	# await client.send_message(target_channel, 'Now Online')

	bittrex_markets = json.loads(requests.get("https://bittrex.com/api/v1.1/public/getmarketsummaries").text)
	binance_markets = json.loads(requests.get("https://api.binance.com/api/v1/ticker/allPrices").text)

	RSI_HISTORY_LENGTH = 14
	market_history = {}
		
	while True:

		# update bittrex markets
		outputs, price_updates = check_bittrex_markets(bittrex_markets, market_history)
		for i, price in price_updates.items():
			market = bittrex_markets["result"][i]
			
			# update market hitory for rsi
			change = get_percent_change(market["Last"], price)
			market_history = update_market_history(market_history, market, change)			
		
		market["Last"] = price

		# update Binance markets
		outputs2, price_updates = check_binance_markets(binance_markets, market_history)
		for i, price in price_updates2.items():
			market = binance_markets[i]
			
			change = get_percent_change(market["Last"], price)
			market_history = update_market_history(market_history, market, change)		

			market["price"] = price

		
		# send out outputs
		outputs.extend(outputs2)
		for out in outputs:
			await client.send_message(target_channel, out)
			await asyncio.sleep(1)
					

		#time.sleep(20)
		await asyncio.sleep(40)

client.run(CLIENT_TOKEN)
