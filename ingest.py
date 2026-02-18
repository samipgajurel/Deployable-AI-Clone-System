import pandas as pd
import secrets
import string
from db import connect, is_postgres, ph
from auth import hash_password

def generate_password(length=10):
    alphabet = string.ascii_letters + string.digits + "!@#$%*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def run_ingest(csv_path: str):
    df = pd.read_csv(csv_path)
    df = df[df["Intern Name"].notna()]

    conn = connect()
    cur = conn.cursor()
    p = ph()

    # clear interns (keep users/tasks if you want; here we rebuild interns)
    cur.execute("DELETE FROM interns")

    created_creds = []

    insert_intern = f"""
    INSERT INTO interns(
      id_info, name, email, learning_skill, working_on_project,
      progress_month1, knowledge_gained, progress_rating_num, status
    )
    VALUES ({p},{p},{p},{p},{p},{p},{p},{p},'pending')
    """

    for _, r in df.iterrows():
        id_info = str(r.get("ID Info", "")).strip()
        name = str(r.get("Intern Name", "")).strip()
        email = str(r.get("E-mail", "")).strip()

        learning = str(r.get("Learning Skill (Internship)", "")).strip()
        project = str(r.get("Working On Project", "")).strip()
        prog = str(r.get("Progress (1st months)", "")).strip()
        know = str(r.get("Knowledge Gained", "")).strip()
        rating = float(str(r.get("Progress Rating", "")).count("★"))

        cur.execute(insert_intern, (id_info, name, email, learning, project, prog, know, rating))

        username = email if email else id_info
        plain = generate_password()
        hashed = hash_password(plain)

        # create intern user if not exists
        if is_postgres():
            cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        else:
            cur.execute("SELECT id FROM users WHERE username=?", (username,))
        exists = cur.fetchone()

        if not exists:
            if is_postgres():
                cur.execute("""
                  INSERT INTO users(username, full_name, role, password_hash, intern_id_info)
                  VALUES (%s,%s,'intern',%s,%s)
                """, (username, name, hashed, id_info))
            else:
                cur.execute("""
                  INSERT INTO users(username, full_name, role, password_hash, intern_id_info, created_at)
                  VALUES (?,?,?,?,?,datetime('now'))
                """, (username, name, "intern", hashed, id_info))

            created_creds.append({
                "role": "intern",
                "username": username,
                "password": plain,
                "intern_id": id_info,
                "name": name
            })

    conn.commit()
    conn.close()
    return int(len(df)), created_creds
