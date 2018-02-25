
import psycopg2
import re

class ServerDatabase:
	def __init__(self, dbname, username, password):
		self._conn = psycopg2.connect(dbname=dbname, user=username, password=password)
		self._cur = self._conn.cursor()

		self._cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS servers
			(id TEXT PRIMARY KEY, name TEXT,
			prefix TEXT, output_channel TEXT, 
			exchanges TEXT)
			"""
		)

		self._conn.commit()


	def add_server(self, server_id: str, name: str, prefix: str):
		query = "INSERT INTO servers VALUES (%s, %s, %s, %s, %s)"

		self._cur.execute(query, [server_id, name, prefix, None, None])


	def get_exchanges(self, server_id: str):
		query = "SELECT exchanges FROM servers WHERE id = %s LIMIT 1"

		self._cur.execute(query, [server_id])

		result = self._cur.fetchone()
		if result:
			return result[0]

		return result


	def get_output_channel(self, server_id: str):
		query = "SELECT output_channel FROM servers WHERE id = %s LIMIT 1"

		self._cur.execute(query, [server_id])

		result = self._cur.fetchone()
		if result:
			return result[0]

		return result


	def get_servers(self):
		query = "SELECT id, name FROM servers"
		self._cur.execute(query)

		result = self._cur.fetchone()

		return result


	def update_prefix(self, server_id: str, prefix: str) -> None:
		query = "UPDATE servers SET prefix = %s WHERE id = %s"

		self._cur.execute(query, [prefix, server_id])

		self._conn.commit()


	def update_output_channel(self, server_id: str, output_channel: str) -> None:
		query = "UPDATE servers SET output_channel = %s WHERE id = %s"

		self._cur.execute(query, [output_channel, server_id])
		self._conn.commit()


	def update_exchanges(self, server_id: str, exchanges: str) -> None:
		query = "UPDATE servers SET exchanges = %s WHERE id = %s"

		self._cur.execute(query, [exchanges, server_id])


	def add_exchanges(self, server_id: str, new_exchanges: list) -> None:
		exchanges = self.get_exchanges(server_id)
		
		if exchanges:
			exchanges += " " + 	" ".join(new_exchanges)

		else:
			exchanges = " ".join(new_exchanges)

		# remove duplicates
		exchanges = set(exchanges.split(" "))
		exchanges = " ".join(exchanges)

		self.update_exchanges(server_id, exchanges)


	def remove_exchanges(self, server_id: str, removed_exchanges: list) -> None:
		exchanges = self.get_exchanges(server_id)

		if exchanges:
			exchanges = [ex for ex in exchanges if ex not in removed_exchanges]
			self.update_exchanges(server_id, exchanges)


	def number_update_servers(self) -> None:
		query = "SELECT Count(*) FROM servers WHERE output_channel IS NOT NULL"

		self._cur.execute(query)

		return self._cur.fetchone()[0]
		