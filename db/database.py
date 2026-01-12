# db/database.py

import sqlite3
from datetime import datetime

DB_PATH = 'music.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Songs cache + analysis
    c.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            song_id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            lyrics TEXT,
            mood TEXT,
            energy INTEGER,
            themes TEXT,
            analyzed_at TIMESTAMP
        )
    ''')
    
    # User taste profile
    c.execute('''
        CREATE TABLE IF NOT EXISTS profile (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Recommendations log
    c.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id TEXT,
            context TEXT,
            recommended_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized.")

# --- Songs ---

def get_song(song_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM songs WHERE song_id = ?', (song_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "song_id": row[0],
            "title": row[1],
            "artist": row[2],
            "lyrics": row[3],
            "mood": row[4],
            "energy": row[5],
            "themes": row[6],
            "analyzed_at": row[7]
        }
    return None

def save_song(song):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO songs 
        (song_id, title, artist, lyrics, mood, energy, themes, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        song['song_id'],
        song.get('title'),
        song.get('artist'),
        song.get('lyrics'),
        song.get('mood'),
        song.get('energy'),
        song.get('themes'),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def get_cached_songs(song_ids):
    """Split into cached and uncached"""
    cached = []
    uncached = []
    for song_id in song_ids:
        song = get_song(song_id)
        if song and song.get('mood'):  # has analysis
            cached.append(song)
        else:
            uncached.append(song_id)
    return cached, uncached

# --- Profile ---

def get_profile():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT key, value FROM profile')
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def set_profile(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO profile (key, value)
        VALUES (?, ?)
    ''', (key, value))
    conn.commit()
    conn.close()

# --- Recommendations ---

def log_recommendation(song_id, context):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO recommendations (song_id, context, recommended_at)
        VALUES (?, ?, ?)
    ''', (song_id, context, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_recent_recommendations(days=30):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT song_id FROM recommendations 
        WHERE recommended_at > datetime('now', ?)
    ''', (f'-{days} days',))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# Initialize on import
if __name__ == "__main__":
    init_db()
