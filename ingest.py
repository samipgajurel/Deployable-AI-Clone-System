import pandas as pd
from db import connect

def run_ingest(csv_path="data\Samip Gajurel Interns Tracking Sheet - Sheet1.csv"):
    df = pd.read_csv(csv_path)
    df = df[df["Intern Name"].notna()]

    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM interns")
    cur.execute("DELETE FROM rag_records")

    for _, r in df.iterrows():
        rating = str(r["Progress Rating"]).count("★")

        cur.execute("""
        INSERT INTO interns VALUES (?,?,?,?,?,?,?,?)
        """,(
            r["ID Info"],
            r["Intern Name"],
            r["E-mail"],
            r["Learning Skill (Internship)"],
            r["Working On Project"],
            r["Progress (1st months)"],
            r["Knowledge Gained"],
            rating
        ))

        text = f"{r['Intern Name']} working on {r['Working On Project']} learned {r['Knowledge Gained']}"
        cur.execute("INSERT INTO rag_records(intern_id,text) VALUES (?,?)",(r["ID Info"],text))

    conn.commit()
    conn.close()
