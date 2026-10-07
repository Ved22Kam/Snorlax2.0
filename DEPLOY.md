# Deployment Guide — YouTube Moderation Bot (Free Tier Ready)

## Target: 5–100 YouTubers, one central bot

## 1. Local Testing (your PC)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment (copy .env.example to .env and edit)
cp .env.example .env
# Fill GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from console.cloud.google.com

# 3. Initialize DB
python -c "from models import init_db; init_db()"

# 4. Start server
python main.py
# → Open http://localhost:8000/
# → Add first streamer via POST /streamers or OAuth flow
# → Open /client/test_streamer in OBS or browser
# → Press SPACE → say command → bot executes
```

## 2. Free Cloud Deployment
### Railway (recommended for this bot)
1. Push this folder to a GitHub repo.
2. Go to https://railway.app → New Project → Deploy from GitHub.
3. Set environment variables (add via Railway dashboard):
   - `BOT_HOST=0.0.0.0`
   - `BOT_PORT=8000`
   - `GOOGLE_CLIENT_ID=...`
   - `GOOGLE_CLIENT_SECRET=...`
4. Railway gives a URL like `https://bot-xyz.up.railway.app/`
5. For 5–10 streams: free tier works.
6. For 50–100 streams: upgrade to $5/mo (Railway Starter) to avoid sleep limits.

### Render (alternative)
1. Create a new Web Service on https://render.com
2. Connect GitHub repo.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python main.py`
5. Set environment variables in Render dashboard.
6. Free tier sleeps after 15 min of inactivity — use a ping service (e.g., UptimeRobot) to keep awake for free.

## 3. Authentication per Streamer (One-time per friend)
Each YouTuber must:
1. Go to `/oauth/start` on the deployed bot.
2. Authorize with their Google account (scopes: YouTube Data API, live chat moderation).
3. The bot gets a refresh token (stored in SQLite DB, never exposed).
4. Add them to the bot via `POST /streamers` with:
   `{"streamer_id":"my_id","channel_id":"UCxxxx","channel_title":"My Channel","refresh_token":"..."}`

**Important:** The bot runs as a moderator only. You do NOT need to share the bot's code with streamers — they just need the `/client/my_id` URL for OBS and the OAuth step.

## 4. Scaling to 100 Streams (Technical)
- Each stream = 1 asyncio task (~2 sec poll interval = ~30 req/min per stream).
- 100 streams = ~3000 req/min = ~50 req/sec. This is easily handled by a small server.
- YouTube API quota: 10,000 units/day free. Reading chat costs ~1/unit, inserting messages ~50/unit. With 30 msg/min per stream, that's ~1800 messages/hour = ~1800 units/hour. At 100 streams = 180,000/hour = exceeds quota.
- **For >10 streams:** Use `youtubei.js` (unofficial, no quota) instead of YouTube API, or upgrade to YouTube API quota ($150/1M units, usually free enough for small/mid channels if optimized).
- The bot is designed to swap between APIs easily (see `chat_manager.py` — replace `poll_chat()` with youtubei.js if needed).

## 5. Voice Command Flow (Zero-setup for streamers)
- Streamer adds `/client/my_id` to OBS Browser Source (or opens in phone).
- Page loads with `WebSocket` connection to bot.
- User presses SPACE or button → `SpeechRecognition` API transcribes → sends JSON to server.
- Server parses → executes moderation → sends result back to page.
- **No software install needed by streamers** — just OBS URL.

## 6. Free Cost Breakdown
| Component | Cost | Notes |
|---|---|---|
| Python + FastAPI | $0 | Open source |
| YouTube Data API | $0 | 10,000 quota/day free |
| SpeechRecognition (browser) | $0 | Web API, no server cost |
| SQLite DB | $0 | Local file |
| Hosting (Railway/Render free) | $0 | Sleep after 15min; ping to stay up |
| Voice STT (local Vosk) | $0 | If browser API unavailable |
| Total | **$0** for testing / small use |

## 7. To Give to Friends
Package as a single `.py` folder with clear README:
- They just need to run `python main.py` locally (test) or deploy on Railway.
- Only YOU configure OAuth tokens — they just need to authorize once.
- Give them the client URL: `https://your-bot.com/client/their_streamer_id`
- Give them the command list (printed at `/`).
