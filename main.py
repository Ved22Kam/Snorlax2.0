"""FastAPI server — entry point for the YouTube Moderation Bot.

Endpoints:
- GET /              → status + list of active streams
- GET /health        → health check
- GET /client/{sid}  → OBS Browser Source / web app (served HTML)
- WS /ws/voice/{sid} → Voice command WebSocket (audio/text -> moderation)
- GET /oauth/start    → OAuth start (redirect to Google)
- GET /oauth/callback → OAuth callback (store refresh token)
- POST /streamers     → Add/activate a stream (manual or via OAuth result)
- GET /streamers      → List all streamers
- POST /streamers/{sid}/start  → Start monitoring chat for a streamer
- POST /streamers/{sid}/stop   → Stop monitoring chat
- GET /streamers/{sid}/status  → Status (messages read, connected, etc.)

Background tasks:
- asyncio.create_task(chat_manager.start()) per streamer
- Cleanup on shutdown
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio, html, time, json, os, sqlite3
from pathlib import Path

# ============ APP INIT ============
app = FastAPI(
    title="YouTube Chat Moderation Bot — Voice Command",
    description="Central bot moderating YouTube live chats with voice commands via OBS/web.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ STATE ============
# Per-streamer chat managers (key = streamer_id)
chat_managers: dict = {}
# WebSocket connections per streamer (for push notifications)
ws_connections: dict = {}
# Global settings
MAX_STREAMS = 100

# ============ INITIALIZE DB ============
from models import init_db, get_streamers, get_streamer, upsert_streamer, get_or_create_rules
init_db()

# ============ UTILS ============
def get_chat_manager(streamer_id: str):
    if streamer_id not in chat_managers:
        streamer = get_streamer(streamer_id)
        if not streamer:
            return None
        from chat_manager import ChatManager
        cm = ChatManager(
            streamer_id=streamer_id,
            refresh_token=streamer.get("refresh_token", ""),
            live_chat_id=streamer.get("live_chat_id"),
            live_stream_id=streamer.get("live_stream_id"),
        )
        chat_managers[streamer_id] = cm
    return chat_managers[streamer_id]


# ============ ROUTES ============
@app.get("/", response_class=HTMLResponse)
async def root():
    """Dashboard / landing page with docs and instructions."""
    active = [sid for sid, cm in chat_managers.items() if cm.is_connected]
    count = len(active)
    html_text = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>YouTube Moderation Bot</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;color:#222;
background:linear-gradient(180deg,#0f0f2d 0%,#1a1a3a 100%);color:#eee;padding:2rem;border-radius:16px;}}
h1{{color:#ffd966}}h2{{border-bottom:2px solid #ffd966;padding-bottom:.3em}}
code{{background:#333;padding:2px 6px;border-radius:4px;font-family:monospace;color:#fff}}
a{{color:#4fc3f7}}
.table{{width:100%;border-collapse:collapse}}
.table th{{text-align:left;padding:8px;border-bottom:2px solid #ffd966}}
.table td{{padding:8px;border-bottom:1px solid #444}}
.btn{{display:inline-block;padding:10px 18px;color:#fff;background:#ffd966;border:none;border-radius:6px;text-decoration:none;font-weight:600}}
</style></head><body>
<h1>🤖 YouTube Chat Moderation Bot</h1>
<h2>Centralized voice-command moderation for 5–100 YouTubers</h2>
<p>One bot, many streams.<br>Voice commands via <b>OBS Browser Source</b> or <b>phone/web</b>.</p>
<div style="background:#222;padding:1rem;border-radius:8px;margin:1rem 0;">
<b>Current active streams:</b> {count}<br>
<b>Client URL:</b> <code>/client/&lt;streamer_id&gt;</code><br>
<b>WebSocket:</b> <code>/ws/voice/&lt;streamer_id&gt;</code>
</div>
<h2>Quick Setup for Streamers</h2><ol>
<li>Authenticate with Google OAuth (add bot as moderator)</li>
<li>Copy streamer ID to OBS Browser Source: <code>/client/your_id</code></li>
<li>Press <b>SPACE</b> while OBS is focused → speak command</li>
<li>Bot moderates your chat (timeout, ban, links, games)</li>
</ol>
<h2>Voice Commands</h2><ul>
<li><code>timeout @user 10</code> — timeout 10 sec</li>
<li><code>ban @user spam</code> — permanent ban</li>
<li><code>hello</code> — bot responds in chat</li>
<li><code>game trivia</code> — starts trivia game</li>
<li><code>status</code> — bot reports stream status</li>
<li><code>link discord</code> — posts configured link</li>
</ul>
<h2>Deployment</h2><p>Test: <code>python main.py</code> → open <a href="/">/</a><br>
Deploy: push to GitHub, connect to <a href="https://railway.app">Railway</a> or <a href="https://render.com">Render</a> (free tiers available).</p>
<p><a href="/docs" class="btn">📄 Full Documentation</a></p>
</body></html>
"""
    return HTMLResponse(content=html_text)


