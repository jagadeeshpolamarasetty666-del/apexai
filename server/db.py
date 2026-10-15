import os
import sqlite3
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apex.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL,
            arguments TEXT,
            status TEXT NOT NULL,
            output TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# --- Message Functions ---

def save_message(sender: str, text: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (sender, text) VALUES (?, ?)", (sender, text))
    conn.commit()
    conn.close()

def get_messages() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender, text, timestamp FROM messages ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r["id"], "sender": r["sender"], "text": r["text"], "timestamp": r["timestamp"]} for r in rows]

def clear_messages():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# --- Audit Log Functions ---

def log_audit(tool_name: str, arguments: str, status: str, output: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (tool_name, arguments, status, output) VALUES (?, ?, ?, ?)",
        (tool_name, arguments, status, output)
    )
    conn.commit()
    conn.close()

# --- Task Functions ---

def get_tasks() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, completed, created_at FROM tasks ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r["id"], "text": r["text"], "completed": bool(r["completed"]), "created_at": r["created_at"]} for r in rows]

def add_task(text: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (text, completed) VALUES (?, 0)", (text,))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": task_id, "text": text, "completed": False}

def toggle_task(task_id: int) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET completed = CASE WHEN completed = 1 THEN 0 ELSE 1 END WHERE id = ?", (task_id,))
    cursor.execute("SELECT id, text, completed, created_at FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    if row:
        return {"id": row["id"], "text": row["text"], "completed": bool(row["completed"])}
    return {}

def delete_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()