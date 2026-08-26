import sqlite3
import pandas as pd
from contextlib import closing

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    # Establish Connection
    def _get_connection(self):
        """Create SQLite3 Connection to db
        """
        return closing(sqlite3.connect(self.db_path))

    def query_df(self, query: str, params: dict | tuple | list | None = None) -> pd.DataFrame:
        """Executes a Select SQL query and returns pandas DataFrame.

        Args:
            query (str): SELECT SQL query
            params (dict | tuple | list | None, optional): Optional Parameters for SQL Query. Defaults to None.

        Returns:
            DataFrame: SQL Query Results
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def execute(self, query: str, params: dict | tuple | list | None = ()):
        """Executes a single INSERT, UPDATE, DELETE, CREATE query and commits.

        Args:
            query (str): single INSERT, UPDATE, or DELETE query
            params (dict | tuple | list | None, optional): Optional Parameters for SQL Query. Defaults to None.

        Returns:
            str: Rowcount from the execution
        """
        with self._get_connection() as conn:
            with conn: # Automatically manage transactions
                cursor = conn.cursor()
                cursor.execute(query,params)
                return cursor.rowcount

    def execute_many(self, query: str, params: dict | tuple | list | None = None):
        """Executes a Bulk INSERTS or UPDATE.

        Args:
            query (str): Bulk INSERT or UPDATE query
            params (dict | tuple | list | None, optional): Optional Parameters for SQL Query. Defaults to None.

        Returns:
            str: Rowcount from the execution
        """
        with self._get_connection() as conn:
            with conn: # Automatically manage transactions
                cursor = conn.cursor()
                cursor.execute_many(query,params)
                return cursor.rowcount

    def table_exists(self, tablename: str):
        """Checks if table exists in database

        Args:
            tablename (str): Table to check if exists

        Returns:
            bool: Table exists in DB
        """
        params = {"tablename":tablename}
        query = '''
                SELECT name 
                FROM sqlite_master
                where name = :tablename
                '''
        with self._get_connection() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query,params)
                return True if len(cursor.fetchall()) == 1 else False

    def truncate_table(self, table_name: str):
        """Truncates table using DELETE

        Args:
            table_name (str): Table to truncate
        """
        query = f"DELETE FROM {table_name};"
        return self.execute(query)


