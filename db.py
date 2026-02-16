import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "interns.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS interns(
        id_info TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        learning_skill TEXT,
        project TEXT,
        progress TEXT,
        knowledge TEXT,
        rating REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rag_records(
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        intern_id TEXT,
        text TEXT
    )
    """)

    conn.commit()
    conn.close()
