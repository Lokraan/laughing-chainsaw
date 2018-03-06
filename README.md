# Hasami
Hasami is a discord bot that provides...
- Notifications for significant price changes and RSI values.
- Information for the cryptocurrency market as a whole or individual cryptocurrencies.
- Dynamic prefixes.


## Adding the bot to your server
Hasami is currently hosted 24/7 on a vps--[vultr](https://www.vultr.com/?ref=7308111)--and you're more than welcome to use it instead of hosting it yourself. All commands work as specified in the commands section.

[Invite Bot](https://discordapp.com/oauth2/authorize?client_id=392534322894340096&scope=bot)

If you have any questions feel free to contact me on discord; my username is **Lokraan#3797**


## Hosting it yourself.
For basic personal use you need to set `"token"` to your personal bot's token in [config.json](/config.json). You will also need to install and set up a database for the bot using postgresql on your computer. 
[this](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-16-04) is a nice tutorial by digital ocean that walks you through the process. 

After you've done this you'll need to put your database auth info into the config.


```json
"token": "your token",
"dbname": "your database",
"dbuser": "your user",
"dbpass": "your password",
"dbhost": "localhost"
```

### Commands
| Command  | Description|
| :------: | ---------- |
| `$start <exchanges>`  | Starts checking the exchanges for price/rsi updates in the channel the message was sent. *Uses bittrex by default*| 
| `$stop <exchanges>`   | Stops checking the exchanges for price/rsi updates in the channel the message was sent.  *Uses bittrex by default*| 
| `$prefix <prefix>`    | Sets the prefix for the current server to the prefix specified. *Only works for users with admin privileges*      |
| `$price`  | Gets market data for currency specified after, ie `$price eth` |
| `$cap`    | Gets the marketcap of cryptocurrencies as a whole.             |
| `$help`   | Private messages user bot commands and github.                 |
| `$greet`  | Greets whoever wants to be greeted. |
| `$source` | Prints the link to this repository. |


### Requirements
- Python >= 3.5.3
- [tenacity](https://github.com/jd/tenacity) (pip install tenacity)
- [discord](https://github.com/Rapptz/discord.py) (pip install discord)
- [asyncpg](https://github.com/MagicStack/asyncpg) (pig install asyncpg)
- [aiohttp](https://github.com/aio-libs/aiohttp) (pip install aiohttp)
- [pyyaml](https://github.com/yaml/pyyaml) (pip install pyyaml)
- [ccxt](https://github.com/ccxt/ccxt) (pip install ccxt)


### Configuration
All configuration takes place within [config.json](/config.json)
{
	"token": "your token",
	"free_fall": -5,
	"mooning": 5,
	"rsi_timeframe": "30m",
	"rsi_period": 14, 
	"over_bought": 80,
	"over_sold": 30,
	"update_interval": 1,
	"debug": false,
	"prefix": "$",
	"dbname": "your database",
	"dbuser": "your user",
	"dbpass": "your password",
	"dbhost": "localhost"
}


| Option  | Description | 
| :-----: | ----------- | 
| `token`     | The bot's token to use to create connection with discord | 
| `free_fall` | Low value to flag market for printing **(Price Change)**|
| `mooning`   | High value to flag market for printing **(Price Change)** |
| `rsi_timeframe`  | Interval between each tick used to calculate **RSI** |
| `rsi_period`  | Period used when calculating RSI **(RSI)** |
| `over_bought` | Over bought value to flag market for printing **(RSI)** |
| `over_sold`   | Over sold value to flag market for printing **(RSI)** | 
| `update_interval` | Delay between each time it checks the markets (in minutes) |
| `debug`           | Whether in debug mode or not. Increases info logged. |
| `prefix` | Default prefix used to specify a command to a bot. |
| `dbname` | Postgresql database to connect to. |
| `dbuser` | Postgresql user to use when connecting. | 
| `dbpass` | Password for database user. |
| `dbhost` | Host database is being hosted on. |


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
1. Debugging
2. Configurable RSI timeframes.
3. Administrative tools and metrics.
