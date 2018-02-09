
import market_grabber


class Processor:
	def __init__(self, logger, config):
		self._logger = logger

		self._makrets = {}
		self._significant_markets = set()


	async def _load_markets(self, session: aiohttp.ClientSession) -> None:
		"""
		Asynchronously loads the markets from bittrex and binance markets.
		This loaded data is used to check percent change.

		Args:
			session: The aiohttp session to be used to query the markets

		Returns:
			None
		
		"""
		self._markets["Binance"] = await self._get_binance_markets(session)
		self._markets["Bittrex"] = await self._get_bittrex_markets(session)


	def _update_prices(self, price_updates: dict) -> None:
		"""
		Updates prices in market dictionary. This is used to prevent
		price update spam. Only updates price if it was significant.

		Args:
			price_updates: Prices and their exchange to update,
				follows format. {
					"Bittrex": {
						0: price,
						1: price,
						etc, etc !
					}
					"Binance": {
						Same thing!
					}
				}
		
		Returns:
			None

		"""

		self._logger.debug("Updating prices: {0}".format(price_updates))
		
		# update bittrex markets
		bittrex_markets = self._markets["Bittrex"]["result"]
		for i, price in price_updates["Bittrex"].items():
			self._logger.debug("Market: {0} Last: {1} New: {2}".format(
				bittrex_markets[i]["MarketName"], bittrex_markets[i]["Last"], price)
			)

			bittrex_markets[i]["Last"] = price

		# Update binance markets
		binance_markets = self._markets["Binance"]
		for i, price in price_updates["Binance"].items():
			self._logger.debug("Market: {0} Last: {1} New: {2}".format(
				binance_markets[i]["symbol"], binance_markets[i]["price"], price)
			)

			binance_markets[i]["price"] = price


	async def _send_embed(self, embed: discord.Embed, depth: int = 1, max_depth: int = 3):
		if depth == max_depth:
			self._logger.error("failed to send embed after %s tries" % depth)

		try:
			await self._client.send_message(
				destination=discord.Object(id=self._update_channel), embed=embed
				)
		except discord.errors.HTTPException:
			print(embed, embed.fields, embed.title)
			self._logger.warning("Failed to send embed try %s" % depth)
			await self._send_embed(embed=embed, depth=depth+1)

	def percent_change(self, new_price: int, old_price: int) -> float:
		"""
		Calculates and returns change in value between new_price and old_price

		Args:
			new_price: new price to be compared to old price.
			old_price: old price to be compared to new price.

		Returns:
			Float of the percent change rounded to 4 sig figs. IE 60.49

		"""
		return round(((new_price - old_price) / old_price) * 100, 2)


	async def calc_rsi(self, session: aiohttp.ClientSession, market: str) -> int:
		"""
		Calculates & Returns the RSI of market according to the RSI formula
		
		RSI = 100 - ( 100 / ( 1 + RS ) )

		RS = Average Gains / Average Losses

		Average Gains
			1st avg gain = sum of gains over past n periods / n
			Everything after = (Prev Avg Gain * n-1 + current gain) / n

		Average Loss
			1st avg loss = sum of losses over past n period / n
			Everything after = (Prev Avg Gain * n-1 + current loss) / n
		
		Args:
			session: The aiohttp ClientSession to be used to GET data from exchanges.
			market: The market to calculate RSI for.

		Returns:
			The RSI of market.


		"""

		interval = self._rsi_time_frame
		history = await self._get_market_history(
			session, market, self._rsi_tick_interval
			)

		res = history["result"]
		closing_prices = [buy["C"] for buy in res]

		# sort first interval prices
		losses = []
		gains = []

		if len(closing_prices) == 0:
			return 50

		for i in range(1, interval):
			change = closing_prices[i] - closing_prices[i-1]
			if change < 0:
				losses.append(abs(change))
			elif change > 0:
				gains.append(change)


		# calc intial avg changes / losses
		avg_gain = sum(gains) / interval
		avg_loss = sum(losses) / interval

		# smooth calc avg change / losses
		for i in range(interval, len(closing_prices)):
			change = closing_prices[i] - closing_prices[i-1]

			# sort loss and gain
			loss = abs(change) if change < 0 else 0
			gain = change if change > 0 else 0

			avg_gain = (avg_gain * (interval - 1) + gain) / interval
			avg_loss = (avg_loss * (interval - 1) + loss) / interval

		RS = avg_gain / avg_loss
		RSI = int(100 - ( 100 / (1 + RS)))

		return RSI
		

	async def process_market(self, session: aiohttp.ClientSession, market_info: dict) -> list:
		"""
		Asynchronously processes market_info from any market following protocol.
		Generates outputs for significant RSIs/price changes.
		 
		market_info = {
			"exchange": str,
			"market_name": str,
			"old_price": double,
	 		"new_price": double,
			"1h": double,
			"24h": double,
		}

		Args:
			session: The aiohttp ClientSession to be used to GET data from exchange
			market_info: Market info, follows format {
				"exchange": str,
				"market_name": str,
				"old_price": double,
		 		"new_price": double,
				"1h": double,
				"24h": double,
			}

		Returns:
			List of all outputs from signifcant price changes / RSIs

		"""
		exchange = market_info["exchange"]
		name = market_info["market_name"]
		old_price = market_info["old_price"]
		new_price = market_info["new_price"]

		# self._logger.debug("Processing {0}".format(name))

		change = self._percent_change(new_price, old_price)
		self._logger.debug("{0} Change {1} old_price {2} new_price {3}".
			format(name, change, old_price, new_price)
			)

		outs = {"RSI": [], "Price Updates": []}

		# Calculating RSI only works for bittrex rn
		if exchange == "Bittrex":
			rsi = await self._calc_rsi(session, name)
			self._logger.debug("RSI {0}".format(rsi))
			if rsi >= self._over_bought or rsi <= self._over_sold:

				# make sure that rsi hasn't been significant yet
				if name not in self._significant_markets:
					self._logger.debug("Not significant yet, creating output")

					outs["RSI"].append(
							"[{0}] RSI: [{1}]".format(name, rsi)
						)

					self._significant_markets.add(name)

			elif name in self._significant_markets:
				self._logger.debug(
					"Previously significant, no longer significant, removing."
					)
				self._significant_markets.remove(name)


		if change >= self._mooning or change <= self._free_fall:
			self._logger.debug("Change significant, creating output")

			prefix = "-" if change < 0 else prefix = "+" 

			outs["Price Updates"].append(
				"{0} {1} changed by {2}%  on {3}".format(prefix, name, str(change), exchange)
				)

		self._logger.debug("Outputs: {0}".format(outs))
		return outs


	async def _check_binance_markets(self, session: aiohttp.ClientSession) -> tuple:
		"""
		Checks binance markets for significant price/rsi updates.

		Args:
			session: The aiohttp ClientSession to be used to GET data from binance
		
		Returns:
			tuple of outputs & price updates
		
		"""
		outputs = {"RSI": [], "Price Updates": []}
		price_updates = {}

		new_markets = await self._get_binance_markets(session)

		old_markets = self._markets["Binance"]

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

				info = {
					"exchange": "Binance",
					"market_name": symb1,
					"old_price": old_price,
					"new_price": new_price,
				}

				out = await self._process_market(session, info)
				for key, val in out.items(): outputs[key].extend(val)

				# make sure price updates
				change = self._percent_change(new_price, old_price)
				if change >= self._mooning or change <= self._free_fall:
					price_updates[i] = new_price

		return (outputs, price_updates)


	async def _check_bittrex_markets(self, session: aiohttp.ClientSession) -> tuple:
		"""
		Checks bittrex markets for significant price/rsi updates.

		Args:
			session: The aiohttp ClientSession to be used to GET data from bittrex
		
		Returns:
			tuple of outputs & price updates
		
		"""
		self._logger.debug("Checking bittrex markets")

		outputs = {"RSI": [], "Price Updates": []}
		price_updates = {}

		new_markets = await self._get_bittrex_markets(session)

		old_markets = self._markets["Bittrex"]

		# get percent change through all the marketspyt
		for i, old_market in enumerate(old_markets["result"]):
			try:
				new_market = new_markets["result"][i]

				old_market_name = old_market["MarketName"]
				new_market_name = new_market["MarketName"]
			except IndexError: #idk
				continue 

			if old_market_name == new_market_name:
				try: 
					old_price = float(old_market["Last"])
					new_price = float(new_market["Last"])
				except:
					continue

				info = {
					"exchange": "Bittrex",
					"market_name": old_market_name,
					"old_price": old_price,
					"new_price": new_price,
					"1h": None,
					"24h": None,
				}

				out = await self._process_market(session, info)
				for key, val in out.items(): outputs[key].extend(val)

				# make sure price updates
				change = self._percent_change(new_price, old_price)
				if change >= self._mooning or change <= self._free_fall:
					price_updates[i] = new_price

		return (outputs, price_updates)


	async def _process_market(self, session: aiohttp.ClientSession, market_info: dict) -> list:
		"""
		Asynchronously processes market_info from any market following protocol.
		Generates outputs for significant RSIs/price changes.
		 
		market_info = {
			"exchange": str,
			"market_name": str,
			"old_price": double,
	 		"new_price": double,
			"1h": double,
			"24h": double,
		}

		Args:
			session: The aiohttp ClientSession to be used to GET data from exchange
			market_info: Market info, follows format {
				"exchange": str,
				"market_name": str,
				"old_price": double,
		 		"new_price": double,
				"1h": double,
				"24h": double,
			}

		Returns:
			List of all outputs from signifcant price changes / RSIs

		"""
		exchange = market_info["exchange"]
		name = market_info["market_name"]
		old_price = market_info["old_price"]
		new_price = market_info["new_price"]

		# self._logger.debug("Processing {0}".format(name))

		change = self._percent_change(new_price, old_price)
		self._logger.debug("{0} Change {1} old_price {2} new_price {3}".
			format(name, change, old_price, new_price)
			)

		outs = {"RSI": [], "Price Updates": []}

		# Calculating RSI only works for bittrex rn
		if exchange == "Bittrex":
			rsi = await self._calc_rsi(session, name)
			self._logger.debug("RSI {0}".format(rsi))
			if rsi >= self._over_bought or rsi <= self._over_sold:

				# make sure that rsi hasn't been significant yet
				if name not in self._significant_markets:
					self._logger.debug("Not significant yet, creating output")

					outs["RSI"].append(
							"[{0}] RSI: [{1}]".format(name, rsi)
						)

					self._significant_markets.add(name)

			elif name in self._significant_markets:
				self._logger.debug(
					"Previously significant, no longer significant, removing."
					)
				self._significant_markets.remove(name)


		if change >= self._mooning or change <= self._free_fall:
			self._logger.debug("Change significant, creating output")

			prefix = "-" if change < 0 else prefix = "+" 

			outs["Price Updates"].append(
				"{0} {1} changed by {2}%  on {3}".format(prefix, name, str(change), exchange)
				)

		self._logger.debug("Outputs: {0}".format(outs))
		return outs
