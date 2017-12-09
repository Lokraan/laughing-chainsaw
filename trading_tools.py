
"""

RSI = 100 - ( 100 / ( 1 + RS ) )

RS = Average Gains / Average Losses

Average Gains: 
	1st avg gain = sum of gains over past n periods / n
	Everything after = (Prev Avg Gain * n-1 + current gain) / n

Average Loss:
	1st avg loss = sum of losses over past n period / n
	Everything after = (Prev Avg Gain * n-1 + current loss) / n

"""
def calc_rsi(gains, losses, last_avg_gain=None, last_avg_loss=None, ret_averages=False):
	assert len(gains) == len(losses) # Make sure data matches up
	assert len(gains) > 0 # Make sure there's data

	n = len(gains)

	if last_avg_gain:
		average_gain = ( ( last_avg_gain * (n - 1) ) + gains[-1] ) / n 
	else:
		average_gain = sum(gains) / n

	if last_avg_loss:
		average_loss = ( ( last_avg_loss * (n - 1) ) + losses[-1] ) / n
	else:
		average_loss = sum(losses) / n
	
	try:
		RS = average_gain / average_loss
		RSI = 100 - ( 100 / ( 1 + RS ) ) 
	except ZeroDivisionError:
		# No losses at all bb
		RSI = 100
		if average_gain == 0:
			RSI = 0
	
	if not ret_averages:
		return RSI
	
	return ( RSI , average_gain , average_loss ) 

