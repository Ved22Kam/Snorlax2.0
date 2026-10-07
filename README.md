# YouTube Chat Moderation Bot — Centralized Voice-Command Moderation

## What it does
- One central bot moderates **5–100 YouTube live streams** simultaneously
- **Voice commands** via OBS Browser Source (push-to-talk) + Web app for phone
- **Chat moderation**: ban, timeout, delete messages, filter links, banter responses, games
- **Authentication**: each streamer adds your bot as a moderator via OAuth (one-time)
- **Zero-config for streamers**: copy the `.exe` to OBS, paste their stream URL

## Architecture
```
Streamer PC                           Central Bot (Railway/Render)
┌──────────────┐                      ┌─────────────────────────────┐
│ OBS Browser  │◄─ WebSocket ────────┤ FastAPI Server              │
│ Source       │                     │ ├─ WebSocket handler        │
│ voice_client │                     │ ├─ ChatManager (per stream) │
└──────────────┘                      │ ├─ Commands parser          │
                                      │ └─ SQLite (streamers, tokens)│
┌──────────────┐                      └─────────────────────────────┘
│ Web App      │                              ▲
│ (phone)      │                              │
└──────────────┘                    YouTube OAuth per streamer
```

## Quick Start (testing on your PC)
```bash
pip install -r requirements.txt
python main.py
# Open http://localhost:8000 to add your first streamer (OAuth flow)
# Open OBS Browser Source → http://localhost:8000/client/streamer_id
# Press and hold the SPACE key in OBS → speak command
```

## Free Deployment
- Railway free tier: push to GitHub, auto-deploy
- Render free tier: same
- Note: free tiers have sleep limits; for 100 streams, upgrade to $5/mo

## Voice Commands (examples)
- "timeout @user 10"
- "ban @user spam"
- "delete message"
- "link discord" → posts configured link
- "banter on/off"
- "game trivia" / "game rps"
- "status" → reports active streams
- "hello" → banter response

## Files
- `main.py` — FastAPI server (entry point)
- `chat_manager.py` — YouTube chat integration + moderation
- `commands.py` — Command parser
- `models.py` — DB models
- `config.py` — Config + helpers
- `voice_client.html` — OBS Browser Source (push-to-talk)
- `app.html` — Phone/web app
- `requirements.txt` — Dependencies
- `DEPLOY.md` — Free-tier deployment guide
- `test_bot.py` — Automated test suite