@app.get("/docs")
async def docs():
    return HTMLResponse(content="""<!doctype html>
<html><head><title>Bot Docs</title></head><body>
<h1>Documentation</h1>
<h2>Architecture</h2><ul>
<li><b>FastAPI</b> server with async per-stream chat tasks</li>
<li><b>WebSocket</b>/voice for real-time command input</li>
<li><b>OBS Browser Source</b> loads /client/{sid} — push-to-talk + Web Speech API</li>
<li><b>Phone/Web App</b> loads /client/{sid} — tap to speak</li>
<li><b>SQLite</b> stores streamers, rules, voice logs</li>
</ul>
<h2>API Endpoints</h2>
<table border="1" cellpadding="6"><tr><th>Method</th><th>Path</th><th>Description</th></tr>
<tr><td>GET</td><td>/</td><td>Dashboard</td></tr>
<tr><td>GET</td><td>/health</td><td>Health check</td></tr>
<tr><td>GET</td><td>/client/{sid}</td><td>Voice client (OBS / web)</td></tr>
<tr><td>WS</td><td>/ws/voice/{sid}</td><td>Voice command socket</td></tr>
<tr><td>GET</td><td>/oauth/start</td><td>OAuth start</td></tr>
<tr><td>GET</td><td>/oauth/callback</td><td>OAuth callback</td></tr>
<tr><td>GET</td><td>/streamers</td><td>List streamers</td></tr>
<tr><td>POST</td><td>/streamers/{sid}/start</td><td>Start monitoring chat</td></tr>
<tr><td>POST</td><td>/streamers/{sid}/stop</td><td>Stop monitoring chat</td></tr>
</table>
<h2>Voice Client (OBS / Browser)</h2>
<p>Load <code>http://your-server/client/STREAMER_ID</code> in OBS Browser Source.</p>
<p>Press SPACE while OBS is focused. The page uses the browser's SpeechRecognition API.
Text is sent over WebSocket to the server, which executes moderation commands.</p>
</body></html>""")


@app.get("/health")
async def health():
    active = sum(1 for cm in chat_managers.values() if cm.is_connected)
    return {"status": "ok", "active_streams": active, "max_streams": MAX_STREAMS, "timestamp": time.time()}


# ============ VOICE CLIENT (OBS / BROWSER / PHONE) ============
@app.get("/client/{streamer_id}", response_class=HTMLResponse)
async def voice_client(streamer_id: str):
    """Serve the voice command client page (OBS Browser Source or phone)."""
    # Check streamer exists
    s = get_streamer(streamer_id)
    status = "Active" if s and s.get("is_active") else "Not configured"
    html_page = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bot Voice — {html.escape(streamer_id)}</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0f0f2d;color:#eee;text-align:center;padding:10% 2rem;}}
