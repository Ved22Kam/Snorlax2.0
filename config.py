"""Configuration + helpers for the YouTube Moderation Bot."""
import os
from pathlib import Path

# ============ ENVIRONMENT (set via .env) ============
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bot.db"
HOST = os.environ.get("BOT_HOST", "0.0.0.0")
PORT = int(os.environ.get("BOT_PORT", 8000))
MODE = os.environ.get("BOT_MODE", "test")  # test | production

# Google Cloud OAuth (from https://console.cloud.google.com)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
OAUTH_REDIRECT_URI = os.environ.get("BOT_REDIRECT_URI", f"http://localhost:{PORT}/oauth/callback")

# ============ YOUTUBE ============
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# ============ VOICE ============
# Hotkeys for OBS Browser Source (configurable per streamer later)
DEFAULT_PUSH_TO_TALK_KEY = " "  # SPACE bar
MAX_RECORDING_SECONDS = 15
MIN_COMMAND_LENGTH = 3

# ============ MODERATION ============
DEFAULT_TIMEOUT_SECONDS = 10
MAX_TIMEOUT_SECONDS = 7200  # 2 hours (YouTube max)
DEFAULT_BANTER_RESPONSES = [
    "Thanks for watching {user}! Keep it friendly in chat.",
    "Appreciate the support, {user}! Enjoy the stream.",
    "Welcome, {user}! Hope you're having a great day.",
]
BANTER_WELCOME_MESSAGE = "Welcome {user} to the stream! Be excellent to each other."

# ============ GAMES ============
TRIVIA_QUESTIONS = [
    {"q": "What's the capital of France?", "a": "paris"},
    {"q": "How many planets in our solar system?", "a": "8"},
    {"q": "What color do you get mixing red and white?", "a": "pink"},
    {"q": "Is water H2O?", "a": "yes"},
    {"q": "YouTube was founded in what year?", "a": "2005"},
]
GAME_ROCK_PAPER_SCISSORS = ["rock", "paper", "scissors"]

# ============ SCALABILITY ============
# Max concurrent streams (each stream = 1 async task)
MAX_CONCURRENT_STREAMS = 100
# Polling frequency (seconds) for chat reads
CHAT_POLL_INTERVAL = 3
# Free-tier-safe batch size for chat polling
CHAT_MAX_RESULTS = 50

# ============ MISC ============
def get_db_path():
    """Returns the database file path (overridable for tests)."""
    return Path(os.environ.get("BOT_DB_PATH", str(DB_PATH)))
