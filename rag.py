from db import connect

def retrieve(intern_id):
    conn = connect()
    cur = conn.cursor()

    rows = cur.execute("SELECT text FROM rag_records WHERE intern_id=?",(intern_id,)).fetchall()
    conn.close()

    return [r["text"] for r in rows]
