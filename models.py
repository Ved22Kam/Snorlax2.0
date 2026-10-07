"""Database models for the YouTube Moderation Bot.

Stores:
- Streamers (channels the bot moderates)
- OAuth tokens (refresh tokens for each channel)
- Moderation rules (per streamer)
- Voice command logs
- Game state (per streamer)
"""
import sqlite3
from datetime import datetime
from config import get_db_path

def init_db(db_path=None):
    """Initialize the SQLite database with all required tables."""
    path = str(db_path) if db_path else get_db_path()
    conn = sqlite3.connect(path)
    c = conn.cursor()

    # Streamers table — each YouTube channel the bot moderates
    c.execute('''
        CREATE TABLE IF NOT EXISTS streamers (
            id TEXT PRIMARY KEY,
            channel_id TEXT UNIQUE,
            channel_title TEXT,
            refresh_token TEXT,
            access_token TEXT,
            token_expires_at REAL,
            live_chat_id TEXT,
            live_stream_id TEXT,
            is_active INTEGER DEFAULT 0,
            created_at REAL,
            updated_at REAL
        )
    ''')

    # Moderation rules per streamer
    c.execute('''
        CREATE TABLE IF NOT EXISTS mod_rules (
            streamer_id TEXT PRIMARY KEY,
            timeout_duration INTEGER DEFAULT 30,
            banned_words TEXT,              -- JSON list
            allowed_links TEXT,            -- JSON list ["discord.gg/x", ...]
            auto_ban_repetitions INTEGER DEFAULT 3,
            slow_mode_enabled INTEGER DEFAULT 0,
            slow_mode_seconds INTEGER DEFAULT 10,
            FOREIGN KEY (streamer_id) REFERENCES streamers(id)
        )
    ''')

    # Voice command history (for learning / debugging)
    c.execute('''
        CREATE TABLE IF NOT EXISTS voice_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            streamer_id TEXT,
            raw_text TEXT,
            parsed_action TEXT,
            success INTEGER,
            timestamp REAL,
            FOREIGN KEY (streamer_id) REFERENCES streamers(id)
        )
    ''')

    # Game state per streamer
    c.execute('''
        CREATE TABLE IF NOT EXISTS game_state (
            streamer_id TEXT PRIMARY KEY,
            game_name TEXT,
            active INTEGER DEFAULT 0,
            current_question TEXT,
            correct_answer TEXT,
            players TEXT,                 -- JSON list of participants
            current_round INTEGER DEFAULT 0,
            FOREIGN KEY (streamer_id) REFERENCES streamers(id)
        )
    ''')

    # Bot settings (global)
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    conn.commit()
    conn.close()
    return path


def get_streamers(db_path=None):
    """Returns list of active streamers from the DB."""
    path = str(get_db_path() if db_path is None else db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM streamers WHERE is_active=1")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_streamer(streamer_id, db_path=None):
    """Returns a single streamer dict or None."""
    path = str(get_db_path() if db_path is None else db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM streamers WHERE id=?", (streamer_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_streamer(streamer_id, channel_id, channel_title, refresh_token=None,
                    live_chat_id=None, live_stream_id=None, is_active=True, db_path=None):
    """Insert or update a streamer record. Returns the record dict."""
    path = str(get_db_path() if db_path is None else db_path)
    now = datetime.now().timestamp()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        INSERT INTO streamers (id, channel_id, channel_title, refresh_token,
            live_chat_id, live_stream_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            channel_id=excluded.channel_id,
            channel_title=excluded.channel_title,
            refresh_token=COALESCE(excluded.refresh_token, streamers.refresh_token),
            live_chat_id=COALESCE(excluded.live_chat_id, streamers.live_chat_id),
            live_stream_id=excluded.live_stream_id,
            is_active=excluded.is_active,
            updated_at=excluded.updated_at
    ''', (streamer_id, channel_id, channel_title, refresh_token,
          live_chat_id, live_stream_id, 1 if is_active else 0, now, now))
    conn.commit()
    c.execute("SELECT * FROM streamers WHERE id=?", (streamer_id,))
    row = c.fetchone()
    conn.close()
    return dict(row)


def get_or_create_rules(streamer_id, db_path=None):
    """Returns moderation rules for a streamer, creating defaults if missing."""
    import json
    path = str(get_db_path() if db_path is None else db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM mod_rules WHERE streamer_id=?", (streamer_id,))
    row = c.fetchone()
    if row is None:
        c.execute('''
            INSERT INTO mod_rules (streamer_id, timeout_duration, banned_words,
                allowed_links, auto_ban_repetitions, slow_mode_enabled)
            VALUES (?, 30, '[]', '[]', 3, 0)
        ''', (streamer_id,))
        conn.commit()
        c.execute("SELECT * FROM mod_rules WHERE streamer_id=?", (streamer_id,))
        row = c.fetchone()
    conn.close()
    result = dict(row)
    result['banned_words'] = json.loads(result.get('banned_words') or '[]') or []
    result['allowed_links'] = json.loads(result.get('allowed_links') or '[]') or []
    return result


def log_voice_command(streamer_id, raw_text, action, success=True, db_path=None):
    """Log a voice command for analytics and debugging."""
    import json
    path = str(get_db_path() if db_path is None else db_path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO voice_commands (streamer_id, raw_text, parsed_action, success, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (streamer_id, raw_text, action, 1 if success else 0, datetime.now().timestamp()))
    conn.commit()
    conn.close()


def get_game_state(streamer_id, db_path=None):
    """Returns current game state for a streamer."""
    path = str(get_db_path() if db_path is None else db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM game_state WHERE streamer_id=?", (streamer_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_game_state(streamer_id, db_path=None, **fields):
    """Update game state fields for a streamer."""
    path = str(get_db_path() if db_path is None else db_path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    # Ensure row exists
    c.execute("INSERT OR IGNORE INTO game_state (streamer_id) VALUES (?)", (streamer_id,))
    if fields:
        cols = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [streamer_id]
        c.execute(f"UPDATE game_state SET {cols} WHERE streamer_id=?", vals)
    conn.commit()
    conn.close()


def clear_active_games(db_path=None):
    """Deactivate all games (useful for shutdown)."""
    path = str(get_db_path() if db_path is None else db_path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("UPDATE game_state SET active=0")
    conn.commit()
    conn.close()
