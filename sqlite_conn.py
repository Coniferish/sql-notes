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

    # -- These params don't have to be used, but are required for context manager --
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
        # -- Immediately establish connection --
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
        return cursor


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
        self._conn = None

    def _ensure_connection(self):
        """Quietly ensure the connection is established."""
        if not self._conn:
            self._conn = sqlite3.connect(self.db_path)

    def _get_cursor(self) -> sqlite3.Cursor:
        if not self._conn:
            raise RuntimeError("Database connection is not established.")
        return self._conn.cursor()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, query: str, params: tuple[str, ...]):
        self._ensure_connection()  # -- Connects only when needed (when 'execute' is called) --
        cursor = self._get_cursor()
        cursor.execute(query, params)
        assert self._conn is not None
        self._conn.commit()
        return cursor


class SQLiteConnectionSingleton:
    """
    Singleton Pattern - ensures only one connection instance exists and has lazy initialization.

    The singleton pattern restricts the instantiation of a class to one "single" instance. In this
    case, it ensures that only one SQLiteConnectionSingleton instance is created. Within this class,
    we're also restricting access to only a single db connection (_conn). Below in the
    SQLiteConnectionMultition class, we allow multiple instances of the class, but each instance
    must have a unique configuration (in that case, a single instance for each db_path), so it's not a true
    singleton. In the SQLiteConnectionPool class, we allow multiple connections to the same
    database, but we control the number of connections to prevent overwhelming the database
    through a singleton-like pattern (it's actually also a multition) by restricting instantiation
    to a single connection pool. So while multiple connections can exist, they are all managed by
    the single pool instance.

    Pros:
    - Guarantees single connection across application
    - Prevents overhead from multiple connections
    - Simple global access

    Cons:
    - Can create bottlenecks in multi-threaded applications
    - Harder to test and mock
    - Global state can make debugging difficult
    - Not suitable for applications needing multiple databases

    Best for: Simple applications with a single database and minimal concurrency.

    Important notes particular to python:
    - Python's module system loads each module only once, which can itself act as a singleton.
      If all you need is shared state, a module-level variable or function may be sufficient.
    - You could use a private class (`_PrivateClass`) at the module level, but you'd have to
      hard-code or otherwise inject the db_path early.
    """

    # -- Class variables to hold the singleton instance and connection --
    _instance: "SQLiteConnectionSingleton | None" = None
    _conn: "sqlite3.Connection | None" = None

    def __new__(cls, db_path: str):
        """__new__ is used to control/return an instance of the class (instantiation) and is called before __init__.

        Below is a common pattern for singletons in Python.
        The first call to __new__ will create the instance as normal, but subsequent calls will return the
        same instance since _instance is a class variable that holds the singleton instance.
        """
        if cls._instance is None:
            # -- Create a new instance of the class (super is the object class in this case) --
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str):
        """Initialize the singleton instance with the database path.

        Even though __new__ ensures a singleton and is run before this, __init__ still runs on
        every instantiation, even if the singleton already exists.
        We use a class variable guard (_initialized) to avoid re-initializing attributes (i.e. db_path).
        """
        # -- Check if an instance has already been initialized to avoid re-initialization --
        if not getattr(self, "_initialized", False):
            self.db_path = db_path
            # -- _initialized is set on the instance and not the class because setting it on the
            # -- class would affect all instances, which would conflict with resetting the singleton
            # -- during tests. This way it goes away when _instance is reset.
            self._initialized = True
        else:
            if self.db_path != db_path:
                raise ValueError(
                    f"Singleton already initialized with db_path='{self.db_path}'."
                    f" Cannot reinitialize with '{db_path}'"
                )
            logging.debug(
                f"SQLiteConnectionSingleton already initialized with db_path='{self.db_path}'."
                " Using existing instance."
            )

    def _ensure_connection(self):
        """Quietly ensure the connection is established."""
        if not self._conn:
            self._conn = sqlite3.connect(self.db_path)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)

    def execute(self, query: str, params: tuple[str, ...] = ()) -> sqlite3.Cursor:
        self._ensure_connection()
        assert self._conn is not None, "Connection not established."
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        self._conn.commit()
        return cursor

    @classmethod
    def reset(cls):
        cls._instance = None
        cls._conn = None


