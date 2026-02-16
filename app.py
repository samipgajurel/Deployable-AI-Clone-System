import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from db import init_db, connect
from ingest import run_ingest
from ai_clone import generate_ai_clone

app = FastAPI(title="Deployable AI Clone System")

@app.on_event("startup")
def startup():
    init_db()

class FeedbackIn(BaseModel):
    supervisor_name: str = "Samip Gajurel"
    note: str
    rating: Optional[int] = None  # 1-5

@app.get("/")
def root():
    return {
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

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

# ✅ List interns
@app.get("/interns")
def list_interns():
    conn = connect()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT id_info, intern_no, name, email, learning_skill, status, working_on_project
        FROM interns
        ORDER BY start_date, intern_no
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ✅ Intern detail
@app.get("/interns/{intern_id}")
def intern_detail(intern_id: str):
    conn = connect()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM interns WHERE id_info=?", (intern_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Intern not found")
    return dict(row)

# ✅ Save supervisor feedback
@app.post("/interns/{intern_id}/feedback")
def add_feedback(intern_id: str, body: FeedbackIn):
    conn = connect()
    cur = conn.cursor()

    # ensure intern exists
    chk = cur.execute("SELECT id_info FROM interns WHERE id_info=?", (intern_id,)).fetchone()
    if not chk:
        conn.close()
        raise HTTPException(status_code=404, detail="Intern not found")

    if os.getenv("DATABASE_URL"):
        cur.execute("""
            INSERT INTO supervisor_feedback(intern_id_info, supervisor_name, note, rating)
            VALUES (%s,%s,%s,%s)
        """, (intern_id, body.supervisor_name, body.note, body.rating))
    else:
        cur.execute("""
            INSERT INTO supervisor_feedback(intern_id_info, supervisor_name, note, rating, created_at)
            VALUES (?,?,?,?,datetime('now'))
        """, (intern_id, body.supervisor_name, body.note, body.rating))

    conn.commit()
    conn.close()
    return {"message": "Feedback saved"}

# ✅ AI clone: saves feedback + returns AI output (RAG + history)
@app.post("/interns/{intern_id}/ai-clone")
def ai_clone(intern_id: str, body: FeedbackIn):
    # save feedback first
    add_feedback(intern_id, body)
    # generate result
    return generate_ai_clone(intern_id, body.note)
