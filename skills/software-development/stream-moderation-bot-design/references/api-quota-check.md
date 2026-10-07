# YouTube Data API Quota — Scale Check Before Building 100 Streams

YouTube Data API v3 has a default quota of 10,000 units/day per project.

## Cost per operation (relevant)

| Method | Quota cost |
|---|---|
| `liveChatMessages().list` | 1 per call |
| `liveChatMessages().insert` (bot posts message) | 50 per call |
| `liveChatBans().insert` (timeout/ban) | 50 per call |
| `videos().list` (get live chat ID) | 1 per call |

## Estimate for 1 stream at 30 msg/min, bot responds 5/min

- Read: 30 msg/min × 60 = 1800 reads/hour = 1800 quota/hour
- Bot posts: 5/min × 60 = 300 posts/hour = 300 × 50 = 15,000 quota/hour → EXCEEDS quota quickly.

Pitfall: The bot must NOT post a message on every user message. Post only on commands, welcome messages, or game responses.

## Scaling to 100 streams

- With optimized polling (batch messages, minimal bot insertion, smart caching), 10–20 active streams can stay within free quota.
- Above that, document swap to `youtubei.js` (unofficial, reads chat via YouTube's internal endpoints, no quota limit). The `chat_manager.poll_chat()` method is structured to allow this swap easily.

Verification: compute `messages_per_min * 60 * 24 / 10000` to get streams supported by quota alone.