class SQLiteConnectionMultition:
    """Multition Pattern - allows multiple instances with different configurations.

    Instead of allowing only one instance, this implementation maintains a registry of instances
    based on configuration keys (db_path), allowing one instance per unique configuration key. This is
    useful when you need multiple database connections but want to reuse connections for the same database.

    Pros:
    - Reuses instances for the same configuration (prevents duplicate connections)
    - Useful for applications needing multiple databases
    - More flexible than Singleton while still controlling instance creation

    Cons:
    - More complex than Singleton
    - Need to manage multiple instances
    - Can lead to resource exhaustion if not managed properly
    - Memory usage grows with number of unique configurations

    Best for: Applications needing multiple database connections with different settings,
    such as microservices connecting to different databases or applications with
    separate databases for different features.

    Usage:
        # These will be the same instance
        db1 = SQLiteConnectionMultition("users.db")
        db1_again = SQLiteConnectionMultition("users.db")

        # This will be a different instance
        db2 = SQLiteConnectionMultition("products.db")
    """

    # -- This dictionary persists across all instances and maintains the multition registry --
    _instances: dict[str, "SQLiteConnectionMultition"] = {}

    def __new__(cls, db_path: str):
        """Controls instance creation - returns existing instance if one exists for this db_path."""
        # -- Check if we already have an instance for this db_path --
        if db_path not in cls._instances:
            # -- Create new instance if none exists for this db_path --
            cls._instances[db_path] = super().__new__(cls)
        # -- Return the instance (either newly created or existing) --
        return cls._instances[db_path]

    def __init__(self, db_path: str):
        """Initialize the multition instance with database path.

        Like the Singleton pattern, __init__ runs every time the class is instantiated,
        even if we return an existing instance from __new__. We use the _initialized
        flag to prevent re-initialization of existing instances.
        """
        # -- Only initialize if this instance hasn't been initialized yet --
        if not getattr(self, "_initialized", False):
            self.db_path = db_path
            # -- Store connection as private attribute, initially None (lazy connection).
            # -- This follows the lazy connection pattern - we don't connect until needed.
            self._conn: sqlite3.Connection | None = None
            # -- Mark as initialized to prevent re-initialization --
            self._initialized = True

    def _ensure_connection(self):
        """Quietly ensure the connection is established (lazy connection pattern)."""
        if not self._conn:
            self._conn = sqlite3.connect(self.db_path)

    def close(self):
        """Close the database connection and reset the connection attribute.

        Note: This closes the connection but doesn't remove the instance from
        the multition registry. The instance can be reconnected by calling
        execute() again.
        """
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, query: str, params: tuple[str, ...] = ()) -> sqlite3.Cursor:
        """Execute a SQL query with parameters.

        This method combines lazy connection establishment with query execution.
        If no connection exists, it will be created automatically.
        """
        self._ensure_connection()
        assert self._conn is not None, "Connection not established."
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        self._conn.commit()
        return cursor

    @classmethod
    def reset(cls):
        """Reset all instances for testing purposes.

        This method is primarily for testing - it closes all connections and
        clears the instance registry, allowing fresh instances to be created.
        """
        # -- Close all existing connections --
        for instance in cls._instances.values():
            instance.close()
        # -- Clear the instance registry --
        cls._instances.clear()


