---
name: stream-moderation-bot-design
description: "Build voice-mod bot products with minimal user setup."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [bot-design, voice-commands, streaming, distributable, free-tier]
    related_skills: [claude-code, hermes-agent]
---

# Stream Moderation Bot Design — Centralized Voice-Command Bot

Design a single bot server that moderates many streamer channels with voice-command input, distributed with near-zero setup for end users (friends / streamers). Optimize for free-tier cost and quick verification.

## When to Use

- User asks for a bot that manages chat for multiple streamers (5–100 scale)
- Voice commands from streamer must trigger moderation (timeout, ban, links, games, banter)
- End users should not install software — only open a URL in OBS / browser / phone
- User explicitly asks whether it can be done for free
- Deliverable is working code + architecture doc, not just a plan

Don't use when: user needs a one-stream bot with full AI chat (use direct script instead); user requires real-time audio streaming instead of text commands; budget allows hosted APIs (OpenAI, AssemblyAI) exclusively.

## Prerequisites

- Python 3.10+, `fastapi`, `uvicorn`, `sqlite3` (stdlib)
- YouTube Data API v3 enabled in Google Cloud Console (OAuth 2.0 Client for token refresh)
- OBS Studio or browser that supports Web Speech API (Chrome/Chromium) for voice input
- Optional: `youtubei.js` if YouTube API quota is insufficient at scale (>10 active streams with high message rates)

## Procedure

### 1. Confirm the centralized-vs-distributed model

Ask clarifying questions (batch in one turn):
- "One bot you control that moderates all of them?" → Yes = central server.
- "Voice input method?" → OBS Browser Source + hotkey / phone web app (free, no install) preferred over per-user executable.
- "Scale?" → 5–100 concurrent streams determines quota planning.
- "Free or paid?" → Build with free stack first, document upgrade paths.

Pitfall: Do NOT design a PyInstaller .exe per friend unless they explicitly request zero-browser usage. The centralized URL pattern eliminates per-user setup.

### 2. Stack selection (free-first, swap-capable)

| Layer | Choice | Rationale | Swap if needed |
|---|---|---|---|
| Server | FastAPI + uvicorn (async) | Handles 100 concurrent WebSocket + poll loops | None |
| DB | SQLite (`sqlite3` stdlib) | Zero setup; file-based; adequate for rules/logs | Postgres if >1 server |
| Chat read | YouTube Data API `liveChatMessages().list()` | Free quota 10,000/day | `youtubei.js` (unofficial, no quota) |
| Voice STT | Browser `SpeechRecognition` (via WebSocket) | Free, works in OBS Chromium, avoids server audio processing | Vosk offline (`vosk`) if browser unavailable |
| Voice reply | None (user required no reply) | Avoids TTS complexity and cost | `edge-tts` / `gTTS` if needed |
| Auth per streamer | OAuth 2.0 refresh tokens in DB | One-time per friend; bot acts as moderator | Service account if managing own channels |

Pitfall: Do NOT assume Vosk is installed (`pip install vosk` may fail due to model download / size). Default to browser STT and mention Vosk only as fallback.

### 3. Architecture file structure

```
main.py              # FastAPI entry: WebSocket (/ws/voice/{sid}), REST endpoints, background chat tasks
commands.py          # Parser + executors for moderation actions
chat_manager.py      # Per-stream manager (poll + moderate + respond)
models.py            # SQLite init + queries
config.py            # Settings + limits (quota-safe defaults)
voice_client.html    # OBS Browser Source / phone web (WebSocket + SpeechRecognition)
README.md            # Usage
DEPLOY.md            # Free-tier deployment + scaling notes + cost breakdown
test_bot.py          # Import / DB / syntax verification
templates/obs-voice-client.html   # Starter copy for new instances
references/free-voice-stt.md     # STT option table
references/api-quota-check.md    # How to verify scale against quota
```

Pitfall: Do NOT put the whole HTML page inline in `main.py` unless it needs server-side rendering. Serving a static HTML string via `HTMLResponse` is acceptable for prototype; for production, serve from `templates/`.

