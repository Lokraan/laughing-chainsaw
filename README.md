# laughing-chainsaw
Watches bittrex and binance exchanges then posts on a discord channel what is increasing, by how much, and the exchange that it's increasing on.

Also provides support for displaying RSI data.

## RSI Data
Currently whenever something is flagged, it prints the RSI along with the default info. 
RSI is calculated using a length of 14 past price changes. Price changes start being recorded
when the bot is first run. RSI data is store in a file labeled `market_history.dat'

This file can be editted by changing
```python
M_HIST_FNAME = "market_history.dat
```

The depth of the RSI calculation can be edditted as well by changing
```python
RSI_LENGTH = 14
```

## Personal Use
There are two things that you currently need to change. (Lines 13 and 14)
```python
CLIENT_TOKEN = "YOUR_TOKEN_HERE"
CHANNEL_ID = "CHANNEL_ID_HERE"
```
Set `CLIENT_TOKEN` to your personal bot's token, and `CHANNEL_ID` to your personal channel's id.

## TODO
1. Support for more exchanges.