.container{{max-width:400px;margin:auto;padding:2rem;border-radius:20px;background:#181830;box-shadow:0 10px 60px rgba(255,217,102,.15)}}
h1{{color:#ffd966;font-size:1.4rem;margin-bottom:.2rem}}
.subtitle{{color:#aaa;font-size:.85rem;margin-bottom:1.5rem}}
.btn{{display:block;width:100%;padding:14px;margin:10px 0;border:none;border-radius:10px;background:#ffd966;color:#222;font-weight:700;font-size:1.1rem;cursor:pointer;transition:.2s}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 4px 15px rgba(255,217,102,.3)}}
#listen-btn.listening{{background:#ff5555;color:#fff}}
.status{{margin-top:1rem;font-size:.9rem;color:#aaa;min-height:1.2rem}}
.log{{margin-top:.5rem;font-family:monospace;font-size:.85rem;color:#ccc;text-align:left;background:#111;padding:.5rem;border-radius:8px;max-height:120px;overflow-y:auto}}
.instruction{{margin-top:1.5rem;font-size:.85rem;color:#777;line-height:1.5}}
</style>
</head><body>
<div class="container">
<h1>🎙 Voice Command Bot</h1>
<div class="subtitle">Streamer: <b>{html.escape(streamer_id)}</b> &nbsp;|&nbsp; Status: <b>{html.escape(status)}</b></div>
<button id="listen-btn" class="btn" onclick="startListening()">PRESS TO TALK (or SPACE key)</button>
<div id="status" class="status">Ready — press button or SPACE when OBS focused</div>
<div id="log" class="log"><b>Log:</b> Waiting for command...</div>
<div class="instruction">
<b>Tips:</b> Speak clearly after button turns green. <br>
<b>Sample:</b> "timeout user 10", "ban spam", "hello", "game trivia"
</div>
</div>
<script>
const sid = "{streamer_id}";
let ws = null;
let recognition = null;
let isListening = false;

function connectWS() {{
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(protocol + "//" + window.location.host + "/ws/voice/" + sid);
  ws.onopen = () => console.log("WS connected");
  ws.onmessage = (e) => {{
    const d = JSON.parse(e.data);
    document.getElementById("status").textContent = d.message || "Done";
    document.getElementById("log").innerHTML += "<br>→ " + (d.message || JSON.stringify(d));
    document.getElementById("log").scrollTop = document.getElementById("log").scrollHeight;
  }};
  ws.onclose = () => console.log("WS disconnected");
}}

function startListening() {{
  if (isListening) {{ stopListening(); return; }}
  isListening = true;
  document.getElementById("listen-btn").classList.add("listening");
  document.getElementById("listen-btn").textContent = "SPEAKING... (click to stop)";
  document.getElementById("status").textContent = "Listening...";
  // Web Speech API (free, works in Chrome / OBS Chromium)
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {{
    document.getElementById("status").textContent = "Speech API not supported in this browser. Use Chrome/OBS Chromium.";
    return;
  }}
  recognition = new SpeechRecognition();
  recognition.continuous = false; recognition.interimResults = false; recognition.lang = 'en-US';
  recognition.onresult = (e) => {{
    const text = e.results[0][0].transcript.trim();
    document.getElementById("log").innerHTML += "<br><b>Heard:</b> " + text;
    if (ws && ws.readyState === WebSocket.OPEN) {{
      ws.send(JSON.stringify({{type:"text", data:text, streamer_id:sid}}));
    }}
    stopListening();
  }};
  recognition.onerror = (e) => {{ console.error(e); stopListening(); }};
  recognition.start();
}}

function stopListening() {{
  isListening = false;
  document.getElementById("listen-btn").classList.remove("listening");
  document.getElementById("listen-btn").textContent = "PRESS TO TALK (or SPACE key)";
  document.getElementById("status").textContent = "Ready";
  if (recognition) recognition.stop();
}}
// Spacebar shortcut when OBS focused (page must be focused)
document.addEventListener("keydown", (e) => {{
  if (e.code === "Space" && document.activeElement.tagName !== "BUTTON") {{
    e.preventDefault();
    startListening();
  }}
}});
// Auto-connect
connectWS();
</script>
</body></html>"""
    return HTMLResponse(content=html_page)


# ============ WEBSOCKET (VOICE COMMAND) ============
@app.websocket("/ws/voice/{streamer_id}")
async def ws_voice(websocket: WebSocket, streamer_id: str):
    await websocket.accept()
    ws_connections.setdefault(streamer_id, set()).add(websocket)
    print(f"[WS] Voice client connected for {streamer_id}")
    # Ensure stream is configured
    s = get_streamer(streamer_id)
    if not s:
        await websocket.send_json({"message": f"Streamer '{streamer_id}' not configured. Add via OAuth first.", "success": False})
        await websocket.close()
        return
    # Ensure chat manager exists
    cm = get_chat_manager(streamer_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")
            if msg_type == "text":
                text = msg.get("data", "").strip()
                # Log command
                from models import log_voice_command
                # Execute command
                if cm:
                    parsed = cm.cmd_parser.parse(text, streamer_id)
                    result = cm.cmd_parser.execute(parsed)
                    # Send result back
                    await websocket.send_json({
                        "message": result.get("message", "Done"),
                        "success": result.get("success", False),
                        "action": parsed.get("action"),
                        "streamer_id": streamer_id,
                    })
                    # If command produces chat output, insert into chat
                    if result.get("message") and parsed.get("action") in ("hello", "game_trivia", "game_rps"):
                        # Send chat message via manager
                        cm.insert_message(result.get("message"), mention_id=msg.get("author"))
                    # Log
                    from models import log_voice_command
                    log_voice_command(streamer_id, text, parsed.get("action"), result.get("success"))
                else:
                    await websocket.send_json({"message": "Chat manager not available", "success": False})
            else:
                await websocket.send_json({"message": "Send {type:'text', data:'your command'}", "success": False})
    except WebSocketDisconnect:
        ws_connections.get(streamer_id, set()).discard(websocket)
        print(f"[WS] Voice client disconnected for {streamer_id}")
    except Exception as e:
        print(f"[WS] Error: {e}")
        await websocket.close()


# ============ OAUTH ============
@app.get("/oauth/start")
async def oauth_start():
    """Initiate OAuth to add this bot to a YouTube channel."""
    # Real implementation: build URL with scope=https://www.googleapis.com/auth/youtube.force-ssl, youtube.readonly, etc.
    # For prototype: show instructions and placeholder URL
    google_url = ("https://accounts.google.com/o/oauth2/v2/auth"
                  "?scope=https://www.googleapis.com/auth/youtube.force-ssl%20https://www.googleapis.com/auth/youtube.readonly"
                  "&access_type=offline&response_type=code"
                  "&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT")
    html_text = f"""<!doctype html><html><head><title>OAuth Start</title></head><body>
<h1>OAuth Setup</h1><p>To start moderating a stream, authenticate with Google.</p>
<p><b>Step 1:</b> Create a project at <a href="https://console.cloud.google.com">Google Cloud Console</a>, enable YouTube Data API v3.</p>
<p><b>Step 2:</b> Create OAuth 2.0 Client ID (Desktop or Web).</p>
<p><b>Step 3:</b> Set your CLIENT_ID and CLIENT_SECRET in this server's environment.</p>
<p><b>Step 4:</b> Click below to authorize (after setting client ID).</p>
<a href="{google_url}" class="btn">Authorize with Google</a>
<p><b>Note:</b> Use <code>?client_id=real_id</code> after configuring.</p>
</body></html>"""
    return HTMLResponse(content=html_text)


@app.get("/oauth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback — in production, exchange code for refresh token."""
    # Real implementation: POST to https://oauth2.googleapis.com/token with code, client_id, secret, redirect_uri
    # For prototype: instruct user and return confirmation
    if error:
        return HTMLResponse(content=f"<h1>OAuth Error: {html.escape(error)}</h1>")
    return HTMLResponse(content=f"""<!doctype html><html><body>
<h1>OAuth Callback Received</h1><p>Code: <code>{html.escape(str(code))}</code></p>
<p>In production, this endpoint exchanges the code for a refresh token and stores it.</p>
<p>After adding the token, create a streamer record: POST /streamers with channel info.</p>
</body></html>""")


# ============ STREAMER MANAGEMENT ============
@app.get("/streamers")
async def get_streamers_route():
    from models import get_streamers
    rows = get_streamers()
    # Sanitize
    safe = []
    for r in rows:
        safe.append({k: r[k] for k in ["id", "channel_id", "channel_title", "is_active", "live_chat_id", "updated_at"]})
    return JSONResponse({"streamers": safe, "count": len(safe)})


@app.post("/streamers")
async def add_streamer(request: Request):
    data = await request.json()
    sid = data.get("streamer_id", data.get("channel_id", "stream" + str(time.time())))
    channel_id = data.get("channel_id", sid)
    title = data.get("channel_title", "Unknown")
    refresh_token = data.get("refresh_token", "")
    live_chat_id = data.get("live_chat_id")
    from models import upsert_streamer
    record = upsert_streamer(sid, channel_id, title, refresh_token, live_chat_id, is_active=True)
    return JSONResponse({"streamer": record, "message": f"Added/updated streamer {sid}"})


@app.post("/streamers/{streamer_id}/start")
async def start_streamer(streamer_id: str):
    cm = get_chat_manager(streamer_id)
    if not cm:
        return JSONResponse({"success": False, "message": "Streamer not found"}, status_code=404)
    # Start background task
    if cm.task is None or cm.task.done():
        cm.task = asyncio.create_task(cm.start())
    return JSONResponse({"success": True, "message": f"Started monitoring {streamer_id}", "streamer_id": streamer_id})


@app.post("/streamers/{streamer_id}/stop")
async def stop_streamer(streamer_id: str):
    cm = chat_managers.get(streamer_id)
    if cm:
        cm.stop()
    return JSONResponse({"success": True, "message": f"Stopped monitoring {streamer_id}"})


@app.get("/streamers/{streamer_id}/status")
async def streamer_status(streamer_id: str):
    cm = chat_managers.get(streamer_id)
    s = get_streamer(streamer_id)
    if not s:
        return JSONResponse({"success": False, "message": "Not found"}, status_code=404)
    return JSONResponse({
        "streamer_id": streamer_id,
        "channel_id": s.get("channel_id"),
        "is_active": s.get("is_active"),
        "connected": cm.is_connected if cm else False,
        "messages_processed": cm.messages_processed if cm else 0,
        "live_chat_id": s.get("live_chat_id"),
    })


# ============ SHUTDOWN CLEANUP ============
@app.on_event("shutdown")
async def shutdown_event():
    for sid, cm in list(chat_managers.items()):
        cm.stop()
    from models import clear_active_games
    clear_active_games()
    print("[Shutdown] All chat managers stopped."),


# ============ MAIN ============
if __name__ == "__main__":
    import uvicorn
    # Auto-init DB
    from models import init_db
    init_db()
    # Start server
    print("=" * 60)
    print("YouTube Chat Moderation Bot — Voice Command")
    print("Dashboard: http://localhost:8000/")
    print("Voice Client (OBS): /client/<streamer_id>")
    print("WebSocket: /ws/voice/<streamer_id>")
    print("Start stream: POST /streamers/{sid}/start")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info", reload=False)
