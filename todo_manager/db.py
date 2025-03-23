from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

DATABASE_URL = "sqlite:///file_manager.db"

# Create an SQLAlchemy engine with a connection pool
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def get_db_connection():
    conn = engine.connect()
    return conn


import time
from sqlalchemy.exc import OperationalError

def retry_on_lock(func):
    def wrapper(*args, **kwargs):
        retries = 5
        delay = 2
        while retries > 0:
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                if 'database is locked' in str(e):
                    retries -= 1
                    print(f"Database is locked. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise
        raise OperationalError("Failed to acquire database lock after multiple retries")
    return wrapper

def init_db():
    conn = get_db_connection()
    cursor = conn.connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            hash TEXT,
            url TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS directories (
            id TEXT PRIMARY KEY,
            path TEXT UNIQUE,
            parent TEXT,
            timestamp TEXT
        )
    ''')
    conn.connection.commit()
    conn.close()

init_db()