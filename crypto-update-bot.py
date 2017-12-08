
from collections import deque
import os.path
import requests
import json
import time
import discord
import asyncio
import trading_tools

client = discord.Client()

# Connecting to discord
CLIENT_TOKEN = "Mzg0ODA5MzU4NTc3MzY5MDk5.DP4NUQ.Ht734YmbZsy-xYDcle7Rf52JAr8"
CHANNEL_ID = "384895816998977543"

# Vals to flag growth
MOONING = 4
FREE_FALL = -10	

# Vals to track history and RSI
M_HIST_FNAME = "market_histories.dat"
RSI_LENGTH = 14

def get_percent_change(old_price, new_price):
	return round( float ( ( (new_price - old_price ) / old_price ) * 100 ) 	, 2)

def get_output(market, percent_change, exchange):
	prefix = "increased by"
	if(percent_change < 0):
		prefix = "decreased by"

	m_histories = json.load(M_HIST_FNAME)
	m_changes = m_histories[market]
	
	# Data to calc RSI
	gains = m_changes["gains"]
	losses = m_changes["losses"]
	last_avg_gain = m_changes["avg_gain"]
	last_avg_loss = m_changes["avg_loss"]

	rsi = trading_tools.calc_rsi(gains, losses, 
		last_avg_gain=last_avg_gain, last_avg_loss=last_avg_loss, ret_averages=True)

	everything = ["```\n", market, prefix, str(percent_change) + "%", "on" + exchange, "RSI:", rsi, "\n```"]
	return " ".join(everything)

"""
Checks the binance markets and checks to see if market is MOONING or in FREE_FALL.
If MOONING or in FREE_FALL it creats an output for it consisting of it's:
	name
	exchange it's on
	percent growth or decline
	and it's RSI val

It also updates the market_history for the market
"""
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
			
			#update market history
			update_market_history(old_market_name, percent_change)

			# generate output if mooning or in free fall
			if percent_change > MOONING or percent_change < FREE_FALL:
				output = get_output(new_market_name, percent_change, "Bittrex")
				outputs.append(output)
				price_updates[i] = new_price	
				
	return (outputs, price_updates)


"""
Checks the binance markets and checks to see if market is MOONING or in FREE_FALL.
If MOONING or in FREE_FALL it creats an output for it consisting of it's:
	name
	exchange it's on
	percent growth or decline
	and it's RSI val

It also updates the market_history for the market
"""
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
								
				# update market history
				update_market_history(symb1, percent_change)

				# check to see if mooning or free falling, if so output 
				if percent_change > MOONING or percent_change < FREE_FALL:
					output = get_output(symb2, percent_change, "Binance")
					outputs.append(output)

					price_updates[i] = new_price	

	return (outputs, price_updates)

""" 

Updates the market_history using a file in JSON.
Loads the history, updates the gains and losses, then writes to the file.

market: {
	"gains": [ List of gains up to len 14 ] (If no gain, 0 is put in)
	"loss": [ List of gains up to len 14] (If no loss, 0 is put in)
	"avg_gain": Last avg gain (Default null)
	"avg_loss": Last avg loss (Default null)
}

"""

def update_market_history(market, change):
	m_histories = json.load(open(M_HIST_FNAME, 'r'))
	if market not in m_histories:
		m_histories[market] = {"gain": deque(maxlen=RSI_LENGTH), "loss": deque(maxlen=RSI_LENGTH), "avg_gain": None, "avg_loss": None}
	else:
		m_hist = m_histories[market]
		m_hist["gain"] = deque(m_hist["gain"], RSI_LENGTH)
		m_hist["loss"] = deque(m_hist["loss"], RSI_LENGTH)
		if change > 0:
			m_hist["gain"].append(change)
			m_hist["loss"].append(0)
		else:	
			m_hist["loss"].append(change)
			m_hist["gain"].append(0)

	m_histories.close()

	m_histories = open(M_HIST_FNAME, 'w')
	json.dump(m_histories)

	m_histories.close()
"""

MAIN GOES HERE 

"""
@client.event
async def on_ready():
	target_channel = client.get_channel(CHANNEL_ID)
	print("Logged in? ?? ")

	# await client.send_message(target_channel, 'Now Online')

	bittrex_markets = json.loads(requests.get("https://bittrex.com/api/v1.1/public/getmarketsummaries").text)
	binance_markets = json.loads(requests.get("https://api.binance.com/api/v1/ticker/allPrices").text)
	
	if not os.path.isfile(M_HIST_FNAME):
		f = open(M_HIST_FNAME, 'w')
		f.close()
	
	while True:
		# update bittrex markets
		outputs, price_updates = check_bittrex_markets(bittrex_markets)
		for i, price in price_updates.items():
			market = bittrex_markets["result"][i]
			
			# update market hitory for rsi
			change = get_percent_change(market["Last"], price)
			market["Last"] = price

		# update Binance markets
		outputs2, price_updates = check_binance_markets(binance_markets)
		for i, price in price_updates.items():
			market = binance_markets[i]
			
			change = get_percent_change(market["Last"], price)
			market["price"] = price
		
		# send out outputs
		outputs.extend(outputs2)
		for out in outputs:
			await client.send_message(target_channel, out)
			await asyncio.sleep(1)
			
	
client.run(CLIENT_TOKEN)