class SQLiteConnectionPool:
    """Connection Pool Pattern with Singleton-per-Database (multiton pattern).

    A connection pool maintains a collection of database connections that can be
    reused across multiple operations, leveraging a database's ability to handle concurrent
    connections (the specifications of this depends on the database and how it's being used (reads
    vs writes)). This implementation uses a quasi-singleton pattern per database path, ensuring that
    multiple requests for the same database share the same *connection pool*, preventing
    proliferation of connections.

    This pattern is especially useful for multi-threaded applications where multiple
    threads need database access simultaneously. SQLite supports concurrent reads
    but only one write at a time, so pooling helps manage this.

    Note: See the docstring in SQLiteConnectionSingleton for more background.

    Note that because we are creating a pool of live connections, we also need to manage their
    lifecycle carefully. Connections should be returned to the pool when no longer needed or there
    is an error, and the pool should be closed properly to release resources. To facilitate this,
    we use a context manager (PooledConnection) that automatically returns connections to the pool
    when done. `PooledConnection` encapsulates this behavior.

    Pros:
    - Better performance for multi-threaded applications
    - Reuses connections instead of creating new ones (reduces overhead)
    - Can limit the number of concurrent connections (prevents resource exhaustion)
    - Handles connection lifecycle automatically
    - Provides thread-safe access to database connections
    - Reduces connection setup/teardown overhead
    - Prevents multiple pools for the same database (singleton per db_path)

    Cons:
    - More complex implementation
    - Need to handle thread safety carefully
    - Memory overhead of maintaining multiple connections
    - Potential for connection leaks if not managed properly

    Best for: Multi-threaded applications with frequent database access, web servers,
    or applications with burst database activity patterns.

    Note: SQLite has some limitations with concurrent writes, so this pool is most
    beneficial for read-heavy workloads or when you need to manage connection limits.

    Usage:
        # These will return the same pool instance
        pool1 = SQLiteConnectionPool("database.db", pool_size=5)
        pool2 = SQLiteConnectionPool("database.db", pool_size=3)  # pool_size ignored, uses existing

        # Get a connection from the pool
        with pool1.get_connection() as conn:
            conn.execute("SELECT * FROM users", ())
    """

    # -- Class variable to store pool instances keyed by db_path --
    _instances: dict[str, "SQLiteConnectionPool"] = {}

    def __new__(cls, db_path: str, pool_size: int = 5):
        """Controls instance creation - returns existing pool if one exists for this db_path.

        This implements a singleton pattern per database path, ensuring that
        multiple requests for pools to the same database return the same pool instance.

        Note: pool_size is not used because we implement singleton-per-database,
        meaning the first pool created for a database determines its configuration. Subsequent
        initializations with different pool_size values will be ignored. But it's included to match
        the constructor signature.
        """
        # -- Check if we already have a pool for this db_path --
        if db_path not in cls._instances:
            # -- Create new pool instance if none exists for this db_path --
            cls._instances[db_path] = super().__new__(cls)
        # -- Return the pool instance (either newly created or existing) --
        return cls._instances[db_path]

    def __init__(self, db_path: str, pool_size: int = 5):
        """Initialize the connection pool.

        Like the Singleton pattern, __init__ runs every time the class is instantiated,
        even if we return an existing instance from __new__. We use the _initialized
        flag to prevent re-initialization of existing pools.

        Args:
            db_path: Path to the SQLite database file
            pool_size: Maximum number of connections to maintain in the pool
        """
        # -- Only initialize if this pool hasn't been initialized yet --
        if not getattr(self, "_initialized", False):
            # -- In production code these would be imported at module level --
            import threading
            import queue

            self.db_path = db_path
            self.pool_size = pool_size

            # -- Use a thread-safe queue to store available connections.
            # -- queue.Queue is thread-safe and blocks when empty (get()) or full (put()).
            self._free_connections: queue.Queue[sqlite3.Connection] = queue.Queue(
                maxsize=pool_size
            )

            # -- Track of all connections for cleanup --
            self._all_connections: list[sqlite3.Connection] = []

            # -- Thread lock for protecting connection creation.
            # -- This ensures only one thread creates connections at a time.
            self._lock = threading.Lock()

            # -- Pre-populate the pool with initial connections --
            self._initialize_pool()

            # -- Mark as initialized to prevent re-initialization --
            self._initialized = True
        else:
            # -- Pool already exists for this db_path, optionally warn about ignored parameters --
            if self.pool_size != pool_size:
                logger.debug(
                    f"SQLiteConnectionPool already initialized for '{db_path}' with pool_size={self.pool_size}. "
                    f"Ignoring new pool_size={pool_size}"
                )

    def _initialize_pool(self):
        """Pre-populate the pool with initial connections.

        This creates the initial set of connections when the pool is created,
        so they're ready for immediate use.
        """
        for _ in range(self.pool_size):
            # -- check_same_thread=False allows connection to be used across threads.
            # -- By default, SQLite connections can only be used in the thread that created them.
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._all_connections.append(conn)
            self._free_connections.put(conn)

    def borrow_connection(self) -> sqlite3.Connection:
        """Borrow a connection from the pool.

        This method blocks until a connection becomes available.
        Used internally by PooledConnection context manager.

        Note: This should not be a public method, but with this current pattern, it can't be made
        private because it needs to be called from the PooledConnection context manager. A better
        pattern would be to make this a private method and use a Composition pattern.
        https://claude.ai/chat/3ae4d343-795f-450d-97ea-8cf440e0332d
        """
        # -- This will block if no connections are available --
        return self._free_connections.get()

    def close_all(self):
        """Close all connections in the pool.

        This should be called when shutting down the application to properly
        clean up all database connections.
        """
        # -- Close all connections we've created --
        for conn in self._all_connections:
            conn.close()

        # -- Clear the collections --
        self._all_connections.clear()

        # -- Empty the queue of any remaining connections --
        while not self._free_connections.empty():
            try:
                self._free_connections.get_nowait()
            # -- Not best practice, but we want to avoid blocking here --
            except Exception:
                break

    def execute(self, query: str, params: tuple[str, ...] = ()) -> sqlite3.Cursor:
        """Execute a query using a connection from the pool.

        This is a convenience method that borrows a connection, executes the query,
        and returns the connection to the pool automatically.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor

    def get_connection(self):
        """Get a connection from the pool.

        Returns a PooledConnection context manager that automatically returns
        the connection to the pool when done.

        This method blocks if no connections are available until one is returned.
        """
        return PooledConnection(self)

    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool.

        Used internally by PooledConnection context manager.
        """
        # -- Put the connection back in the available queue --
        self._free_connections.put(conn)

    @classmethod
    def reset(cls):
        """Reset all pool instances for testing purposes.

        This method is primarily for testing - it closes all connections in all pools
        and clears the instance registry, allowing fresh pools to be created.
        """
        # -- Close all connections in all pools --
        for pool in cls._instances.values():
            pool.close_all()
        # -- Clear the instance registry --
        cls._instances.clear()


class PooledConnection:
    """Context manager for managing the lifecycle of a single borrowed connection.

    This context manager ensures that connections borrowed from the pool
    are always returned, even if an exception occurs during database operations.

    This follows the RAII (Resource Acquisition Is Initialization) pattern,
    ensuring proper resource cleanup.
    """

    def __init__(self, pool: SQLiteConnectionPool):
        """Initialize with a reference to the connection pool."""
        self.pool = pool
        self.conn: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        """Borrow a connection from the pool when entering the context."""
        # -- Get a connection from the pool (this may block if none available) --
        self.conn = self.pool.borrow_connection()
        return self.conn

    # -- These params don't have to be used, but are required for context manager --
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        """Return the connection to the pool when exiting the context.

        This is called automatically when exiting the 'with' block,
        even if an exception occurred.
        """
        if self.conn:
            # -- Return the connection to the pool for reuse --
            self.pool.return_connection(self.conn)
            self.conn = None

class SQLiteConnectionFactory:
    pass


class SQLiteConnectionDependencyInjection:
    pass


class SQLiteConnectionDecorator:
    pass
