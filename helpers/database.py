
import asyncio
import asyncpg
import re

class ServerDatabase:
	def __init__(self, database, user, password=None):
		self._database = database
		self._user = user
		self._password = password

		loop = asyncio.get_event_loop()
		loop.run_until_complete(self.create_db())


	async def create_db(self):
		conn = await asyncpg.connect(
			database=self._database, user=self._user, password=self._password
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
			database=self._database, user=self._user, password=self._password)


	async def get_server(self, server_id: str) -> list:
		query = "SELECT * FROM servers WHERE id = $1"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				return await conn.fetchrow(query, server_id)


	async def server_exists(self, server_id: str):
		if await self.get_server(server_id):
			return True

		return False


	async def add_server(self, server_id: str, name: str, prefix: str):
		query = "INSERT INTO servers VALUES ($1, $2, $3, $4, $5)"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				await conn.execute(query, server_id, name, prefix, None, None)


	async def get_exchanges(self, server_id: str):
		query = "SELECT exchanges FROM servers WHERE id = $1"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query, server_id)

				return res


	async def get_output_channel(self, server_id: str):
		query = "SELECT output_channel FROM servers WHERE id = $1"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query, server_id)
				
				return res


	async def get_prefix(self, server_id: str):
		query = "SELECT prefix FROM servers WHERE id = $1"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query, server_id)

				return res


	async def get_servers(self):
		query = "SELECT id, name FROM servers"
		
		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query, server_id)

				return res


	async def update_prefix(self, server_id: str, prefix: str) -> None:
		query = "UPDATE servers SET prefix = $1 WHERE id = $2"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				await conn.execute(query, prefix, server_id)


	async def update_output_channel(self, server_id: str, output_channel: str) -> None:
		query = "UPDATE servers SET output_channel = $1 WHERE id = $2"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				await conn.execute(query, output_channel, server_id)


	async def update_exchanges(self, server_id: str, exchanges: list) -> None:
		query = "UPDATE servers SET exchanges = $1 WHERE id = $2"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				await conn.execute(query, exchanges, server_id)


	async def add_exchanges(self, server_id: str, new_exchanges: list) -> None:
		exchanges = await self.get_exchanges(server_id)

		if exchanges:
			exchanges.extend(new_exchanges)
		else:
			exchanges = new_exchanges

		# remove duplicates
		exchanges = set(exchanges)
		exchanges = list(exchanges)

		await self.update_exchanges(server_id, exchanges)


	async def remove_exchanges(self, server_id: str, removed_exchanges: list) -> None:
		exchanges = await self.get_exchanges(server_id)

		if exchanges:
			exchanges = [ex for ex in exchanges if ex not in removed_exchanges]
			await self.update_exchanges(server_id, exchanges)


	async def number_update_servers(self) -> int:
		query = "SELECT Count(*) FROM servers WHERE output_channel IS NOT NULL"

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetchval(query)

				return res


	async def servers_wanting_signals(self) -> list:
		query = """
			SELECT id, name, output_channel, exchanges 
			FROM servers WHERE output_channel IS NOT NULL
			"""

		async with self.pool.acquire() as conn:
			async with conn.transaction():
				res = await conn.fetch(query)

				return res
