"""Voice command parser + moderation actions for the bot.

Commands are parsed from text (from browser Web Speech API or server-side STT).
The bot executes moderation actions against YouTube Live Chat API.
"""
import re
import random
from config import DEFAULT_TIMEOUT_SECONDS, DEFAULT_BANTER_RESPONSES, BANTER_WELCOME_MESSAGE
from config import GAME_ROCK_PAPER_SCISSORS, TRIVIA_QUESTIONS


class ModerationBotCommands:
    """Parse and execute moderation commands."""

    def __init__(self, chat_manager):
        self.chat = chat_manager
        self.commands = {
            "timeout": self.cmd_timeout,
            "ban": self.cmd_ban,
            "unban": self.cmd_unban,
            "delete": self.cmd_delete,
            "hide": self.cmd_hide,
            "slow_mode": self.cmd_slow_mode,
            "filter_add": self.cmd_filter_add,
            "filter_remove": self.cmd_filter_remove,
            "filter_list": self.cmd_filter_list,
            "link": self.cmd_link,
            "links_add": self.cmd_links_add,
            "links_list": self.cmd_links_list,
            "welcome": self.cmd_welcome,
            "banter": self.cmd_banter,
            "hello": self.cmd_hello,
            "game_trivia": self.cmd_game_trivia,
            "game_rps": self.cmd_game_rps,
            "status": self.cmd_status,
            "help": self.cmd_help,
        }

    # ============ PARSER ============
    def parse(self, text: str, streamer_id: str) -> dict:
        """Parse raw text into a structured command."""
        if not text or len(text.strip()) < 2:
            return {"action": "unknown", "raw": text, "success": False, "reason": "text too short"}
        text = text.strip().lower()
        # Try to match structured commands first
        # Timeout: "timeout @username 5" or "timeout user 5 minutes"
        timeout_match = re.search(
            r"timeout\s+(@?[\w]+)\s+(\d+)(?:\s*(min|minute|minutes|m))?",
            text,
        )
        if timeout_match:
            user = timeout_match.group(1).lstrip("@")
            seconds = int(timeout_match.group(2))
            modifier = timeout_match.group(3) or ""
            if "min" in modifier or modifier == "minutes" or modifier == "m":
                seconds *= 60
            return {"action": "timeout", "user": user, "duration": seconds,
                    "raw": text, "streamer_id": streamer_id}
        # Ban: "ban @username reason"
        ban_match = re.search(
            r"ban\s+(@?[\w]+)(?:\s+(.+))?",
            text,
        )
        if ban_match:
            user = ban_match.group(1).lstrip("@")
            reason = (ban_match.group(2) or "spam").strip()
            return {"action": "ban", "user": user, "reason": reason,
                    "raw": text, "streamer_id": streamer_id}
        # Unban: "unban @username"
        unban_match = re.search(
            r"unban\s+(@?[\w]+)", text,
        )
        if unban_match:
            user = unban_match.group(1).lstrip("@")
            return {"action": "unban", "user": user,
                    "raw": text, "streamer_id": streamer_id}
        # Filter add: "filter add spamword"
        filter_add_match = re.search(
            r"filter\s+add\s+(.+)", text,
        )
        if filter_add_match:
            word = filter_add_match.group(1).strip()
            return {"action": "filter_add", "word": word,
                    "raw": text, "streamer_id": streamer_id}
        # Filter remove: "filter remove spamword"
        filter_remove_match = re.search(
            r"filter\s+remove\s+(.+)", text,
        )
        if filter_remove_match:
            word = filter_remove_match.group(1).strip()
            return {"action": "filter_remove", "word": word,
                    "raw": text, "streamer_id": streamer_id}
        # Filter list: "filter list"
        if re.search(r"filter\s+list", text):
            return {"action": "filter_list", "raw": text, "streamer_id": streamer_id}
        # Link / links commands
        link_post_match = re.search(
            r"link\s+(.+)", text,
        )
        if link_post_match and "add" not in text and "list" not in text:
            link_name = link_post_match.group(1).strip()
            return {"action": "link", "name": link_name,
                    "raw": text, "streamer_id": streamer_id}
        # Links add: "links add discord https://..."
        links_add_match = re.search(
            r"links\s+add\s+([\w]+)\s+(.+)", text,
        )
        if links_add_match:
            name = links_add_match.group(1).strip()
            url = links_add_match.group(2).strip()
            return {"action": "links_add", "name": name, "url": url,
                    "raw": text, "streamer_id": streamer_id}
        # Links list: "links list"
        if re.search(r"links\s+list", text):
            return {"action": "links_list", "raw": text, "streamer_id": streamer_id}
        # Slow mode: "slow mode 30" / "slow mode off"
        slow_match = re.search(
            r"slow\s+mode\s+(on|off|\d+)", text,
        )
        if slow_match:
            val = slow_match.group(1)
            if val == "on":
                return {"action": "slow_mode", "enable": True, "duration": 10,
                        "raw": text, "streamer_id": streamer_id}
            elif val == "off":
                return {"action": "slow_mode", "enable": False,
                        "raw": text, "streamer_id": streamer_id}
            else:
                return {"action": "slow_mode", "enable": True, "duration": int(val),
                        "raw": text, "streamer_id": streamer_id}
        # Welcome: "welcome on" / "welcome off"
        welcome_match = re.search(r"welcome\s+(on|off)", text)
        if welcome_match:
            return {"action": "welcome", "enable": welcome_match.group(1) == "on",
                    "raw": text, "streamer_id": streamer_id}
        # Banter toggle: "banter on" / "banter off"
        if re.search(r"banter\s+on", text) or text == "banter on":
            return {"action": "banter", "enable": True, "raw": text, "streamer_id": streamer_id}
        if re.search(r"banter\s+off", text) or text == "banter off":
            return {"action": "banter", "enable": False, "raw": text, "streamer_id": streamer_id}
        # Hello / greeting
        if text.startswith("hello") or text.startswith("hi ") or text.startswith("hey "):
            return {"action": "hello", "raw": text, "streamer_id": streamer_id}
        # Games
        if "game trivia" in text or "trivia" in text:
            return {"action": "game_trivia", "raw": text, "streamer_id": streamer_id}
        if "game rps" in text or ("rock" in text and "paper" in text) or ("rps" in text):
            return {"action": "game_rps", "raw": text, "streamer_id": streamer_id}
        # Status
        if "status" in text:
            return {"action": "status", "raw": text, "streamer_id": streamer_id}
        # Help
        if "help" in text:
            return {"action": "help", "raw": text, "streamer_id": streamer_id}
        # Hide user (soft moderation)
        hide_match = re.search(r"hide\s+(@?[\w]+)", text)
        if hide_match:
            user = hide_match.group(1).lstrip("@")
            return {"action": "hide", "user": user,
                    "raw": text, "streamer_id": streamer_id}
        # Delete message (needs message id, but we approximate by latest from user)
        delete_match = re.search(r"delete\s+(@?[\w]+)", text)
        if delete_match:
            user = delete_match.group(1).lstrip("@")
            return {"action": "delete", "user": user,
                    "raw": text, "streamer_id": streamer_id}
        # If nothing matched, return unknown (but still try to respond for banter)
        return {"action": "unknown", "raw": text, "success": False,
                "reason": f"No command matched for: {text}", "streamer_id": streamer_id}

    # ============ EXECUTORS ============
    def cmd_timeout(self, parsed: dict) -> dict:
        user, duration = parsed.get("user"), parsed.get("duration", DEFAULT_TIMEOUT_SECONDS)
        # Enforce max duration
        from config import MAX_TIMEOUT_SECONDS
        duration = min(duration, MAX_TIMEOUT_SECONDS)
        result = self.chat.ban_user(user, duration=duration, reason="timeout by voice command")
        if result.get("success"):
            return {"success": True, "message": f"Timeout applied to @{user} for {duration}s"}
        return {"success": False, "message": result.get("error", "Timeout failed")}

    def cmd_ban(self, parsed: dict) -> dict:
        user, reason = parsed.get("user"), parsed.get("reason", "spam")
        result = self.chat.ban_user(user, duration=None, reason=reason)
        if result.get("success"):
            return {"success": True, "message": f"Banned @{user} (reason: {reason})"}
        return {"success": False, "message": result.get("error", "Ban failed")}

    def cmd_unban(self, parsed: dict) -> dict:
        user = parsed.get("user")
        result = self.chat.unban_user(user)
        if result.get("success"):
            return {"success": True, "message": f"Unbanned @{user}"}
        return {"success": False, "message": result.get("error", "Unban failed")}

    def cmd_delete(self, parsed: dict) -> dict:
        # Approximate: delete latest message from user
        user = parsed.get("user", "")
        result = self.chat.delete_latest_message(user)
        if result.get("success"):
            return {"success": True, "message": f"Deleted message from @{user}"}
        return {"success": False, "message": result.get("error", "Delete failed")}

    def cmd_hide(self, parsed: dict) -> dict:
        user = parsed.get("user", "")
        result = self.chat.hide_user(user)
        if result.get("success"):
            return {"success": True, "message": f"Hidden @{user} from chat"}
        return {"success": False, "message": result.get("error", "Hide failed")}

    def cmd_slow_mode(self, parsed: dict) -> dict:
        enable, duration = parsed.get("enable"), parsed.get("duration", 30)
        result = self.chat.set_slow_mode(enable=enable, duration=duration)
        if result.get("success"):
            return {"success": True, "message": f"Slow mode {'ON' if enable else 'OFF'} (duration: {duration}s)"}
        return {"success": False, "message": result.get("error", "Slow mode failed")}

    def cmd_filter_add(self, parsed: dict) -> dict:
        word = parsed.get("word")
        if not word:
            return {"success": False, "message": "No word specified"}
        # This would be stored in DB rules; for now confirm
        return {"success": True, "message": f"Added filter word: '{word}'"}

    def cmd_filter_remove(self, parsed: dict) -> dict:
        word = parsed.get("word")
        if not word:
            return {"success": False, "message": "No word specified"}
        return {"success": True, "message": f"Removed filter word: '{word}'"}

    def cmd_filter_list(self, parsed: dict) -> dict:
        # Would retrieve from rules; placeholder
        return {"success": True, "message": "Filter list: spam, badword (update rules file)"}

    def cmd_link(self, parsed: dict) -> dict:
        name = parsed.get("name", "")
        # This would look up a configured link for this streamer
        # For now, return placeholder
        return {"success": True, "message": f"Link '{name}': not configured (add via links_add)"}

    def cmd_links_add(self, parsed: dict) -> dict:
        name, url = parsed.get("name"), parsed.get("url")
        return {"success": True, "message": f"Added link '{name}' → {url}"}

    def cmd_links_list(self, parsed: dict) -> dict:
        return {"success": True, "message": "Configured links: (see rules)"}

    def cmd_welcome(self, parsed: dict) -> dict:
        enable = parsed.get("enable", True)
        return {"success": True, "message": f"Auto-welcome {'ON' if enable else 'OFF'}"}

    def cmd_banter(self, parsed: dict) -> dict:
        enable = parsed.get("enable", True)
        return {"success": True, "message": f"Banter responses {'ON' if enable else 'OFF'}"}

    def cmd_hello(self, parsed: dict) -> dict:
        responses = DEFAULT_BANTER_RESPONSES
        msg = random.choice(responses).format(user="Streamer")
        return {"success": True, "message": msg, "banter": msg}

    def cmd_game_trivia(self, parsed: dict) -> dict:
        import random
        q = random.choice(TRIVIA_QUESTIONS)
        return {"success": True, "message": f"Trivia question: {q['q']} (Answer: {q['a']})",
                "game": "trivia", "question": q["q"], "answer": q["a"]}

    def cmd_game_rps(self, parsed: dict) -> dict:
        import random
        choice = random.choice(GAME_ROCK_PAPER_SCISSORS)
        return {"success": True, "message": f"Rock Paper Scissors! Bot chooses: {choice}",
                "game": "rps", "bot_choice": choice}

    def cmd_status(self, parsed: dict) -> dict:
        # This is handled by the server, not here
        return {"success": False, "message": "Status handled by server endpoint"}

    def cmd_help(self, parsed: dict) -> dict:
        help_text = (
            "Voice Commands: timeout @user 10 | ban @user spam | unban @user | "
            "delete @user | filter add word | link discord | links add name url | "
            "welcome on/off | banter on/off | hello | game trivia | game rps | status | help"
        )
        return {"success": True, "message": help_text, "help": True}

    def execute(self, parsed: dict) -> dict:
        """Run the parsed command."""
        action = parsed.get("action", "unknown")
        if action not in self.commands:
            return {"success": False, "message": f"Unknown command: {action}"}
        return self.commands[action](parsed)
