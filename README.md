# Hasami
Hasami is a discord bot that monitors bittrex and binance exchanges for significant changes in price / significant RSI values and prints it out in a specified channel.

It also prints out the market cap of the entire crypto market and market information into nicely formatted discord embeds upon request. (Data from coinmarketcap.)

## Adding the bot to your server
I currently host the bot 24/7 on a vps and you're free to add it to your discord server if you'd like. To enable price/rsi updates just type `$start` in the desired channel and it will starts sending price/rsi updates to the channel. To stop it type, `$stop`.

https://discordapp.com/oauth2/authorize?client_id=392534322894340096&scope=bot


## Hosting it yourself.
For basic personal use you need to set `"token"` to your personal bot's token, and `"update_channel"` to the channel the bot should print updates to in [config.json](/config.json)

It is not necessary to include the update channel, as typing `$start` uses the current channel for price/rsi updates and `$stop` removes it.

```json
"token": "your token",
"update_channel": "your channel id",
```

### Commands
| Command | Description |
| --- | --- |
| `$start` | Starts checking the markets for price/rsi updates in the channel the message was sent. | 
| `$stop` | Stops checking the markets for price/rsi updates in the channel the message was sent. | 
| `$exit` | Shuts down the bot. |
| `$greet` | Greets whoever wants to be greeted. |
| `$price` | Gets market data for currency specified after, ie `$price eth` |
| `$cap` | Gets the marketcap of cryptocurrencies as a whole. |

### Requirements
- Python >= 3.5.3
- [discord](https://github.com/Rapptz/discord.py) (pip install discord)
- [aiohttp](https://github.com/aio-libs/aiohttp) (pip install aiohttp) 
- [pyyaml](https://github.com/yaml/pyyaml) (pip install pyyaml)


### Configuration
All configuration takes place within [config.json](/config.json)

```json
{
	"token": "your token",
	"update_channel": "your channel id",
	"free_fall": -4,
	"mooning": 4,
	"rsi_tick_interval": "thirtyMin",
	"rsi_time_frame": 14, 
	"over_bought": 75,
	"over_sold": 25,
	"update_interval": 1,
	"debug": 0,
	"command_prefix": "$"
}
```

| Option | Description | 
| --- | --- | 
| `token` | The bot's token to use to create connection with discord | 
| `update_channel` | The channel the bot will print updates to |
| `free_fall` | Low value to flag market for printing **(Price Change)**|
| `mooning` | High value to flag market for printing **(Price Change)** |
| `rsi_tick_interval` | Interval between each tick used to calculate **(RSI)** [Options](https://github.com/thebotguys/golang-bittrex-api/wiki/Bittrex-API-Reference-(Unofficial)#getticks): "oneMin", "fiveMin", "thirtyMin", "hour", "day".  |
| `rsi_time_frame` | Number of ticks to use to calculate **(RSI)** |
| `over_bought` | Over bought value to flag market for printing **(RSI)** |
| `over_sold` | Over sold value to flag market for printing **(RSI)** | 
| `update_interval` | Delay between each time it checks the markets (in minutes) |
| `debug` | Whether in debug mode or not. Increases info logged. |
| `command_prefix` | Prefix used to specify a command to a bot. |

### What it's doing
When a market's growth/decline is greater than or equal to `mooning` or `free_fall`, the bot flags it and prints an update according to this format.
```
<market_name> changed by <change> on <exchange>
```

When a market's rsi value is greater than or equal to `over_bought` or `over_sold`, the bot flags it and prints an update according to this format.
```
<market_name> RSI: <rsi>
```

## TODO
1. Support for more exchanges.

