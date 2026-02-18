import os
import sqlite3

def is_postgres() -> bool:
    return bool(os.getenv("DATABASE_URL"))

def connect():
    if is_postgres():
        import psycopg2
        from psycopg2.extras import RealDictCursor
        db_url = os.getenv("DATABASE_URL", "").strip()
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

    conn = sqlite3.connect("interns.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(r):
    if r is None:
        return None
    if isinstance(r, dict):
        return r
    return dict(r)

def ph():
    return "%s" if is_postgres() else "?"

def init_db():
    conn = connect()
    cur = conn.cursor()

    if is_postgres():
        cur.execute("""
        CREATE TABLE IF NOT EXISTS interns(
            id_info TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            learning_skill TEXT,
            working_on_project TEXT,
            progress_month1 TEXT,
            knowledge_gained TEXT,
            progress_rating_num DOUBLE PRECISION,
            status TEXT DEFAULT 'pending'
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL, -- admin|supervisor|intern
            password_hash TEXT NOT NULL,
            intern_id_info TEXT NULL,
            supervisor_user_id INTEGER NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'todo', -- todo|in_progress|done
            due_date TIMESTAMP NULL,
            assigned_to_user_id INTEGER NOT NULL,
            assigned_by_user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS task_updates(
            id SERIAL PRIMARY KEY,
            task_id INTEGER NOT NULL,
            intern_user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS supervisor_feedback(
            id SERIAL PRIMARY KEY,
            intern_id_info TEXT NOT NULL,
            supervisor_name TEXT,
            note TEXT,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS interns(
            id_info TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            learning_skill TEXT,
            working_on_project TEXT,
            progress_month1 TEXT,
            knowledge_gained TEXT,
            progress_rating_num REAL,
            status TEXT DEFAULT 'pending'
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            intern_id_info TEXT,
            supervisor_user_id INTEGER,
            active INTEGER DEFAULT 1,
            created_at TEXT
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'todo',
            due_date TEXT,
            assigned_to_user_id INTEGER NOT NULL,
            assigned_by_user_id INTEGER NOT NULL,
            created_at TEXT
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS task_updates(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            intern_user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS supervisor_feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id_info TEXT NOT NULL,
            supervisor_name TEXT,
            note TEXT,
            rating INTEGER,
            created_at TEXT
        );
        """)

    conn.commit()
    conn.close()