### 4. Build order (verify at each step)

1. Write `config.py` + `models.py` → verify `python -c "from models import init_db; init_db()"`
2. Write `chat_manager.py` (with simulated YouTube calls, replace with real API when auth is ready) → verify import
3. Write `commands.py` → test parser with `python -c "from commands import ModerationBotCommands; ..."`
4. Write `main.py` → verify `python -c "from main import app; print('FastAPI OK')"`
5. Write `voice_client.html` (WebSocket to `/ws/voice/{sid}`, button + SPACE listener, `SpeechRecognition`) → open in Chrome, verify connection
6. Write `test_bot.py` → `python test_bot.py` should pass import + DB checks

Pitfall: Never claim the bot works end-to-end before verifying at least import + DB + server load. The user explicitly wants verified results, not descriptions.

### 5. Voice command design

Use browser-side `SpeechRecognition` to avoid server-side audio processing. Client sends JSON `{"type":"text","data":"timeout user 10","streamer_id":"..."}` over WebSocket. Server parses with regex patterns (`timeout`, `ban`, `filter add`, `game trivia`, `hello`, etc.), executes via `chat_manager`, and sends result back.

Pitfall: The `SpeechRecognition` API requires user interaction (button click or key press) and works best in Chrome-based browsers (OBS uses Chromium). Do not rely on it in Firefox/Safari without fallback instructions.

### 6. Scaling / quota check (before committing to 100 streams)

Calculate: messages/min/stream × streams × minutes/day = total messages. Each `liveChatMessages().list()` call costs 1 quota unit; inserting a bot message costs 50. If total > ~10,000/day, document swap to `youtubei.js`.

Pitfall: Do NOT skip this step. The user asked specifically if it can scale; answer with a number (quota/stream) and an alternative.

### 7. Free-cost documentation

Produce `DEPLOY.md` with:
- How to deploy on Railway / Render free tier
- Environment variables needed (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)
- What friends must do (authorize via OAuth once, use `/client/{sid}` URL)
- Cost table showing $0 for 5–10 streams, ~$5/mo for 50–100 (server upgrade, not API)
- Note that YouTube API is free with quota; server can stay free with ping service

Pitfall: Do NOT present the bot as "completely free at any scale." Quota and server sleep limits are real constraints; document them honestly.

## Verification

- `python test_bot.py` passes (imports + DB init)
- Server loads (`python main.py`) and responds at `http://localhost:8000/`
- Voice client URL `/client/test_streamer` loads in browser and connects via WebSocket
- Command parser handles `timeout`, `ban`, `hello`, `game trivia` correctly
- DB contains streamers after `POST /streamers`
- `DEPLOY.md` contains free-tier deployment steps and quota notes

## Pitfalls

- **No Vosk installed by default:** Build with browser STT first; mention Vosk only as fallback.
- **No real OAuth exchange in prototype:** `/oauth/callback` is a placeholder — production needs `google-auth-oauthlib` token exchange.
- **No YouTube API auth configured:** `chat_manager.poll_chat()` is simulated; replace with `googleapiclient.discovery.build()` once `refresh_token` is valid.
- **WebSocket requires server URL:** Friends need `https://your-bot.com/client/their_id`, not just localhost — document deployment URL step.
- **User wants no setup for friends:** If a friend must install Python/Node, redesign to centralized server + URL. Verify by asking clarifying question.
- **Free tier server sleeps:** Use UptimeRobot / cron ping if running 24/7 for free.
- **Voice reply not needed:** Do NOT add TTS by default; it increases cost (GPU/CPU) and complexity.
- **Verify before declaring success:** Always run import/DB test; never rely on "code looks right."

## References

- `references/free-voice-stt.md` — Browser SpeechRecognition vs Vosk vs cloud STT table
- `references/api-quota-check.md` — YouTube Data API quota costs and swap to youtubei.js
- `templates/obs-voice-client.html` — Starter HTML for OBS Browser Source
