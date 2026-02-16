from db import connect

def retrieve(intern_id_info: str, top_k: int = 8):
    conn = connect()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT record_type, text, created_at FROM rag_records WHERE intern_id_info=? ORDER BY record_id DESC",
        (intern_id_info,)
    ).fetchall()
    conn.close()

    # Works in both DBs because db.py returns row dict-like objects for Postgres,
    # and sqlite row supports dict-like indexing.
    out = []
    for r in rows[:top_k]:
        out.append({
            "type": r["record_type"],
            "text": r["text"],
            "created_at": str(r["created_at"])
        })
    return out
