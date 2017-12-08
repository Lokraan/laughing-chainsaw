# laughing-chainsaw
Watches bittrex and binance exchanges then posts on a discord channel what is increasing, by how much, and the exchange that it's increasing on.

Also provides support for displaying RSI data.

## Personal Use
There are two things that you currently need to change. (Lines 13 and 14)
```python
CLIENT_TOKEN = "YOUR_TOKEN_HERE"
CHANNEL_ID = "CHANNEL_ID_HERE"
```
Set `CLIENT_TOKEN` to your personal bot's token, and `CHANNEL_ID` to your personal channel's id.

## TODO
1. Support for more exchanges.
