
import asyncio
import asyncpg
import re

class ServerDatabase:
	"""
	Database used to store server information and preferences. This is used to allow
	customization and continuation of services after reboot without having the users
	respecify their preferences etc.

	Database uses asyncpg: a asynchronous library for PostgreSQL

	Attributes:
		_datbase: postgresql database to connect to
		_user: postgresql user to connect to
		_host: host postgresql is using
		_passsword: password for the user
	"""
	def __init__(self, database, user, host, logger, password=None):
		self._database = database
		self._user = user
		self._host = host
		self._logger = logger
		self._password = password

		loop = asyncio.get_event_loop()
		loop.run_until_complete(self._create_db())


	async def _create_db(self):
		"""
		Creates the database if it doesn't exist and instantiates a pool to broker
		requests between async processes.
		"""
		conn = await asyncpg.connect(
			database=self._database, user=self._user,
			password=self._password, host=self._host
			)

		await conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS servers (
				id TEXT PRIMARY KEY, 
				name TEXT,
				prefix TEXT,
				output_channel TEXT, 
				exchanges TEXT ARRAY
			)
			"""
		)

		await conn.close()

		self.pool = await asyncpg.create_pool(
			database=self._database, user=self._user, 
			host=self._host, password=self._password
			)

		self._logger.info("Set up database")


	async def get_server(self, server_id: str) -> list:
		"""
		Returns server information:
			id
			name
			prefix
			output_channel
			exchanges

		Args:
			server_id: server whose information is to be selected
		"""
		query = "SELECT * FROM servers WHERE id = $1"
		self._logger.debug("Getting server {0}".format(server_id))

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				return await conn.fetchrow(query, server_id)


	async def server_exists(self, server_id: str) -> bool:
		"""
		Checks if server entry exists inside the database.

		Args:
			server_id: server whose information is to be selected

		Returns:
			True if the server entry exists, else false.
		"""
		if await self.get_server(server_id):
			return True

		return False


	async def add_server(self, server_id: str, name: str, prefix: str) -> None:
		"""
		Adds server to database, output_channel and exchanges are null by default

		Args:
			server_id: server whose information is to be selected
			name: server name to be put inside
			prefix: prefix to be used for commands in the server

		"""
		query = "INSERT INTO servers VALUES ($1, $2, $3, $4, $5)"
		self._logger.debug("Adding server {0}".format(server_id))

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				await conn.execute(query, server_id, name, prefix, None, None)


	async def get_exchanges(self, server_id: str) -> list:
		"""
		Gets exchanges that the server wants signals for.

		Args:
			server_id: server whose information is to be selected

		Returns:
			list of exchanges that the server wants signals for

		"""
		query = "SELECT exchanges FROM servers WHERE id = $1"
		self._logger.debug("Getting exchanges from server {0}".format(server_id))

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query, server_id)

				return res


	async def get_output_channel(self, server_id: str) -> str:
		"""
		Gets the output_channel the server wants signals sent to.

		Args:
			server_id: server whose information is to be selected

		Returns:
			str of the output_channel's id

		"""
		query = "SELECT output_channel FROM servers WHERE id = $1"
		self._logger.debug("Getting out_channel from server {0}".format(server_id))

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query, server_id)
				
				return res


	async def get_prefix(self, server_id: str) -> str:
		"""
		Gets the prefix the server wants commands to be specified by.

		Args:
			server_id: server whose information is to be selected

		Returns:
			str of the prefix

		"""
		query = "SELECT prefix FROM servers WHERE id = $1"
		self._logger.debug("Getting prefix from server {0}".format(server_id))

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query, server_id)

				return res


	async def get_servers(self) -> list:
		"""
		Gets every server's id & name (Will be deprecated)

		Args:
			server_id: server whose information is to be selected

		Returns:
			list of all server's information

		"""
		query = "SELECT id, name FROM servers"
		self._logger.debug("Getting all servers")

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query, server_id)

				return res


	async def update_prefix(self, server_id: str, prefix: str) -> None:
		"""
		Sets the prefix to the one the server wants commands to be specified by.

		Args:
			server_id: server whose prefix is to be changed
			prefix: what the curr prefix is to be changed to

		"""
		query = "UPDATE servers SET prefix = $1 WHERE id = $2"
		self._logger.debug("Updating prefix to {0} for server {1}"\
			.format(prefix, server_id))

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				await conn.execute(query, prefix, server_id)


	async def update_output_channel(self, server_id: str, output_channel: str) -> None:
		"""
		Sets the output_channel to the one the server wants signals to be sent to.

		Args:
			server_id: server whose prefix is to be changed
			output_channel: what the curr output_channel is to be changed to

		"""
		query = "UPDATE servers SET output_channel = $1 WHERE id = $2"
		self._logger.debug("Updating out_channel to {0} for server {1}"\
			.format(output_channel, server_id))

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				await conn.execute(query, output_channel, server_id)


	async def update_exchanges(self, server_id: str, exchanges: list) -> None:
		"""
		Sets the exchanges to the ones the server wants

		Args:
			server_id: server whose prefix is to be changed
			exchanges: what the curr exchanges are to be to changed to

		"""
		query = "UPDATE servers SET exchanges = $1 WHERE id = $2"
		self._logger.debug("Updating exchanges to {0} for server {1}"\
			.format(exchanges, server_id))

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				await conn.execute(query, exchanges, server_id)


	async def add_exchanges(self, server_id: str, new_exchanges: list) -> None:
		"""
		Adds exchanges to current exchanges the server is using.

		Args:
			server_id: server whose prefix is to be changed
			new_exchanges: exchanges to be added

		"""
		self._logger.debug("Adding exchanges {0} for server {1}"\
			.format(exchanges, server_id))
		exchanges = await self.get_exchanges(server_id)

		if exchanges:
			exchanges.extend(new_exchanges)
		else:
			exchanges = new_exchanges

		# remove duplicates
		exchanges = list(set(exchanges))

		await self.update_exchanges(server_id, exchanges)


	async def remove_exchanges(self, server_id: str, removed_exchanges: list) -> None:
		"""
		Removes exchanges from the current exchanges the server is using.

		Args:
			server_id: server whose prefix is to be changed
			new_exchanges: exchanges to be added

		"""
		self._logger.debug("Removing exchanges {0} for server {1}"\
			.format(exchanges, server_id))
		exchanges = await self.get_exchanges(server_id)

		if exchanges:
			exchanges = [ex for ex in exchanges if ex not in removed_exchanges]
			await self.update_exchanges(server_id, exchanges)


	async def number_update_servers(self) -> int:
		"""
		Gets the count of current servers asking for signals.

		Returns:
			the number of servers asking for signals as an integer

		"""
		self._logger.debug("Getting number update servers")
		query = "SELECT Count(*) FROM servers WHERE output_channel IS NOT NULL"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query)

				return res


	async def servers_wanting_signals(self) -> list:
		"""
		Gets the information of all the servers wanting signals.

		Returns:
			a list of all the servers wanting information

		"""
		self._logger.debug("Getting data for servers that want signals")
		query = """
			SELECT id, name, output_channel, exchanges 
			FROM servers WHERE output_channel IS NOT NULL
			"""

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetch(query)

				return res
