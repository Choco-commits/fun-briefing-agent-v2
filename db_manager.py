import sqlite3
from datetime import datetime

DB_PATH = "subscriptions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            topic TEXT NOT NULL,
            city TEXT,
            send_hour INTEGER NOT NULL,
            send_minute INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cached_html TEXT,
            cached_at TIMESTAMP,
            cache_status INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_subscription(email, topic, city, send_hour, send_minute=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO subscriptions (email, topic, city, send_hour, send_minute)
        VALUES (?, ?, ?, ?, ?)
    ''', (email, topic, city, send_hour, send_minute))
    conn.commit()
    conn.close()

def get_all_subscriptions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, email, topic, city, send_hour, send_minute, enabled FROM subscriptions WHERE enabled=1')
    rows = c.fetchall()
    conn.close()
    return rows

def get_subscription(sub_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, email, topic, city, send_hour, send_minute, cached_html, cache_status FROM subscriptions WHERE id=?', (sub_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_cache(sub_id, html, status=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE subscriptions SET cached_html=?, cached_at=?, cache_status=? WHERE id=?',
              (html, datetime.now(), status, sub_id))
    conn.commit()
    conn.close()

def get_cache_and_clear(sub_id):
    """读取缓存并清除，返回 (html, status)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT cached_html, cache_status FROM subscriptions WHERE id=?', (sub_id,))
    row = c.fetchone()
    if row and row[1] == 1:
        html = row[0]
        # 清除缓存
        c.execute('UPDATE subscriptions SET cached_html=NULL, cache_status=0 WHERE id=?', (sub_id,))
        conn.commit()
        conn.close()
        return html, True
    conn.close()
    return None, False

def delete_subscription(sub_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM subscriptions WHERE id = ?', (sub_id,))
    conn.commit()
    conn.close()

def add_subscription(email, topic, city, send_hour, send_minute=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO subscriptions (email, topic, city, send_hour, send_minute)
        VALUES (?, ?, ?, ?, ?)
    ''', (email, topic, city, send_hour, send_minute))
    conn.commit()
    sub_id = c.lastrowid
    conn.close()
    return sub_id
