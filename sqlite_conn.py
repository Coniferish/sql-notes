import sqlite3
from typing import Any
import logging


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class SQLiteConnectionContextManager:
    def __init__(self, db_path: str):
        """
        Initialize a SQLite connection using Context Manager Pattern.

        This automatically handles connection lifecycle within a 'with' statement.

        Pros:
        - Automatic resource cleanup guaranteed by Python's context manager protocol
        - Clear scope of database operations within the 'with' block
        - Exception-safe - connection will be closed even if an exception occurs
        - No need to remember to call close() explicitly

        Cons:
        - Connection is short-lived - limited to the 'with' block scope
        - Need to create new context for each database operation session
        - May not be suitable for long-running database sessions

        Best for: Well-defined database operation sessions where you want guaranteed
        cleanup and clear resource management boundaries.

        Usage:
            with SQLiteConnection("database.db") as db:
                db.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        """
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self

    # -- These params don't have to be used, but are required for context manager
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, query: str, params: tuple[str, ...] = ()):
        """
        Executes a SQL query with the given parameters.

        See more about using params/placeholders to bind values in SQL queries here:
        https://docs.python.org/3/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries
        """
        if not self.conn:
            raise RuntimeError("Connection not established.")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()


# --- OTHER CONNECTION PATTERNS ---


class SQLiteConnectionEager:
    def __init__(self, db_path: str):
        """
        Initialize a SQLite connection upon initialization (Eager Connection Pattern).

        This pattern establishes the database connection immediately upon object creation.

        Pros:
        - Simple and straightforward
        - Connection is ready to use immediately
        - No separate connect() method

        Cons:
        - May waste resources if the connection isn't used immediately
        - No control over when the connection is established
        - You have to create a new instance to reconnect
        - Harder to handle connection failures gracefully
        - Can lead to "too many connections" errors in multi-threaded applications

        Best for: Simple scripts or applications with immediate database usage.
        """
        self.db_path = db_path
        # -- Immediately establish connection:
        self.conn: sqlite3.Connection | None = sqlite3.connect(self.db_path)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, query: str, params: tuple[str, ...]):
        if not self.conn:
            raise RuntimeError("Connection not established.")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()


class SQLiteConnectionLazy:
    """Truly Lazy Pattern - connects only when execute() is called.

    Pros:
    - Connection is established only when needed, helping reduce connection overhead

    Cons:
    - Need to check/establish connection in class methods

    Best for: Applications with infrequent database access or where connection overhead is a concern.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def _ensure_connection(self):
        """Quietly ensure the connection is established."""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)

    def _get_cursor(self) -> sqlite3.Cursor:
        if not self.conn:
            raise RuntimeError("Database connection is not established.")
        return self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, query: str, params: tuple[str, ...]):
        self._ensure_connection()  # Connects only when needed (when 'execute' is called)
        cursor = self._get_cursor()
        cursor.execute(query, params)
        assert self.conn is not None
        self.conn.commit()


class SQLiteConnectionSingleton:
    """
    Singleton Pattern - ensures only one connection instance exists.

    Pros:
    - Guarantees single connection across application
    - Prevents multiple connection overhead
    - Simple global access

    Cons:
    - Can create bottlenecks in multi-threaded applications
    - Harder to test and mock
    - Global state can make debugging difficult
    - Not suitable for applications needing multiple databases

    Best for: Simple applications with single database and minimal concurrency.
    """

    pass


class SQLiteConnectionPool:
    """
    Connection Pool Pattern - manages multiple connections for concurrent access.

    Pros:
    - Better performance for multi-threaded applications
    - Reuses connections instead of creating new ones
    - Can limit the number of concurrent connections
    - Handles connection lifecycle automatically

    Cons:
    - More complex implementation
    - Additional overhead for simple applications
    - Need to handle thread safety

    Best for: Multi-threaded applications with frequent database access.
    """

    pass
