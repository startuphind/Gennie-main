import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Any


class TodoManager:
    def __init__(self, db_path: str = 'todo.db'):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date TIMESTAMP,
                categories TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def execute_sql_query(self, query: str, params: Optional[Any] = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        results = cursor.fetchall()
        conn.close()
        return results
