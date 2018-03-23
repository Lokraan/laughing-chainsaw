
def calc_rsi(data: list, period: int) -> int:
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
		data: data used to calculate rsi
		period: period used to calculate rsi

	Returns:
		The RSI of the data given.

	"""

	# sort first period prices
	losses = []
	gains = []

	if len(data) == 0:
		return 50

	closing_prices = [i[4] for i in data]

	max_len = period if period < len(closing_prices) else len(closing_prices)

	for i in range(1, max_len):
		change = closing_prices[i] - closing_prices[i-1]
		if change < 0:
			losses.append(abs(change))
		elif change > 0:
			gains.append(change)


	# calc intial avg changes / losses
	avg_gain = sum(gains) / period
	avg_loss = sum(losses) / period

	# smooth calc avg change / losses
	for i in range(period, len(closing_prices)):
		change = closing_prices[i] - closing_prices[i-1]

		# sort loss and gain
		loss = abs(change) if change < 0 else 0
		gain = change if change > 0 else 0

		avg_gain = (avg_gain * (period - 1) + gain) / period
		avg_loss = (avg_loss * (period - 1) + loss) / period

	if avg_gain == 0:
		return 0
	elif avg_loss == 0:
		return 100

	RS = avg_gain / avg_loss
	RSI = 100 - ( 100 / (1 + RS))

	return int(RSI)
