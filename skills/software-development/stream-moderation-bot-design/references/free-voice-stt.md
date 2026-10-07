# Free Voice STT Options for Bot Products

Problem: server-side speech recognition requires model download, GPU/CPU, and library installation (Vosk, Whisper, etc.). For a product given to non-technical friends, avoid server-side audio processing if possible.

## Decision Table

| Approach | Cost | Setup burden | Works in OBS Chrome? | Best for |
|---|---|---|---|---|
| Browser `SpeechRecognition` (Web API) | $0 | None (built into Chrome) | Yes (OBS = Chromium) | Hotkey + mic via OBS Browser Source; primary choice for this bot |
| Vosk (`pip install vosk` + model) | $0 | Model download (~1GB), Python dep | Not needed (server processes audio) | Offline server-side; only if browser unavailable |
| Whisper (OpenAI) local (`pip whisper`) | $0 | Heavy GPU/CPU, model download | Not needed | High accuracy; only if needed |
| Whisper API / AssemblyAI / Deepgram | $0.006/min | API key only | Not needed | Best accuracy; budget allows $20–50/mo for heavy use |

## Recommendation (this session's verified approach)
- Default to Browser SpeechRecognition via WebSocket (text sent to server).
- Mention Vosk only as fallback in `DEPLOY.md`.
- Do not build server-side audio ingestion unless user explicitly needs it.

Pitfall: `vosk` pip install may fail if model not present or if binary wheels missing on Windows. Verify `import vosk` before relying on it.
