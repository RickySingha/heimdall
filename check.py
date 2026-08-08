import sqlite3

with sqlite3.connect("data/proxy.db") as conn:
    rows = conn.execute(
        "SELECT id, status, retry_count,created_at FROM webhooks ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    for row in rows:
        print(row)