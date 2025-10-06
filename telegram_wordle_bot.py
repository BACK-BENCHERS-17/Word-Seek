#!/usr/bin/env python3
"""
Enhanced Telegram Wordle Solver Bot (Multi-Chat, Render-Ready)
- Works in multiple groups at once
- Uses StringSession (no phone number)
- Survives +reboot on Render
"""
import asyncio
import os
import re
import sys
import threading
import time
from datetime import datetime
from collections import Counter
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import requests
from flask import Flask, jsonify

# ==========================
# 📝 CONFIG — Using String Session
# ==========================
API_ID = int(os.getenv('TELEGRAM_API_ID', '55460'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '00505c7ecb5d84fc463e7e1839d40fb4')
SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING')
if not SESSION_STRING:
    raise ValueError("❌ TELEGRAM_SESSION_STRING is required!")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==========================
# 🔤 WORD LIST & UTILITIES
# ==========================
MATH_BOLD_MAP = {
    '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E',
    '𝗙': 'F', '𝗚': 'G', '𝗛': 'H', '𝗜': 'I', '𝗝': 'J',
    '𝗞': 'K', '𝗟': 'L', '𝗠': 'M', '𝗡': 'N', '𝗢': 'O',
    '𝗣': 'P', '𝗤': 'Q', '𝗥': 'R', '𝗦': 'S', '𝗧': 'T',
    '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X', '𝗬': 'Y', '𝗭': 'Z',
    '𝗮': 'a', '𝗯': 'b', '𝗰': 'c', '𝗱': 'd', '𝗲': 'e',
    '𝗳': 'f', '𝗴': 'g', '𝗵': 'h', '𝗶': 'i', '𝗷': 'j',
    '𝗸': 'k', '𝗹': 'l', '𝗺': 'm', '𝗻': 'n', '𝗼': 'o',
    '𝗽': 'p', '𝗾': 'q', '𝗿': 'r', '𝘀': 's', '𝘁': 't',
    '𝘂': 'u', '𝘃': 'v', '𝘄': 'w', '𝘅': 'x', '𝘆': 'y', '𝘇': 'z',
}

def load_words():
    words_file = "words_5letter.txt"
    if not os.path.exists(words_file):
        print("📥 Using built-in word list...")
        common_words = [
            "CRANE", "SLATE", "ADIEU", "STARE", "CRISP", "AUDIO", "AROSE", "RAISE",
            "SAINT", "PARTY", "TRUMP", "MOURN", "CLOTH", "DEMON", "FIELD", "GHOST",
            "HULKS", "MIXER", "POWER", "QUICK", "STORM", "TWINS", "VIXEN", "WHIPS",
            # ... (rest of your 1000+ words — keep as-is)
            "ZESTS", "ZONES", "ZOOMS"
        ]
        with open(words_file, 'w') as f:
            for word in common_words:
                f.write(word + '\n')
    try:
        with open(words_file, 'r', encoding='utf-8', errors='ignore') as f:
            words = [line.strip().upper() for line in f if len(line.strip()) == 5 and line.strip().isalpha()]
        print(f"📚 Loaded {len(words)} 5-letter words")
        return words
    except Exception as e:
        print(f"❌ Error reading words: {e}")
        return []

WORDS = load_words()

# ==========================
# 🧠 FAST WORDLE SOLVER
# ==========================
class FastWordleSolver:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.fixed = {}
        self.forbidden = {}
        self.min_cnt = {}
        self.max_cnt = {}
        self.known = set()
        self.candidates = WORDS.copy()
        self.guess_count = 0

    def clean_word(self, w):
        cleaned = ''.join(MATH_BOLD_MAP.get(c, c) for c in w)
        cleaned = ''.join(c for c in cleaned if c.isascii() and c.isalpha()).upper()
        return cleaned[:5] if len(cleaned) >= 5 else cleaned

    def emoji_to_pattern(self, text):
        emoji_map = {'🟩': 'G', '🟨': 'Y', '🟥': 'B', '⬛': 'B', '⬜': 'B', '⬛️': 'B', '⬜️': 'B', '🟫': 'B'}
        pattern = ""
        for char in text:
            if char in emoji_map:
                pattern += emoji_map[char]
                if len(pattern) == 5:
                    break
        return pattern if len(pattern) == 5 else None

    def parse_feedback(self, text):
        lines = text.splitlines()
        for line in reversed(lines):
            pattern = self.emoji_to_pattern(line)
            if not pattern:
                continue
            word = None
            parts = line.split()
            for part in reversed(parts):
                candidate = self.clean_word(part)
                if len(candidate) == 5:
                    word = candidate
                    break
            if not word:
                all_letters = ''.join(MATH_BOLD_MAP.get(c, c) for c in line if c.isalpha() or c in MATH_BOLD_MAP)
                all_letters = ''.join(c for c in all_letters if c.isascii()).upper()
                if len(all_letters) >= 5:
                    word = all_letters[-5:]
            if word and len(word) == 5:
                return word, pattern
        return None, None

    def process_feedback(self, guess, pattern):
        self.guess_count += 1
        greens, yellows, greys = [], [], []
        for i, (p, ch) in enumerate(zip(pattern, guess)):
            if p == "G":
                greens.append((i, ch))
                self.known.add(ch)
            elif p == "Y":
                yellows.append((i, ch))
                self.known.add(ch)
            else:
                greys.append((i, ch))
        for i, ch in greens:
            self.fixed[i] = ch
        for i, ch in yellows + greys:
            if i not in self.forbidden:
                self.forbidden[i] = set()
            self.forbidden[i].add(ch)
        gy_count = Counter(ch for _, ch in greens + yellows)
        for ch, cnt in gy_count.items():
            self.min_cnt[ch] = max(self.min_cnt.get(ch, 0), cnt)
        for i, ch in greys:
            if ch not in self.known:
                self.max_cnt[ch] = 0
            else:
                current_min = self.min_cnt.get(ch, 0)
                self.max_cnt[ch] = max(0, current_min)
        self.candidates = [w for w in self.candidates if self.is_valid_word(w)]

    def is_valid_word(self, word):
        for i, ch in self.fixed.items():
            if word[i] != ch:
                return False
        for i in range(5):
            if i in self.forbidden and word[i] in self.forbidden[i]:
                return False
        word_count = Counter(word)
        for ch, min_cnt in self.min_cnt.items():
            if word_count.get(ch, 0) < min_cnt:
                return False
        for ch, max_cnt in self.max_cnt.items():
            if word_count.get(ch, 0) > max_cnt:
                return False
        return True

    def get_next_guess(self):
        if not self.candidates:
            return None
        if self.guess_count == 0:
            starters = ["CRANE", "SLATE", "ADIEU", "STARE", "CRISP", "AUDIO", "AROSE", "RAISE"]
            for starter in starters:
                if starter in self.candidates:
                    return starter
        return self.candidates[0]

    def is_solved(self, pattern):
        return pattern and len(pattern) == 5 and all(c == 'G' for c in pattern)

# ==========================
# 🤖 TELEGRAM BOT — MULTI-CHAT SUPPORT
# ==========================
active_sessions = {}  # chat_id → session dict

rate_limit_delay = 3.0
last_request_time = 0
blocked_until = 0
health_status = "healthy"
uptime_start = None

async def intelligent_delay():
    global last_request_time, rate_limit_delay, blocked_until
    current_time = time.time()
    if blocked_until > current_time:
        wait_time = blocked_until - current_time
        print(f"⏰ Waiting {int(wait_time)}s until unblocked...")
        await asyncio.sleep(wait_time)
        blocked_until = 0
        print("🟢 Unblocked!")
    time_since_last = current_time - last_request_time
    if time_since_last < rate_limit_delay:
        await asyncio.sleep(rate_limit_delay - time_since_last)
    last_request_time = time.time()

async def handle_rate_limit_block():
    global blocked_until, rate_limit_delay, health_status
    print("🚫 Rate limit detected!")
    blocked_until = time.time() + (20 * 60)
    rate_limit_delay = min(rate_limit_delay * 1.5, 10.0)
    health_status = "rate_limited"
    print(f"⏰ Blocked until: {datetime.fromtimestamp(blocked_until).strftime('%H:%M:%S')}")

def keep_alive_ping():
    try:
        requests.get("http://localhost:5000/ping", timeout=5)
    except:
        pass

async def auto_recovery_check():
    global health_status, blocked_until, rate_limit_delay
    while True:
        await asyncio.sleep(300)
        current_time = time.time()
        if blocked_until < current_time and health_status == "rate_limited":
            health_status = "healthy"
            rate_limit_delay = max(3.0, rate_limit_delay * 0.8)
            print("💚 Health restored")
        keep_alive_ping()

async def start_new_game_in_chat(chat_id):
    session = active_sessions[chat_id]
    solver = session["solver"]
    solver.reset()
    session["processed_words"].clear()
    first_guess = solver.get_next_guess()
    if first_guess:
        session["last_sent_guess"] = first_guess
        await intelligent_delay()
        await client.send_message(chat_id, first_guess)
        print(f"📤 Chat {chat_id}: Started with '{first_guess}'")
    else:
        await finish_game_in_chat(chat_id, success=False)

async def finish_game_in_chat(chat_id, success=True):
    if chat_id not in active_sessions:
        return
    session = active_sessions[chat_id]
    session["games_solved"] += 1
    solver = session["solver"]
    if success:
        print(f"✅ Chat {chat_id}: Game {session['games_solved']} solved in {solver.guess_count} guesses")
    else:
        print(f"❌ Chat {chat_id}: Game {session['games_solved']} failed")
    if session["games_solved"] < session["games_to_solve"]:
        await asyncio.sleep(1)
        await client.send_message(chat_id, "/new")
        await asyncio.sleep(1)
        await start_new_game_in_chat(chat_id)
    else:
        del active_sessions[chat_id]
        print(f"🔚 Chat {chat_id}: All games done")

@client.on(events.NewMessage(pattern=r'/new(?:\s+(\d+))?'))
async def handle_new_command(event):
    chat_id = event.chat_id
    if chat_id in active_sessions:
        await event.reply("⚠️ Game already active here.")
        return
    try:
        count = int(event.pattern_match.group(1)) if event.pattern_match.group(1) else 1
        if not (1 <= count <= 1000):
            await event.reply("❌ Use /new [1–1000]")
            return
        active_sessions[chat_id] = {
            "solver": FastWordleSolver(),
            "games_to_solve": count,
            "games_solved": 0,
            "processed_words": set(),
            "last_sent_guess": None,
            "last_processed_message": None,
            "state": "guessing"
        }
        print(f"🎯 Chat {chat_id}: Starting {count} game(s)")
        await start_new_game_in_chat(chat_id)
    except Exception as e:
        await event.reply(f"⚠️ Error: {e}")
        if chat_id in active_sessions:
            del active_sessions[chat_id]

@client.on(events.NewMessage(pattern='/stop'))
async def handle_stop_command(event):
    if event.chat_id in active_sessions:
        del active_sessions[event.chat_id]
        await event.reply("⏹️ Stopped in this chat.")

@client.on(events.NewMessage(pattern='/status'))
async def handle_status_command(event):
    chat_id = event.chat_id
    if chat_id not in active_sessions:
        await event.reply(f"Idle (Words: {len(WORDS)})")
    else:
        s = active_sessions[chat_id]
        msg = f"Active: {s['games_solved']}/{s['games_to_solve']} | Guesses: {s['solver'].guess_count} | Candidates: {len(s['solver'].candidates)}"
        await event.reply(msg)

@client.on(events.NewMessage(pattern=r'\+reboot'))
async def handle_reboot_command(event):
    await event.reply("🔄 Rebooting...")
    await asyncio.sleep(1)
    os._exit(0)  # Render will restart

@client.on(events.NewMessage)
async def handle_game_response(event):
    chat_id = event.chat_id
    if chat_id not in active_sessions:
        return
    session = active_sessions[chat_id]
    if session["state"] != "guessing":
        return
    solver = session["solver"]
    text = event.raw_text.lower()
    # Completion messages
    if ("congrats" in text and "guessed it correctly" in text) or "start with /new" in text:
        await finish_game_in_chat(chat_id, success=True)
        return
    if "someone has already guessed" in text or "already guessed" in text:
        if session["last_sent_guess"] in solver.candidates:
            solver.candidates.remove(session["last_sent_guess"])
        next_guess = solver.get_next_guess()
        if next_guess:
            session["last_sent_guess"] = next_guess
            await intelligent_delay()
            await client.send_message(chat_id, next_guess)
        else:
            await finish_game_in_chat(chat_id, success=False)
        return
    # Skip if no emojis
    if not any(e in event.raw_text for e in "🟥🟨🟩⬛⬜⬛️⬜️🟫"):
        return
    if event.raw_text == session.get("last_processed_message"):
        return
    try:
        word, pattern = solver.parse_feedback(event.raw_text)
        if not word or not pattern:
            return
        key = f"{word}-{pattern}"
        if key in session["processed_words"]:
            return
        session["processed_words"].add(key)
        session["last_processed_message"] = event.raw_text
        if solver.is_solved(pattern):
            await finish_game_in_chat(chat_id, success=True)
            return
        solver.process_feedback(word, pattern)
        next_guess = solver.get_next_guess()
        if "you win" in text or "correct!" in text:
            await finish_game_in_chat(chat_id, success=True)
        elif "game over" in text or "you lose" in text:
            await finish_game_in_chat(chat_id, success=False)
        elif next_guess:
            session["last_sent_guess"] = next_guess
            await intelligent_delay()
            await client.send_message(chat_id, next_guess)
        else:
            await finish_game_in_chat(chat_id, success=False)
    except Exception as e:
        print(f"⚠️ Error in chat {chat_id}: {e}")
        if "flood" in str(e).lower() or "blocked" in str(e).lower():
            await handle_rate_limit_block()

# ==========================
# 🌐 FLASK WEB SERVER
# ==========================
app = Flask(__name__)

@app.route('/health')
def health():
    is_blocked = blocked_until > time.time()
    return jsonify({
        "healthy": health_status == "healthy" and not is_blocked,
        "status": health_status,
        "active_chats": len(active_sessions),
        "uptime_seconds": int(time.time() - uptime_start) if uptime_start else 0,
        "version": "multi-chat-2.1"
    })

@app.route('/ping')
def ping():
    return "pong", 200

def run_flask_server():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ==========================
# 🚀 MAIN
# ==========================
async def main():
    global uptime_start, health_status
    if not WORDS:
        print("❌ No words loaded!")
        return
    uptime_start = time.time()
    health_status = "healthy"
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    print("🌐 Flask server started on port 5000")
    await client.start()
    print("✅ Bot ready! Supports multiple chats.")
    recovery_task = asyncio.create_task(auto_recovery_check())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
