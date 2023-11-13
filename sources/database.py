import sqlite3 as _sqlite3, json as _json
from typing import Union as _Union, Any as _Any

from .common.developerconfig import DATABASE_FILE

database_file = DATABASE_FILE

__all__ = [
    "DGDatabaseSession"
]
class DGDatabaseSession:
    """
        Handles connection between the server and discord client.
    """

    def __enter__(self):
        return self
    
    def __exit__(self, type_, value_, traceback_):
        self.database.commit()
        self.cursor.close() if self.cursor else None
        self.database.close()
    
    def __init__(self):
        
        """
            Handles connection between the server and discord client.
        """

        
        self.database_file = database_file
        self.database: _sqlite3.Connection = _sqlite3.connect(database_file, timeout=60)
        self.cursor: _Union[_sqlite3.Cursor, None] = self.database.cursor()

    def check(self) -> bool:
        try:
            self._exec_db_command("SELECT * FROM history")
            self._exec_db_command("SELECT * FROM model_rules")
            self._exec_db_command("SELECT * FROM guild_configs")
            return True
        except _sqlite3.OperationalError:
            return False

    def _exec_db_command(self, query: str, args: tuple=()) -> list[_Any]:
        
        self.cursor = self.database.cursor()

        fetched = self.cursor.execute(query, args).fetchall()

        self.database.commit()
        self.cursor.close()
        self.cursor = None

        return fetched
    
    def init(self) -> None:
        """Creates tables required for normal bot operation."""
        
        self._exec_db_command("CREATE TABLE history (uid TEXT NOT NULL, author_id INTEGER NOT NULL, chat_name VARCHAR(40) NOT NULL, chat_json TEXT NOT NULL, is_private INTEGER CHECK (is_private IN (0,1)))")
        self._exec_db_command("CREATE TABLE model_rules (gid INTEGER NOT NULL UNIQUE, jsontables TEXT NOT NULL)")
        self._exec_db_command("CREATE TABLE guild_configs (gid INTEGER NOT NULL UNIQUE, oid INTEGER NOT NULL, json TEXT NOT NULL)")
    
    def delete(self) -> None:
        """Deletes tables that are needed. This should only be used if there is an error with the database. DGDatabaseSession.init() should be called right after this."""
        self._exec_db_command("DROP TABLE IF EXISTS history")
        self._exec_db_command("DROP TABLE IF EXISTS model_rules")
        self._exec_db_command("DROP TABLE IF EXISTS guild_configs")
    
    def reset(self) -> None:
        """Resets the database contents to default (Zero items) This is shorthand for delete() then init()"""
        self.delete()
        self.init()