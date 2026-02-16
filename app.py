import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional

from db import init_db, connect, is_postgres
from ingest import run_ingest
from ai_clone import generate_ai_clone

app = FastAPI(title="Deployable AI Clone System")

@app.on_event("startup")
def startup():
    init_db()

# ---------- Helpers ----------
def placeholder():
    return "%s" if is_postgres() else "?"

def row_to_dict(row):
    """Works for sqlite Row, psycopg2 RealDictCursor, or tuple fallback."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        # tuple fallback (should not happen if RealDictCursor is used)
        return {"data": row}

# ---------- Schemas ----------
class FeedbackIn(BaseModel):
    supervisor_name: str = "Samip Gajurel"
    note: str
    rating: Optional[int] = None  # 1-5

# ---------- Routes ----------
@app.get("/")
def root():
    return {"status": "running", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"ok": True}

# ✅ Upload dataset (CSV) and rebuild DB + RAG
@app.post("/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "interns.csv")

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        n = run_ingest(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Dataset uploaded + ingested + RAG rebuilt", "interns_imported": n}

# ✅ List interns (matches your ingest schema)
@app.get("/interns")
def list_interns():
    ph = placeholder()
    conn = connect()
    cur = conn.cursor()

    # Your ingest inserts columns:
    # id_info, name, email, learning_skill, working_on_project, progress_month1, knowledge_gained, progress_rating_num
    cur.execute("""
        SELECT id_info, name, email, learning_skill, working_on_project,
               progress_month1, knowledge_gained, progress_rating_num
        FROM interns
        ORDER BY id_info
    """)
    rows = cur.fetchall()
    conn.close()

    # rows may already be dicts (RealDictCursor) or sqlite Rows
    return [row_to_dict(r) for r in rows]

# ✅ Intern detail
@app.get("/interns/{intern_id}")
def intern_detail(intern_id: str):
    ph = placeholder()
    conn = connect()
    cur = conn.cursor()

    cur.execute(f"SELECT * FROM interns WHERE id_info={ph}", (intern_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Intern not found")

    return row_to_dict(row)

# ✅ Save supervisor feedback
@app.post("/interns/{intern_id}/feedback")
def add_feedback(intern_id: str, body: FeedbackIn):
    ph = placeholder()
    conn = connect()
    cur = conn.cursor()

    # ensure intern exists
    cur.execute(f"SELECT id_info FROM interns WHERE id_info={ph}", (intern_id,))
    chk = cur.fetchone()
    if not chk:
        conn.close()
        raise HTTPException(status_code=404, detail="Intern not found")

    if is_postgres():
        cur.execute(f"""
            INSERT INTO supervisor_feedback(intern_id_info, supervisor_name, note, rating)
            VALUES ({ph},{ph},{ph},{ph})
        """, (intern_id, body.supervisor_name, body.note, body.rating))
    else:
        cur.execute(f"""
            INSERT INTO supervisor_feedback(intern_id_info, supervisor_name, note, rating, created_at)
            VALUES ({ph},{ph},{ph},{ph},datetime('now'))
        """, (intern_id, body.supervisor_name, body.note, body.rating))

    conn.commit()
    conn.close()
    return {"message": "Feedback saved"}

# ✅ AI clone: saves feedback + returns AI output (RAG + history)
@app.post("/interns/{intern_id}/ai-clone")
def ai_clone(intern_id: str, body: FeedbackIn):
    # store feedback
    add_feedback(intern_id, body)

    # generate AI response (make sure ai_clone.py uses correct placeholders too)
    try:
        result = generate_ai_clone(intern_id, body.note)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI clone error: {str(e)}")

    return result
