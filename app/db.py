"""
Database operations for Iraq Education AI Assistant.
Includes: users, study plans, quiz runs, reading results, and progress tracking.
"""
import sqlite3
import json
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from datetime import datetime

SCHEMA_SQL = """
-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'student',
  display_name TEXT,
  grade TEXT
);

-- Study plans
CREATE TABLE IF NOT EXISTS study_plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  user_id INTEGER,
  title TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Reading analysis results
CREATE TABLE IF NOT EXISTS reading_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  user_id INTEGER,
  label TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Quiz runs (generated quizzes)
CREATE TABLE IF NOT EXISTS quiz_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  user_id INTEGER,
  kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Progress tracking for computer lab
CREATE TABLE IF NOT EXISTS lab_progress (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  user_id INTEGER,
  total_questions INTEGER DEFAULT 0,
  correct_answers INTEGER DEFAULT 0,
  total_points INTEGER DEFAULT 0,
  best_streak INTEGER DEFAULT 0,
  badges_json TEXT DEFAULT '[]',
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Quiz attempts (individual quiz attempts with scores)
CREATE TABLE IF NOT EXISTS quiz_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  user_id INTEGER,
  quiz_type TEXT NOT NULL,
  subject TEXT,
  grade TEXT,
  score INTEGER,
  total_questions INTEGER,
  time_taken_seconds INTEGER,
  payload_json TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

def init_db(db_path: str) -> None:
    """Initialize database with all tables."""
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()

@contextmanager
def db_conn(db_path: str):
    """Context manager for database connections."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# ========================
# Generic CRUD Operations
# ========================

def insert_json(db_path: str, table: str, created_at: str, label_or_kind: str, payload_json: str, user_id: Optional[int] = None) -> int:
    """Insert JSON payload into specified table."""
    col = "title" if table == "study_plans" else ("label" if table == "reading_results" else "kind")
    
    if user_id:
        sql = f"INSERT INTO {table} (created_at, user_id, {col}, payload_json) VALUES (?, ?, ?, ?)"
        params = (created_at, user_id, label_or_kind, payload_json)
    else:
        sql = f"INSERT INTO {table} (created_at, {col}, payload_json) VALUES (?, ?, ?)"
        params = (created_at, label_or_kind, payload_json)
    
    with db_conn(db_path) as conn:
        cur = conn.execute(sql, params)
        return int(cur.lastrowid)

