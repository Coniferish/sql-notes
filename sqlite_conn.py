import sqlite3
from typing import Any


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
        Initialize a SQLite connection immediately (Eager Connection Pattern).

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
    def __init__(self, db_path: str):
        """
        Initialize a SQLite connection without connecting immediately (Lazy Pattern).

        This pattern defers connection establishment until explicitly requested via connect(). It is
        an improvement over the eager connection pattern by allowing more control over when the
        connection is made, but still requires the user to manage the connection lifecycle and will
        not inherently prevent resource leaks or avoid "too many connections" errors.

        Pros:
        - More control over when connections are established
        - Can handle connection failures more gracefully by checking connection state
        - Allows for connection pooling or reconnection logic

        Cons:
        - Requires explicit connect() call before use
        - Potential for runtime errors if connect() is forgotten
        - Need to check connection state in methods

        Best for: Applications that need fine-grained control over connection lifecycle,
        or when connections might not be needed immediately.
        """
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def connect(self):
        if self.conn is not None:
            raise Warning("A connection is already established.")
        else:
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
        cursor = self._get_cursor()
        cursor.execute(query, params)
        if self.conn is None:
            raise RuntimeError("Database connection is not established.")
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
