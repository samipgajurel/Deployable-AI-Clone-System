import os, io, csv, shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from db import init_db, connect, is_postgres, row_to_dict, ph
from auth import verify_password, create_token, decode_token, hash_password
from ingest import run_ingest
from mailer import send_email, email_enabled

app = FastAPI(title="AI Clone Intern System")

# CORS (so frontend can call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for testing; later restrict to your frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer = HTTPBearer(auto_error=True)

@app.on_event("startup")
def startup():
    init_db()
    ensure_default_admin()

def ensure_default_admin():
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASS", "admin123")

    conn = connect()
    cur = conn.cursor()
    p = ph()

    cur.execute(f"SELECT id FROM users WHERE username={p}", (admin_user,))
    row = cur.fetchone()
    if not row:
        if is_postgres():
            cur.execute("""
              INSERT INTO users(username, full_name, role, password_hash)
              VALUES (%s,%s,'admin',%s)
            """, (admin_user, "System Admin", hash_password(admin_pass)))
        else:
            cur.execute("""
              INSERT INTO users(username, full_name, role, password_hash, created_at)
              VALUES (?,?,?,?,datetime('now'))
            """, (admin_user, "System Admin", "admin", hash_password(admin_pass)))
        conn.commit()
    conn.close()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(401, "Invalid token")

    conn = connect()
    cur = conn.cursor()
    p = ph()
    cur.execute(f"SELECT id, username, full_name, role, intern_id_info, active FROM users WHERE id={p}", (payload["uid"],))
    u = cur.fetchone()
    conn.close()

    if not u:
        raise HTTPException(401, "User not found")

    u = row_to_dict(u)
    if not u.get("active"):
        raise HTTPException(403, "Account disabled")
    return u

def require_role(*roles):
    def guard(u=Depends(get_current_user)):
        if u["role"] not in roles:
            raise HTTPException(403, "Forbidden")
        return u
    return guard

# ---------- Schemas ----------
class LoginIn(BaseModel):
    username: str
    password: str

class CreateSupervisorIn(BaseModel):
    username: str
    full_name: str
    password: str

class StatusUpdate(BaseModel):
    status: str  # pending|active|completed

class TaskCreateIn(BaseModel):
    intern_username: str  # assign by intern username (email/id)
    title: str
    description: Optional[str] = ""
    due_date: Optional[str] = None

class TaskSetStatusIn(BaseModel):
    status: str  # todo|in_progress|done

class TaskUpdateIn(BaseModel):
    message: str

# ---------- Base ----------
@app.get("/")
def root():
    return {"status":"running","docs":"/docs","health":"/health"}

@app.get("/health")
def health():
    return {"ok": True}

# ---------- Auth ----------
@app.post("/auth/login")
def login(body: LoginIn):
    conn = connect()
    cur = conn.cursor()
    p = ph()

    cur.execute(f"SELECT id, username, password_hash, role FROM users WHERE username={p}", (body.username,))
    u = cur.fetchone()
    conn.close()
    if not u:
        raise HTTPException(401, "Invalid credentials")

    u = row_to_dict(u)
    if not verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    token = create_token({"uid": u["id"], "role": u["role"]})
    return {"access_token": token, "role": u["role"]}

@app.get("/auth/me")
def me(u=Depends(require_role("admin","supervisor","intern"))):
    return u

