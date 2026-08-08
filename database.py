import sqlite3
import json

DB_FILE = "data/proxy.db"

def init_db() : #create database
    with sqlite3.connect(DB_FILE) as conn:
        # cursor = conn.cursor()
        conn.execute("""CREATE TABLE IF NOT EXISTS webhooks(
        id TEXT Primary key,
        client_id TEXT NOT NULL,
        payload BLOB NOT NULL,
        headers TEXT NOT NULL,
        signature TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        status TEXT DEFAULT 'Pending',
        retry_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(signature)
        )""")
        conn.commit()

def save_webhook(request_id : str, client_id: str,payload:bytes,headers:dict,signature: str,timestamp:int):
    headers_json = json.dumps(headers)
    with sqlite3.connect(DB_FILE) as conn:
        # cursor = conn.cursor()
        conn.execute(
        "INSERT INTO webhooks (id,client_id,payload,headers,signature,timestamp) VALUES(?,?,?,?,?,?)",
        (request_id,client_id,payload,headers_json,signature,timestamp)
         )
        conn.commit()
def update_status(request_id:str, status: str, retry_count: int):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "UPDATE webhooks SET status = ?, retry_count = ? WHERE id = ?",(status,retry_count,request_id)
        )
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialised succesfully")