def list_rows(db_path: str, table: str, limit: int = 10, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """List rows from table, optionally filtered by user."""
    if user_id:
        sql = f"SELECT * FROM {table} WHERE user_id = ? ORDER BY id DESC LIMIT ?"
        params = (user_id, limit)
    else:
        sql = f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?"
        params = (limit,)
    
    with db_conn(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def get_row(db_path: str, table: str, row_id: int) -> Optional[Dict[str, Any]]:
    """Get single row by ID."""
    sql = f"SELECT * FROM {table} WHERE id = ?"
    with db_conn(db_path) as conn:
        r = conn.execute(sql, (row_id,)).fetchone()
        return dict(r) if r else None

# ========================
# User Operations
# ========================

def create_user(db_path: str, username: str, password_hash: str, role: str = "student", display_name: str = None, grade: str = None) -> int:
    """Create new user."""
    now = datetime.now().isoformat(timespec="seconds")
    sql = "INSERT INTO users (created_at, username, password_hash, role, display_name, grade) VALUES (?, ?, ?, ?, ?, ?)"
    with db_conn(db_path) as conn:
        cur = conn.execute(sql, (now, username, password_hash, role, display_name, grade))
        return int(cur.lastrowid)

def get_user_by_username(db_path: str, username: str) -> Optional[Dict[str, Any]]:
    """Get user by username."""
    sql = "SELECT * FROM users WHERE username = ?"
    with db_conn(db_path) as conn:
        r = conn.execute(sql, (username,)).fetchone()
        return dict(r) if r else None

def get_user_by_id(db_path: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    sql = "SELECT * FROM users WHERE id = ?"
    with db_conn(db_path) as conn:
        r = conn.execute(sql, (user_id,)).fetchone()
        return dict(r) if r else None

# ========================
# Progress Tracking
# ========================

def get_user_progress(db_path: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's lab progress."""
    sql = "SELECT * FROM lab_progress WHERE user_id = ? ORDER BY id DESC LIMIT 1"
    with db_conn(db_path) as conn:
        r = conn.execute(sql, (user_id,)).fetchone()
        return dict(r) if r else None

def update_user_progress(db_path: str, user_id: int, total_questions: int, correct_answers: int, total_points: int, best_streak: int, badges: List[str]) -> int:
    """Update or create user's lab progress."""
    now = datetime.now().isoformat(timespec="seconds")
    badges_json = json.dumps(badges, ensure_ascii=False)
    
    # Check if exists
    existing = get_user_progress(db_path, user_id)
    
    if existing:
        sql = """UPDATE lab_progress SET 
                 total_questions = ?, correct_answers = ?, total_points = ?, 
                 best_streak = ?, badges_json = ?
                 WHERE user_id = ?"""
        with db_conn(db_path) as conn:
            conn.execute(sql, (total_questions, correct_answers, total_points, best_streak, badges_json, user_id))
            return existing['id']
    else:
        sql = """INSERT INTO lab_progress 
                 (created_at, user_id, total_questions, correct_answers, total_points, best_streak, badges_json) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)"""
        with db_conn(db_path) as conn:
            cur = conn.execute(sql, (now, user_id, total_questions, correct_answers, total_points, best_streak, badges_json))
            return int(cur.lastrowid)

def record_quiz_attempt(db_path: str, user_id: int, quiz_type: str, subject: str, grade: str, score: int, total: int, time_seconds: int, payload: Dict) -> int:
    """Record a quiz attempt for progress tracking."""
    now = datetime.now().isoformat(timespec="seconds")
    payload_json = json.dumps(payload, ensure_ascii=False)
    
    sql = """INSERT INTO quiz_attempts 
             (created_at, user_id, quiz_type, subject, grade, score, total_questions, time_taken_seconds, payload_json) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    with db_conn(db_path) as conn:
        cur = conn.execute(sql, (now, user_id, quiz_type, subject, grade, score, total, time_seconds, payload_json))
        return int(cur.lastrowid)

def get_user_stats(db_path: str, user_id: int) -> Dict[str, Any]:
    """Get comprehensive user statistics."""
    stats = {
        "total_quizzes": 0,
        "total_questions_answered": 0,
        "correct_answers": 0,
        "accuracy": 0,
        "subjects": {},
        "recent_activity": [],
        "lab_progress": None
    }
    
    with db_conn(db_path) as conn:
        # Quiz attempts stats
        sql = """SELECT COUNT(*) as count, SUM(total_questions) as total_q, SUM(score) as correct
                 FROM quiz_attempts WHERE user_id = ?"""
        r = conn.execute(sql, (user_id,)).fetchone()
        if r:
            stats["total_quizzes"] = r["count"] or 0
            stats["total_questions_answered"] = r["total_q"] or 0
            stats["correct_answers"] = r["correct"] or 0
            if stats["total_questions_answered"] > 0:
                stats["accuracy"] = round(stats["correct_answers"] / stats["total_questions_answered"] * 100, 1)
        
        # Subject breakdown
        sql = """SELECT subject, COUNT(*) as attempts, AVG(score * 100.0 / total_questions) as avg_score
                 FROM quiz_attempts WHERE user_id = ? AND subject IS NOT NULL
                 GROUP BY subject"""
        rows = conn.execute(sql, (user_id,)).fetchall()
        for r in rows:
            stats["subjects"][r["subject"]] = {
                "attempts": r["attempts"],
                "avg_score": round(r["avg_score"] or 0, 1)
            }
        
        # Recent activity
        sql = """SELECT * FROM quiz_attempts WHERE user_id = ? ORDER BY id DESC LIMIT 5"""
        rows = conn.execute(sql, (user_id,)).fetchall()
        stats["recent_activity"] = [dict(r) for r in rows]
        
        # Lab progress
        stats["lab_progress"] = get_user_progress(db_path, user_id)
    
    return stats