# ---------- Admin ----------
@app.post("/admin/create-supervisor")
def create_supervisor(body: CreateSupervisorIn, admin=Depends(require_role("admin"))):
    conn = connect()
    cur = conn.cursor()
    p = ph()

    cur.execute(f"SELECT id FROM users WHERE username={p}", (body.username,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(400, "Username already exists")

    if is_postgres():
        cur.execute("""
          INSERT INTO users(username, full_name, role, password_hash)
          VALUES (%s,%s,'supervisor',%s)
        """, (body.username, body.full_name, hash_password(body.password)))
    else:
        cur.execute("""
          INSERT INTO users(username, full_name, role, password_hash, created_at)
          VALUES (?,?,?,?,datetime('now'))
        """, (body.username, body.full_name, "supervisor", hash_password(body.password)))

    conn.commit()
    conn.close()
    return {"message":"Supervisor created"}

@app.post("/admin/dataset/upload")
async def upload_dataset(file: UploadFile = File(...), admin=Depends(require_role("admin"))):
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "interns.csv")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    n, creds = run_ingest(path)

    # credentials CSV (copy once & store safely)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["role","username","password","intern_id","name"])
    writer.writeheader()
    for c in creds:
        writer.writerow(c)
    creds_csv = output.getvalue()

    # optional: email the credentials
    sent = 0
    failed = []
    if email_enabled():
        subject = os.getenv("CREDS_EMAIL_SUBJECT", "Intern Login Credentials")
        login_url = os.getenv("FRONTEND_LOGIN_URL", "")
        for c in creds:
            to_email = c["username"] if "@" in c["username"] else ""
            if not to_email:
                continue
            body = f"""
Hello {c['name']},

Your internship portal credentials are ready.

Login page: {login_url if login_url else "(Ask admin for login link)"}
Username: {c['username']}
Password: {c['password']}

Please keep this secure.

Thanks,
Internship Admin
""".strip()
            try:
                send_email(to_email, subject, body)
                sent += 1
            except Exception as e:
                failed.append({"email": to_email, "error": str(e)})

    return {
        "message": "Dataset ingested + intern accounts created",
        "interns_imported": n,
        "credentials_csv": creds_csv,
        "emails_sent": sent,
        "emails_failed": failed[:10]
    }

# ---------- Interns ----------
@app.get("/interns")
def list_interns(u=Depends(require_role("admin","supervisor","intern"))):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
      SELECT id_info, name, email, working_on_project, progress_rating_num, status
      FROM interns
      ORDER BY id_info
    """)
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.get("/interns/{intern_id}")
def intern_detail(intern_id: str, u=Depends(require_role("admin","supervisor","intern"))):
    conn = connect()
    cur = conn.cursor()
    p = ph()
    cur.execute(f"SELECT * FROM interns WHERE id_info={p}", (intern_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        raise HTTPException(404, "Intern not found")
    return row_to_dict(r)

@app.put("/interns/{intern_id}/status")
def update_intern_status(intern_id: str, body: StatusUpdate, u=Depends(require_role("admin","supervisor"))):
    allowed = {"pending","active","completed"}
    status = body.status.strip().lower()
    if status not in allowed:
        raise HTTPException(400, "status must be pending|active|completed")

    conn = connect()
    cur = conn.cursor()
    p = ph()
    cur.execute(f"UPDATE interns SET status={p} WHERE id_info={p}", (status, intern_id))
    if getattr(cur, "rowcount", 0) == 0:
        conn.close()
        raise HTTPException(404, "Intern not found")
    conn.commit()
    conn.close()
    return {"message": f"Status updated to {status}"}

# ---------- Tasks ----------
@app.post("/tasks/create")
def create_task(body: TaskCreateIn, u=Depends(require_role("admin","supervisor"))):
    conn = connect()
    cur = conn.cursor()
    p = ph()

    # find intern user id by username
    cur.execute(f"SELECT id, intern_id_info FROM users WHERE username={p} AND role='intern'", (body.intern_username,))
    intern_user = cur.fetchone()
    if not intern_user:
        conn.close()
        raise HTTPException(404, "Intern user not found (check intern username/email)")

    intern_user = row_to_dict(intern_user)
    intern_user_id = intern_user["id"]
    intern_id_info = intern_user.get("intern_id_info")

    if is_postgres():
        cur.execute("""
          INSERT INTO tasks(title, description, due_date, assigned_to_user_id, assigned_by_user_id)
          VALUES (%s,%s,%s,%s,%s)
        """, (body.title, body.description, body.due_date, intern_user_id, u["id"]))
    else:
        cur.execute("""
          INSERT INTO tasks(title, description, due_date, assigned_to_user_id, assigned_by_user_id, created_at)
          VALUES (?,?,?,?,?,datetime('now'))
        """, (body.title, body.description, body.due_date, intern_user_id, u["id"]))

    # auto-activate intern if pending
    if intern_id_info:
        cur.execute(f"UPDATE interns SET status='active' WHERE id_info={p} AND status='pending'", (intern_id_info,))

    conn.commit()
    conn.close()
    return {"message":"Task created"}

@app.get("/tasks/my")
def my_tasks(u=Depends(require_role("admin","supervisor","intern"))):
    conn = connect()
    cur = conn.cursor()
    p = ph()

    if u["role"] == "intern":
        cur.execute(f"SELECT * FROM tasks WHERE assigned_to_user_id={p} ORDER BY id DESC", (u["id"],))
    else:
        cur.execute(f"SELECT * FROM tasks WHERE assigned_by_user_id={p} ORDER BY id DESC", (u["id"],))

    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.put("/tasks/{task_id}/status")
def set_task_status(task_id: int, body: TaskSetStatusIn, u=Depends(require_role("admin","supervisor","intern"))):
    allowed = {"todo","in_progress","done"}
    status = body.status.strip().lower()
    if status not in allowed:
        raise HTTPException(400, "status must be todo|in_progress|done")

    conn = connect()
    cur = conn.cursor()
    p = ph()

    # interns can only change own task
    if u["role"] == "intern":
        cur.execute(f"SELECT id FROM tasks WHERE id={p} AND assigned_to_user_id={p}", (task_id, u["id"]))
        if not cur.fetchone():
            conn.close()
            raise HTTPException(403, "Not your task")

    cur.execute(f"UPDATE tasks SET status={p} WHERE id={p}", (status, task_id))

    # if intern finished all tasks -> mark completed
    if u["role"] == "intern" and status == "done":
        cur.execute(f"SELECT COUNT(*) AS rem FROM tasks WHERE assigned_to_user_id={p} AND status!='done'", (u["id"],))
        rem_row = cur.fetchone()
        rem = rem_row["rem"] if isinstance(rem_row, dict) else rem_row[0]
        if rem == 0 and u.get("intern_id_info"):
            cur.execute(f"UPDATE interns SET status='completed' WHERE id_info={p}", (u["intern_id_info"],))

    conn.commit()
    conn.close()
    return {"message": f"Task {task_id} status -> {status}"}

@app.post("/tasks/{task_id}/update")
def task_update(task_id: int, body: TaskUpdateIn, u=Depends(require_role("intern"))):
    conn = connect()
    cur = conn.cursor()
    p = ph()

    cur.execute(f"SELECT id FROM tasks WHERE id={p} AND assigned_to_user_id={p}", (task_id, u["id"]))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(403, "Not your task")

    if is_postgres():
        cur.execute("INSERT INTO task_updates(task_id, intern_user_id, message) VALUES (%s,%s,%s)",
                    (task_id, u["id"], body.message))
        cur.execute("UPDATE tasks SET status='in_progress' WHERE id=%s", (task_id,))
    else:
        cur.execute("INSERT INTO task_updates(task_id, intern_user_id, message, created_at) VALUES (?,?,?,datetime('now'))",
                    (task_id, u["id"], body.message))
        cur.execute("UPDATE tasks SET status='in_progress' WHERE id=?", (task_id,))

    conn.commit()
    conn.close()
    return {"message":"Update saved"}

@app.get("/tasks/{task_id}/updates")
def task_updates(task_id: int, u=Depends(require_role("admin","supervisor","intern"))):
    conn = connect()
    cur = conn.cursor()
    p = ph()

    # intern only sees own task updates
    if u["role"] == "intern":
        cur.execute(f"SELECT id FROM tasks WHERE id={p} AND assigned_to_user_id={p}", (task_id, u["id"]))
        if not cur.fetchone():
            conn.close()
            raise HTTPException(403, "Not your task")

    cur.execute(f"SELECT * FROM task_updates WHERE task_id={p} ORDER BY id DESC", (task_id,))
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

# ---------- Analytics (Charts + Stats) ----------
@app.get("/analytics/summary")
def analytics_summary(u=Depends(require_role("admin","supervisor"))):
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM interns")
    r = cur.fetchone()
    total_interns = r["total"] if isinstance(r, dict) else r[0]

    cur.execute("SELECT status, COUNT(*) AS c FROM interns GROUP BY status")
    rows = cur.fetchall()
    status_counts = {rr["status"]: rr["c"] for rr in rows} if (rows and isinstance(rows[0], dict)) else {rr[0]: rr[1] for rr in rows}

    cur.execute("SELECT AVG(progress_rating_num) AS avg_rating FROM interns")
    ar = cur.fetchone()
    avg_rating = ar["avg_rating"] if isinstance(ar, dict) else ar[0]
    avg_rating = float(avg_rating or 0)

    cur.execute("SELECT COUNT(*) AS total_tasks FROM tasks")
    tr = cur.fetchone()
    total_tasks = tr["total_tasks"] if isinstance(tr, dict) else tr[0]

    cur.execute("SELECT status, COUNT(*) AS c FROM tasks GROUP BY status")
    trows = cur.fetchall()
    task_counts = {rr["status"]: rr["c"] for rr in trows} if (trows and isinstance(trows[0], dict)) else {rr[0]: rr[1] for rr in trows}

    conn.close()
    return {
        "total_interns": int(total_interns),
        "status_counts": status_counts,
        "avg_rating": round(avg_rating, 2),
        "total_tasks": int(total_tasks),
        "task_counts": task_counts
    }

@app.get("/analytics/interns/ratings")
def ratings_distribution(u=Depends(require_role("admin","supervisor"))):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
      SELECT CAST(progress_rating_num AS INT) AS r, COUNT(*) AS c
      FROM interns
      GROUP BY CAST(progress_rating_num AS INT)
      ORDER BY r
    """)
    rows = cur.fetchall()
    conn.close()

    out = []
    for rr in rows:
        if isinstance(rr, dict):
            out.append({"rating": int(rr["r"]), "count": int(rr["c"])})
        else:
            out.append({"rating": int(rr[0]), "count": int(rr[1])})
    return out

@app.get("/analytics/tasks/status")
def tasks_status(u=Depends(require_role("admin","supervisor"))):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) AS c FROM tasks GROUP BY status")
    rows = cur.fetchall()
    conn.close()

    out = []
    for rr in rows:
        if isinstance(rr, dict):
            out.append({"status": rr["status"], "count": int(rr["c"])})
        else:
            out.append({"status": rr[0], "count": int(rr[1])})
    return out
