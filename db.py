import os
import sqlite3

def is_postgres() -> bool:
    return bool(os.getenv("DATABASE_URL"))

def ph() -> str:
    """SQL placeholder depending on DB driver."""
    return "%s" if is_postgres() else "?"

def connect():
    """
    - Railway Postgres: uses DATABASE_URL
    - Local: sqlite interns.db
    """
    if is_postgres():
        import psycopg2
        from psycopg2.extras import RealDictCursor

        db_url = os.getenv("DATABASE_URL", "").strip()
        # Some providers still output postgres:// which psycopg2 accepts, but we normalize anyway
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

    conn = sqlite3.connect("interns.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # ✅ SQLite: foreign keys are OFF by default
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def row_to_dict(r):
    if r is None:
        return None
    if isinstance(r, dict):
        return r
    return dict(r)

def init_db():
    conn = connect()
    cur = conn.cursor()

    if is_postgres():
        # -------------------- INTERNS --------------------
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
            status TEXT DEFAULT 'pending'  -- pending|active|completed
        );
        """)

        # -------------------- USERS --------------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id BIGSERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,    -- use email as username (recommended)
            full_name TEXT,
            role TEXT NOT NULL,              -- admin|supervisor|intern
            password_hash TEXT NOT NULL,
            intern_id_info TEXT NULL REFERENCES interns(id_info) ON DELETE SET NULL,
            supervisor_user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # -------------------- TASKS --------------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'todo',         -- todo|in_progress|done
            due_date TIMESTAMP NULL,
            assigned_to_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            assigned_by_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to_user_id);
        """)

        # -------------------- TASK UPDATES --------------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS task_updates(
            id BIGSERIAL PRIMARY KEY,
            task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            intern_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # -------------------- SUPERVISOR FEEDBACK --------------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS supervisor_feedback(
            id BIGSERIAL PRIMARY KEY,
            intern_id_info TEXT NOT NULL REFERENCES interns(id_info) ON DELETE CASCADE,
            supervisor_name TEXT,
            note TEXT,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # -------------------- RAG RECORDS (MISSING IN YOUR FILE) --------------------
        cur.execute("""
        CREATE TABLE IF NOT EXISTS rag_records(
            id BIGSERIAL PRIMARY KEY,
            intern_id_info TEXT NOT NULL REFERENCES interns(id_info) ON DELETE CASCADE,
            record_type TEXT DEFAULT 'dataset',
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_intern ON rag_records(intern_id_info);
        """)

    else:
        # -------------------- SQLITE VERSION --------------------
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
            intern_id_info TEXT REFERENCES interns(id_info) ON DELETE SET NULL,
            supervisor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'todo',
            due_date TEXT,
            assigned_to_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            assigned_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to_user_id);
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS task_updates(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            intern_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS supervisor_feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id_info TEXT NOT NULL REFERENCES interns(id_info) ON DELETE CASCADE,
            supervisor_name TEXT,
            note TEXT,
            rating INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)

        # ✅ add missing rag_records
        cur.execute("""
        CREATE TABLE IF NOT EXISTS rag_records(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id_info TEXT NOT NULL REFERENCES interns(id_info) ON DELETE CASCADE,
            record_type TEXT DEFAULT 'dataset',
            text TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_intern ON rag_records(intern_id_info);
        """)

    conn.commit()
    conn.close()
