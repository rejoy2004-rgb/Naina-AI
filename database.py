import sqlite3
import os

DB_PATH = "naina_users.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initialize the SQLite database and create users, conversations, and chats tables.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Create conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            assessment_active INTEGER DEFAULT 0,
            assessment_questions INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)
    
    # 3. Create chats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def get_or_create_user(name, phone):
    """
    Create a new user or return an existing user's ID if the phone number already exists.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    name = name.strip()
    phone = phone.strip()
    try:
        cursor.execute("SELECT id, name FROM users WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        if row:
            user_id = row["id"]
            if row["name"] != name:
                cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
                conn.commit()
            return user_id
        else:
            cursor.execute("INSERT INTO users (name, phone) VALUES (?, ?)", (name, phone))
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()

def create_conversation(user_id, title="New Chat"):
    """
    Create a new conversation session for a user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
            (user_id, title)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_user_conversations(user_id):
    """
    Get all conversation sessions for a user, sorted by newest first.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, title, created_at FROM conversations WHERE user_id = ? ORDER BY id DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"]} for r in rows]
    finally:
        conn.close()

def get_conversation_chats(conversation_id, limit=50):
    """
    Fetch the chat messages for a specific conversation session.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT role, content FROM chats WHERE conversation_id = ? ORDER BY timestamp ASC LIMIT ?",
            (conversation_id, limit)
        )
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
    finally:
        conn.close()

def save_chat_message(conversation_id, role, content):
    """
    Persist a chat message under a specific conversation session.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO chats (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        conn.commit()
    finally:
        conn.close()

def get_conversation_state(conversation_id):
    """
    Get the assessment state of a conversation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT assessment_active, assessment_questions FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        row = cursor.fetchone()
        if row:
            return bool(row["assessment_active"]), int(row["assessment_questions"])
        return False, 0
    finally:
        conn.close()

def update_conversation_state(conversation_id, active, questions):
    """
    Update the assessment state of a conversation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE conversations SET assessment_active = ?, assessment_questions = ? WHERE id = ?",
            (1 if active else 0, questions, conversation_id)
        )
        conn.commit()
    finally:
        conn.close()

def update_conversation_title(conversation_id, title):
    """
    Update the title/label of a conversation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Limit length
    if len(title) > 35:
        title = title[:32] + "..."
    try:
        cursor.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id)
        )
        conn.commit()
    finally:
        conn.close()
