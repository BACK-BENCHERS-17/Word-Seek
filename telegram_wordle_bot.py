#!/usr/bin/env python3
"""
Enhanced Telegram Wordle Solver Bot
- Starts with /new command and auto-stops after solving
- Supports /new [number] for bulk solving
- Combines fast solver with clean Telegram integration
"""
import asyncio
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta
from collections import Counter
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import requests
from flask import Flask, jsonify

# ==========================
# 📝 CONFIG — Using String Session (no phone login needed)
# ==========================
API_ID = 16996248
API_HASH = "00505c7ecb5d84fc463e7e1839d40fb4"

# 🔑 Your saved session string
SESSION_STRING = (
    "1BVtsOKEBu5gbNLapDxhWWsLeu-4RPelgFxcv3pY7FdKdzxepSMrSh5MS8_atvJPeDobEU370OQESOjOgOwIFwpjI7s-MbbREffIse86OpVpjfhkRD0SFo0FkZ_3bpyBfvw-umau2B9bR7_dKhfBFTXlHI0F4Sj0VNs3-jY17vNDWnFgBOty8K0o0sg-vC-a5uNQjNCSPqAjmT9bwUyl-MkGmEH9aKJBZdpVgzmNwmVfxaBpcGsmlPPqwTszHRYwp9ptpTIFIP3u9QlgI7uFUJUDEogInyQabkVXFF_rJOavj5Rd5T2wwZ6zHlti7hbBGoRRkyEIA94fwxWDuVp2hyycinaYeDXA="
)

# Create Telegram client using string session
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
SESSION_NAME = "WORDLE_SOLVER_BOT"  # kept for reference, but not used with StringSession

# ==========================
# 🔤 WORD LIST & UTILITIES
# ==========================

# Math bold letters mapping for emoji parsing
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
    """Load 5-letter words from online source or local file"""
    words_file = "words_5letter.txt"
    if not os.path.exists(words_file):
        print("📥 Downloading 5-letter words...")
        try:
            # Try to get words from the attached file or online source
            if os.path.exists("attached_assets/words_alpha_1757612406771.txt"):
                # Load from attached file and filter 5-letter words
                with open("attached_assets/words_alpha_1757612406771.txt", 'r') as f:
                    all_words = [line.strip().upper() for line in f if len(line.strip()) == 5 and line.strip().isalpha()]
                # Save filtered words
                with open(words_file, 'w') as f:
                    for word in all_words:
                        f.write(word + '\n')
            else:
                # Fallback: use a smaller curated list of common 5-letter words
                # Enhanced word list with better coverage and common Wordle words
                common_words = [
                    # Optimal starting words
                    "CRANE", "SLATE", "ADIEU", "STARE", "CRISP", "AUDIO", "AROSE", "RAISE",
                    "SAINT", "PARTY", "TRUMP", "MOURN", "CLOTH", "DEMON", "FIELD", "GHOST",
                    "HULKS", "MIXER", "POWER", "QUICK", "STORM", "TWINS", "VIXEN", "WHIPS",
                    # High-frequency 5-letter words
                    "ABOUT", "ABOVE", "ABUSE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT",
                    "AFTER", "AGAIN", "AGENT", "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT",
                    "ALIEN", "ALIGN", "ALIKE", "ALIVE", "ALLOW", "ALONE", "ALONG", "ALTER",
                    "AMBER", "AMEND", "AMONG", "ANGEL", "ANGER", "ANGLE", "ANGRY", "ANKLE",
                    "APPLE", "APPLY", "ARENA", "ARGUE", "ARISE", "ARMED", "ARMOR", "ARRAY",
                    "ARROW", "ASIDE", "ASSET", "ATLAS", "AWARD", "AWARE", "BADLY", "BAKER",
                    "BASIC", "BATCH", "BEACH", "BEARD", "BEAST", "BEGAN", "BEGIN", "BEING",
                    "BELLY", "BELOW", "BENCH", "BIKES", "BILLS", "BIRDS", "BIRTH", "BLACK",
                    "BLADE", "BLAME", "BLANK", "BLAST", "BLAZE", "BLEED", "BLEND", "BLIND",
                    "BLOCK", "BLOOD", "BLOOM", "BLOWN", "BLUES", "BLUNT", "BLUSH", "BOARD",
                    "BOAST", "BOATS", "BOBBY", "BONDS", "BONES", "BONUS", "BOOST", "BOOTH",
                    "BOOTS", "BOUND", "BOXES", "BRAIN", "BRAKE", "BRAND", "BRAVE", "BREAD",
                    "BREAK", "BREED", "BRICK", "BRIDE", "BRIEF", "BRING", "BRINK", "BROAD",
                    "BROKE", "BROOK", "BROWN", "BRUSH", "BUILD", "BUILT", "BUNCH", "BURST",
                    "BUYER", "CABLE", "CACHE", "CANDY", "CARRY", "CARVE", "CATCH", "CAUSE",
                    "CHAIN", "CHAIR", "CHALK", "CHAMP", "CHART", "CHASE", "CHEAP", "CHECK",
                    "CHEEK", "CHESS", "CHEST", "CHILD", "CHINA", "CHIPS", "CHOIR", "CHOSE",
                    "CIVIC", "CIVIL", "CLAIM", "CLAMP", "CLASH", "CLASS", "CLEAN", "CLEAR",
                    "CLERK", "CLICK", "CLIFF", "CLIMB", "CLOCK", "CLOSE", "CLOUD", "CLUBS",
                    "CLUES", "COACH", "COAST", "CODES", "COINS", "COLOR", "COMBO", "COMES",
                    "COMIC", "CORAL", "CORPS", "COSTS", "COUCH", "COUGH", "COULD", "COUNT",
                    "COURT", "COVER", "CRACK", "CRAFT", "CRANE", "CRASH", "CRAZY", "CREAM",
                    "CREEK", "CRIME", "CRISP", "CROPS", "CROSS", "CROWD", "CROWN", "CRUDE",
                    "CRUSH", "CURVE", "CYBER", "CYCLE", "DAILY", "DAIRY", "DANCE", "DATED",
                    "DEALS", "DEALT", "DEATH", "DEBIT", "DEBUG", "DEBUT", "DELAY", "DEMON",
                    "DENSE", "DEPOT", "DEPTH", "DERBY", "DESK", "DETER", "DEVIL", "DIARY",
                    "DICE", "DIGIT", "DIODE", "DIRTY", "DISCO", "DISK", "DITCH", "DIVER",
                    "DIZZY", "DOCK", "DOING", "DOLLS", "DOORS", "DOSES", "DOUBT", "DOUGH",
                    "DOZEN", "DRAFT", "DRAIN", "DRAKE", "DRAMA", "DRANK", "DRAW", "DREAM",
                    "DRESS", "DRILL", "DRINK", "DRIVE", "DRONE", "DROVE", "DRUMS", "DRUNK",
                    "DUCKS", "DUNES", "DUSTY", "DUTCH", "DYING", "EAGER", "EAGLE", "EARLY",
                    "EARTH", "EIGHT", "ELBOW", "ELDER", "ELECT", "ELITE", "EMPTY", "ENDED",
                    "ENEMY", "ENJOY", "ENTER", "ENTRY", "EQUAL", "ERROR", "EVENT", "EVERY",
                    "EXACT", "EXAMS", "EXCEL", "EXIST", "EXTRA", "FABLE", "FACED", "FACTS",
                    "FAILS", "FAINT", "FAIRY", "FAITH", "FALSE", "FANCY", "FARMS", "FATAL",
                    "FAULT", "FAVOR", "FEAST", "FENCE", "FEVER", "FIBER", "FIELD", "FIERY",
                    "FIFTY", "FIGHT", "FILES", "FILLS", "FILMS", "FINAL", "FINDS", "FINES",
                    "FIRED", "FIRMS", "FIRST", "FIXED", "FLAGS", "FLAME", "FLAPS", "FLASH",
                    "FLASK", "FLEET", "FLESH", "FLIES", "FLOAT", "FLOCK", "FLOOD", "FLOOR",
                    "FLOUR", "FLOWS", "FLUID", "FLUSH", "FLUTE", "FLIES", "FOAMS", "FOCAL",
                    "FOCUS", "FOLKS", "FONTS", "FOODS", "FORCE", "FORMS", "FORTH", "FORTY",
                    "FORUM", "FOUND", "FRAME", "FRANK", "FRAUD", "FRESH", "FRIED", "FRONT",
                    "FROST", "FRUIT", "FUELS", "FULLY", "FUNDS", "FUNNY", "FURRY", "FUSED",
                    "FUZZY", "GAINS", "GAMES", "GANGS", "GATES", "GEARS", "GENES", "GHOST",
                    "GIANT", "GIFTS", "GIRLS", "GIVEN", "GIVES", "GLASS", "GLIDE", "GLOBE",
                    "GLOVE", "GOALS", "GOATS", "GOING", "GOODS", "GRACE", "GRADE", "GRAIN",
                    "GRAND", "GRANT", "GRAPE", "GRAPH", "GRASP", "GRASS", "GRAVE", "GREAT",
                    "GREED", "GREEN", "GREET", "GRIEF", "GRILL", "GRIND", "GRIPS", "GROSS",
                    "GROUP", "GROWN", "GROWS", "GUARD", "GUESS", "GUEST", "GUIDE", "GUILD",
                    "GUILT", "GUITAR", "HABIT", "HALLS", "HANDS", "HANDY", "HAPPY", "HARSH",
                    "HASTE", "HASTY", "HATCH", "HAWKS", "HEADS", "HEALS", "HEARD", "HEART",
                    "HEAVY", "HEDGE", "HEELS", "HELLO", "HELPS", "HENCE", "HERBS", "HIDES",
                    "HILLS", "HINTS", "HIRED", "HOBBY", "HOLDS", "HOLES", "HONEY", "HONOR",
                    "HOOKS", "HOPES", "HORNS", "HORSE", "HOSTS", "HOTEL", "HOURS", "HOUSE",
                    "HUMAN", "HUMOR", "HURRY", "HUSKY", "ICONS", "IDEAL", "IDEAS", "IDIOM",
                    "IMAGE", "IMPLY", "INDEX", "INDIE", "INNER", "INPUT", "INTRO", "IRONS",
                    "ISSUE", "ITEMS", "IVORY", "JAPAN", "JEANS", "JELLY", "JEWEL", "JOINS",
                    "JOINT", "JOKES", "JUDGE", "JUICE", "JUMBO", "JUMPS", "KEEPS", "KICKS",
                    "KILLS", "KINDS", "KINGS", "KNIFE", "KNOCK", "KNOTS", "KNOWN", "KNOWS",
                    "LABEL", "LACKS", "LAKES", "LAMPS", "LANCE", "LANDS", "LANES", "LARGE",
                    "LASER", "LASTS", "LATER", "LAUGH", "LAYER", "LEADS", "LEAKS", "LEARN",
                    "LEASE", "LEAST", "LEAVE", "LEDGE", "LEFTS", "LEGAL", "LEMON", "LEVEL",
                    "LEVER", "LEWIS", "LIGHT", "LIKES", "LIMIT", "LINED", "LINES", "LINKS",
                    "LIONS", "LISTS", "LIVED", "LIVER", "LIVES", "LOADS", "LOANS", "LOBBY",
                    "LOCAL", "LOCKS", "LODGE", "LOGIC", "LOGOS", "LOOKS", "LOOPS", "LOOSE",
                    "LORDS", "LOSES", "LOVED", "LOVER", "LOVES", "LOWER", "LOYAL", "LUCKY",
                    "LUMPS", "LUNCH", "LUNGS", "LYING", "LYNCH", "MAGIC", "MAJOR", "MAKER",
                    "MAKES", "MALES", "MANGO", "MAPLE", "MARCH", "MARIA", "MARKS", "MARRY",
                    "MARSH", "MASKS", "MATCH", "MATES", "MAYBE", "MAYOR", "MEALS", "MEANS",
                    "MEANT", "MEATS", "MEDAL", "MEDIA", "MEETS", "MELON", "MELTS", "MERCY",
                    "MERGE", "MERIT", "MERRY", "METAL", "METER", "MICE", "MICRO", "MIGHT",
                    "MILES", "MILLS", "MINDS", "MINES", "MINOR", "MINUS", "MIXED", "MIXER",
                    "MIXES", "MODAL", "MODEL", "MODES", "MOIST", "MOLDY", "MONEY", "MONKS",
                    "MONTH", "MOODS", "MORAL", "MOTOR", "MOTTO", "MOULD", "MOUND", "MOUNT",
                    "MOUSE", "MOUTH", "MOVED", "MOVES", "MOVIE", "MOWER", "MUDDY", "MULTI",
                    "MUMBO", "MUSIC", "MYTHS", "NAILS", "NAKED", "NAMED", "NAMES", "NASTY",
                    "NAVAL", "NECKS", "NEEDS", "NERVE", "NEVER", "NEWLY", "NEXUS", "NICER",
                    "NIGHT", "NINTH", "NOBLE", "NODES", "NOISE", "NORKA", "NORTH", "NOSES",
                    "NOTCH", "NOTED", "NOTES", "NOVEL", "NURSE", "NUTTY", "NYLON", "OASIS",
                    "OATHS", "OCCUR", "OCEAN", "ODDS", "OFFER", "OFTEN", "OLDER", "OLIVE",
                    "OMEGA", "ONION", "OPENS", "OPERA", "ORBIT", "ORDER", "ORGAN", "OTHER",
                    "OUGHT", "OUNCE", "OUTER", "OWNED", "OWNER", "PACED", "PACKS", "PAGES",
                    "PAINS", "PAINT", "PAIRS", "PALACE", "PALMS", "PANEL", "PANIC", "PAPER",
                    "PARKS", "PARTS", "PARTY", "PASTA", "PASTE", "PATCH", "PATHS", "PATIO",
                    "PAUSE", "PEACE", "PEACH", "PEAKS", "PEARL", "PEDAL", "PENNY", "PERCH",
                    "PHASE", "PHONE", "PHOTO", "PIANO", "PICKS", "PIECE", "PILOT", "PINCH",
                    "PIPES", "PITCH", "PIXEL", "PIZZA", "PLACE", "PLAIN", "PLANE", "PLANS",
                    "PLANT", "PLATE", "PLAYS", "PLAZA", "POEMS", "POETS", "POINT", "POLES",
                    "POLLS", "POOLS", "PORCH", "PORTS", "POSTS", "POUCH", "POUND", "POWER",
                    "PRESS", "PRICE", "PRIDE", "PRIME", "PRINT", "PRIOR", "PRIZE", "PROBE",
                    "PROOF", "PROPS", "PROUD", "PROVE", "PROXY", "PULSE", "PUMPS", "PUNCH",
                    "PUPIL", "PURSE", "PUSHY", "PUTTY", "QUEEN", "QUERY", "QUEST", "QUEUE",
                    "QUICK", "QUIET", "QUILT", "QUITE", "QUOTE", "RACES", "RACKS", "RADAR",
                    "RADIO", "RAILS", "RAINS", "RAISE", "RALLY", "RANCH", "RANGE", "RANKS",
                    "RAPID", "RATES", "RATIO", "REACH", "READS", "READY", "REALM", "REBEL",
                    "RECAP", "REFER", "REGEX", "RELAX", "RELAY", "REMIX", "REPLY", "RESET",
                    "RIDER", "RIDES", "RIDGE", "RIGHT", "RIGID", "RINGS", "RISKS", "RIVAL",
                    "RIVER", "ROADS", "ROAST", "ROBES", "ROBOT", "ROCKS", "ROCKY", "ROLES",
                    "ROLLS", "ROMAN", "ROOMS", "ROOTS", "ROPES", "ROSES", "ROTTY", "ROUGH",
                    "ROUND", "ROUTE", "ROVER", "ROYAL", "RUGBY", "RUINS", "RULED", "RULER",
                    "RULES", "RUMOR", "RURAL", "RUSTY", "SADLY", "SAFER", "SAILS", "SAINT",
                    "SALAD", "SALES", "SALON", "SANDY", "SAUCE", "SAVES", "SCALE", "SCAMP",
                    "SCANS", "SCARE", "SCENE", "SCENT", "SCOPE", "SCORE", "SCOUT", "SCRAP",
                    "SEALS", "SEATS", "SEEDS", "SEEKS", "SEEMS", "SELLS", "SENDS", "SENSE",
                    "SERVE", "SETUP", "SEVEN", "SHADE", "SHAKE", "SHALL", "SHAME", "SHAPE",
                    "SHARE", "SHARK", "SHARP", "SHAVE", "SHEEP", "SHEET", "SHELF", "SHELL",
                    "SHIFT", "SHINE", "SHIPS", "SHIRT", "SHOCK", "SHOES", "SHOOT", "SHOPS",
                    "SHORT", "SHOTS", "SHOWN", "SHOWS", "SHRUG", "SIDED", "SIDES", "SIGHT",
                    "SIGNS", "SILLY", "SIMON", "SINCE", "SINGS", "SIXTH", "SIXTY", "SIZED",
                    "SIZES", "SKILL", "SKINS", "SKIPS", "SKULL", "SLACK", "SLANT", "SLATE",
                    "SLAVE", "SLEEP", "SLICE", "SLIDE", "SLOPE", "SLOTS", "SLUMP", "SMALL",
                    "SMART", "SMELL", "SMILE", "SMOKE", "SNAKE", "SNAPS", "SNEAK", "SNOWY",
                    "SOCKS", "SOLAR", "SOLID", "SOLVE", "SONGS", "SONIC", "SORRY", "SORTS",
                    "SOULS", "SOUND", "SOUTH", "SPACE", "SPARE", "SPARK", "SPEAK", "SPECS",
                    "SPEED", "SPELL", "SPEND", "SPENT", "SPICE", "SPINE", "SPLIT", "SPOKE",
                    "SPOON", "SPORT", "SPOTS", "SPRAY", "SQUAD", "STAGE", "STAIN", "STAKE",
                    "STAMP", "STAND", "STARE", "STARK", "START", "STATE", "STAYS", "STEAL",
                    "STEAM", "STEEL", "STEEP", "STEER", "STEMS", "STEPS", "STERN", "STICK",
                    "STILL", "STING", "STINK", "STOCK", "STOMP", "STONE", "STOOD", "STOOL",
                    "STOPS", "STORE", "STORM", "STORY", "STRIP", "STUCK", "STUDY", "STUFF",
                    "STYLE", "SUGAR", "SUITE", "SUNNY", "SUPER", "SURGE", "SWAMP", "SWAPS",
                    "SWEAR", "SWEAT", "SWEEP", "SWEET", "SWEPT", "SWIFT", "SWING", "SWISS",
                    "SWORD", "SWORN", "TABLE", "TACIT", "TAKEN", "TAKES", "TALES", "TALKS",
                    "TANKS", "TAPES", "TASKS", "TASTE", "TAXES", "TEACH", "TEAMS", "TEARS",
                    "TEENS", "TEETH", "TELLS", "TEMPO", "TENDS", "TENOR", "TENSE", "TENTH",
                    "TERMS", "TESTS", "TEXTS", "THANK", "THEFT", "THEIR", "THEME", "THERE",
                    "THESE", "THICK", "THIEF", "THING", "THINK", "THIRD", "THOSE", "THREE",
                    "THREW", "THROW", "THUMB", "THUGS", "TIGER", "TIGHT", "TILES", "TIMER",
                    "TIMES", "TIRED", "TITLE", "TODAY", "TOKEN", "TOMBS", "TONES", "TOOLS",
                    "TOOTH", "TOPIC", "TORCH", "TOTAL", "TOUCH", "TOUGH", "TOURS", "TOWEL",
                    "TOWER", "TOWNS", "TOXIC", "TOYS", "TRACK", "TRADE", "TRAIL", "TRAIN",
                    "TRAIT", "TRASH", "TREAT", "TREES", "TREND", "TRIAL", "TRIBE", "TRICK",
                    "TRIED", "TRIES", "TRIPS", "TRUCK", "TRULY", "TRUNK", "TRUST", "TRUTH",
                    "TUBES", "TUNES", "TURNS", "TWEET", "TWICE", "TWINS", "TWIST", "TYPED",
                    "TYPES", "ULTRA", "UNCLE", "UNDER", "UNION", "UNITS", "UNITY", "UNTIL",
                    "UPPER", "UPSET", "URBAN", "URGED", "USAGE", "USERS", "USES", "USUAL",
                    "VALID", "VALUE", "VAPOR", "VAULT", "VEINS", "VENUE", "VERSE", "VIDEO",
                    "VIEWS", "VINYL", "VIRAL", "VIRUS", "VISIT", "VITAL", "VOCAL", "VOICE",
                    "VOID", "VOGUE", "VOTES", "WAGES", "WAIST", "WAITS", "WAKE", "WALKS",
                    "WALLS", "WANTS", "WARD", "WARM", "WARNS", "WASTE", "WATCH", "WATER",
                    "WAVES", "WAYS", "WEAK", "WEAR", "WEIRD", "WELLS", "WELSH", "WENT",
                    "WERE", "WEST", "WHAT", "WHEAT", "WHEEL", "WHERE", "WHICH", "WHILE",
                    "WHITE", "WHOLE", "WHOSE", "WIDER", "WIDOW", "WIDTH", "WIELD", "WILDE",
                    "WINDS", "WINES", "WINGS", "WIPES", "WIRED", "WIRES", "WITCH", "WIVES",
                    "WOMAN", "WOMEN", "WOODS", "WORDS", "WORKS", "WORLD", "WORRY", "WORSE",
                    "WORST", "WORTH", "WOULD", "WOUND", "WOVEN", "WRITE", "WRONG", "WROTE",
                    "YARDS", "YEARS", "YEAST", "YIELD", "YOUNG", "YOURS", "YOUTH", "ZEBRA",
                    "ZESTS", "ZONES", "ZOOMS"
                ]
                with open(words_file, 'w') as f:
                    for word in common_words:
                        f.write(word + '\n')
        except Exception as e:
            print(f"❌ Error loading words: {e}")
            return []

    # Read the words file
    try:
        with open(words_file, 'r', encoding='utf-8', errors='ignore') as f:
            words = [line.strip().upper() for line in f if len(line.strip()) == 5 and line.strip().isalpha()]
        print(f"📚 Loaded {len(words)} 5-letter words")
        return words
    except Exception as e:
        print(f"❌ Error reading words file: {e}")
        return []

WORDS = load_words()

# ==========================
# 🧠 FAST WORDLE SOLVER
# ==========================

class FastWordleSolver:
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset solver state for a new game"""
        self.fixed = {}
        self.forbidden = {}
        self.min_cnt = {}
        self.max_cnt = {}
        self.known = set()
        self.candidates = WORDS.copy()
        self.guess_count = 0

    def clean_word(self, w):
        """Extract clean 5-letter word from text"""
        # Convert mathematical bold letters first
        cleaned = ''.join(MATH_BOLD_MAP.get(c, c) for c in w)
        # Keep only ASCII letters
        cleaned = ''.join(c for c in cleaned if c.isascii() and c.isalpha()).upper()
        return cleaned[:5] if len(cleaned) >= 5 else cleaned

    def emoji_to_pattern(self, text):
        """Convert emoji feedback to pattern (G/Y/B)"""
        # Support multiple emoji variants commonly used in Wordle bots
        emoji_map = {
            '🟩': 'G',  # Green square (correct letter, correct position)
            '🟨': 'Y',  # Yellow square (correct letter, wrong position)
            '🟥': 'B',  # Red square (wrong letter)
            '⬛': 'B',  # Black square (wrong letter)
            '⬜': 'B',  # White square (wrong letter)
            '⬛️': 'B',  # Black square with variation selector
            '⬜️': 'B',  # White square with variation selector
            '🟫': 'B',  # Brown square (wrong letter)
        }
        pattern = ""
        for char in text:
            if char in emoji_map:
                pattern += emoji_map[char]
                if len(pattern) == 5:
                    break
        return pattern if len(pattern) == 5 else None

    def parse_feedback(self, text):
        """Parse feedback message to extract word and pattern (get latest line)"""
        lines = text.splitlines()
        # Process lines in REVERSE to get the most recent guess first
        for line in reversed(lines):
            # Get pattern from emojis
            pattern = self.emoji_to_pattern(line)
            if not pattern:
                continue
            # Extract word - try different approaches
            word = None
            # Method 1: Look for word at end of line
            parts = line.split()
            for part in reversed(parts):
                candidate = self.clean_word(part)
                if len(candidate) == 5:
                    word = candidate
                    break
            # Method 2: Extract all letters from end of string
            if not word:
                all_letters = ''.join(
                    MATH_BOLD_MAP.get(c, c) for c in line 
                    if c.isalpha() or c in MATH_BOLD_MAP
                )
                all_letters = ''.join(c for c in all_letters if c.isascii()).upper()
                if len(all_letters) >= 5:
                    word = all_letters[-5:]
            if word and len(word) == 5:
                return word, pattern
        return None, None

    def process_feedback(self, guess, pattern):
        """Update solver state based on guess and feedback pattern"""
        self.guess_count += 1
        greens = []
        yellows = []
        greys = []
        for i, (p, ch) in enumerate(zip(pattern, guess)):
            if p == "G":
                greens.append((i, ch))
                self.known.add(ch)
            elif p == "Y":
                yellows.append((i, ch))
                self.known.add(ch)
            else:  # B (grey)
                greys.append((i, ch))

        # Update fixed positions (green letters)
        for i, ch in greens:
            self.fixed[i] = ch

        # Update forbidden positions (yellow and grey letters)
        for i, ch in yellows + greys:
            if i not in self.forbidden:
                self.forbidden[i] = set()
            self.forbidden[i].add(ch)

        # Count green and yellow letters
        gy_count = Counter(ch for _, ch in greens + yellows)

        # Update minimum counts (from greens and yellows)
        for ch, cnt in gy_count.items():
            self.min_cnt[ch] = max(self.min_cnt.get(ch, 0), cnt)

        # Update maximum counts (from greys)
        for i, ch in greys:
            if ch not in self.known:  # Letter not in word at all
                self.max_cnt[ch] = 0
            else:  # Letter in word but not in this position
                current_min = self.min_cnt.get(ch, 0)
                self.max_cnt[ch] = max(0, current_min)

        # Filter candidates
        self.candidates = [w for w in self.candidates if self.is_valid_word(w)]

    def is_valid_word(self, word):
        """Check if word matches current constraints"""
        # Check fixed positions
        for i, ch in self.fixed.items():
            if word[i] != ch:
                return False
        # Check forbidden positions
        for i in range(5):
            if i in self.forbidden and word[i] in self.forbidden[i]:
                return False
        # Check letter counts
        word_count = Counter(word)
        # Minimum counts
        for ch, min_cnt in self.min_cnt.items():
            if word_count.get(ch, 0) < min_cnt:
                return False
        # Maximum counts
        for ch, max_cnt in self.max_cnt.items():
            if word_count.get(ch, 0) > max_cnt:
                return False
        return True

    def get_next_guess(self):
        """Get the best next guess"""
        if not self.candidates:
            return None
        # For first guess, use proven starters with high vowel/consonant coverage
        if self.guess_count == 0:
            starters = [
                "CRANE", "SLATE", "ADIEU", "STARE", "CRISP", "AUDIO", 
                "AROSE", "RAISE", "SAINT", "PARTY", "TRUMP", "MOURN",
                "CLOTH", "DEMON", "FIELD", "GHOST", "HULKS", "MIXER",
                "POWER", "QUICK", "STORM", "TWINS", "VIXEN", "WHIPS"
            ]
            for starter in starters:
                if starter in self.candidates:
                    return starter
        # Return first valid candidate
        return self.candidates[0]

    def is_solved(self, pattern):
        """Check if the game is solved (all green)"""
        return pattern and len(pattern) == 5 and all(c == 'G' for c in pattern)

# ==========================
# 🤖 TELEGRAM BOT
# ==========================

# Global variables for bot state
# client = TelegramClient(SESSION_NAME, API_ID, API_HASH)  # ❌ DELETED - This was causing the error!
solver = FastWordleSolver()
is_active = False
target_chat_id = None
games_to_solve = 0
games_solved = 0
current_game_state = "waiting"  # waiting, guessing, solved, failed
last_sent_guess = None  # Track last guess to avoid duplicates
last_processed_message = None  # Track last processed feedback
processed_words = set()  # Track which word feedback we've already processed
auto_start_enabled = True  # Auto-start after reboot
rate_limit_delay = 3.0  # Delay between guesses to avoid flooding
last_request_time = 0
blocked_until = 0  # Timestamp when bot will be unblocked
uptime_start = None  # Track uptime
health_status = "healthy"

def reset_session():
    """Reset the solving session"""
    global is_active, target_chat_id, games_to_solve, games_solved, current_game_state, last_sent_guess, last_processed_message, processed_words
    is_active = False
    target_chat_id = None
    games_to_solve = 0
    games_solved = 0
    current_game_state = "waiting"
    last_sent_guess = None
    last_processed_message = None
    processed_words.clear()
    solver.reset()

async def intelligent_delay():
    """Smart delay system to avoid rate limiting"""
    global last_request_time, rate_limit_delay, blocked_until
    current_time = time.time()
    # If we're blocked, wait until unblock time
    if blocked_until > current_time:
        wait_time = blocked_until - current_time
        print(f"⏰ Waiting {int(wait_time)} seconds until unblocked...")
        await asyncio.sleep(wait_time)
        blocked_until = 0
        print("🟢 Unblocked! Resuming operations...")
    # Smart delay based on request frequency
    time_since_last = current_time - last_request_time
    if time_since_last < rate_limit_delay:
        delay = rate_limit_delay - time_since_last
        await asyncio.sleep(delay)
    last_request_time = time.time()

async def handle_rate_limit_block():
    """Handle rate limiting and blocking"""
    global blocked_until, rate_limit_delay, health_status
    print("🚫 Rate limit detected! Implementing backoff strategy...")
    # Set block time (20 minutes as mentioned in error)
    blocked_until = time.time() + (20 * 60)  # 20 minutes
    # Increase delay for future requests
    rate_limit_delay = min(rate_limit_delay * 1.5, 10.0)  # Max 10 seconds
    health_status = "rate_limited"
    print(f"⏰ Blocked for 20 minutes. New delay: {rate_limit_delay:.1f}s")
    print(f"🕐 Will resume at: {datetime.fromtimestamp(blocked_until).strftime('%H:%M:%S')}")

def keep_alive_ping():
    """Keep-alive function to maintain connection"""
    try:
        # Simple HTTP request to keep the service alive
        requests.get("http://localhost:5000/ping", timeout=5)
    except:
        pass  # Ignore errors in keep-alive

async def auto_recovery_check():
    """Auto-recovery system for 24/7 operation"""
    global health_status, blocked_until, rate_limit_delay
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            current_time = time.time()
            # Reset health if we're no longer blocked
            if blocked_until < current_time and health_status == "rate_limited":
                health_status = "healthy"
                rate_limit_delay = max(3.0, rate_limit_delay * 0.8)  # Gradually reduce delay
                print("💚 Health status restored: healthy")
            # Keep-alive ping
            keep_alive_ping()
        except Exception as e:
            print(f"⚠️ Auto-recovery error: {e}")

@client.on(events.NewMessage(pattern=r'/new(?:\s+(\d+))?'))
async def handle_new_command(event):
    """Handle /new and /new [number] commands"""
    global is_active, target_chat_id, games_to_solve, games_solved, current_game_state
    try:
        match = re.match(r'/new(?:\s+(\d+))?', event.raw_text)
        if not match:
            return
        count_str = match.group(1)
        count = int(count_str) if count_str else 1
        if count < 1:
            await event.reply("❌ Number must be positive!")
            return
        if count > 1000:
            await event.reply("❌ Too many games! Max 1000.")
            return
        if is_active:
            return
        # Start solving session
        is_active = True
        target_chat_id = event.chat_id
        games_to_solve = count
        games_solved = 0
        current_game_state = "waiting"
        # Start solving immediately - no /end or /new commands
        print(f"🎯 Starting {count} game(s)...")
        await start_new_game()
    except Exception as e:
        await event.reply(f"⚠️ Error: {str(e)}")
        reset_session()

@client.on(events.NewMessage(pattern='/stop'))
async def handle_stop_command(event):
    """Handle /stop command"""
    global is_active
    if not is_active:
        return
    reset_session()

@client.on(events.NewMessage(pattern='/status'))
async def handle_status_command(event):
    """Handle /status command"""
    if not is_active:
        await event.reply(f"Idle (Words: {len(WORDS)})")
    else:
        status = f"Active: {games_solved}/{games_to_solve} | Guesses: {solver.guess_count} | Candidates: {len(solver.candidates)}"
        await event.reply(status)

@client.on(events.NewMessage(pattern=r'\+reboot'))
async def handle_reboot_command(event):
    """Handle +reboot command to restart the bot"""
    try:
        print("🔄 Reboot command received - restarting bot...")
        await event.reply("🔄 Rebooting userbot... Will be back online in a few seconds!")
        # Give time for the message to send
        await asyncio.sleep(1)
        # Force restart the process - Replit deployment will automatically restart it
        print("⚡ Executing bot restart...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Reboot error: {e}")
        await event.reply(f"⚠️ Reboot failed: {str(e)}")

async def start_new_game():
    """Start a new game"""
    global current_game_state, last_sent_guess, processed_words
    solver.reset()
    processed_words.clear()  # Clear processed words for new game
    current_game_state = "guessing"
    first_guess = solver.get_next_guess()
    if first_guess:
        last_sent_guess = first_guess  # Important: Track the first guess
        # Don't pre-add to processed_words - let feedback processing handle it
        await intelligent_delay()
        await client.send_message(target_chat_id, first_guess)
        print(f"🎯 Game {games_solved + 1}: Started with '{first_guess}'")
    else:
        print("❌ No words available for guessing!")
        await handle_game_finished(success=False)

@client.on(events.NewMessage)
async def handle_game_response(event):
    """Handle responses from the game"""
    global is_active, target_chat_id, current_game_state, last_sent_guess, last_processed_message
    if not is_active or event.chat_id != target_chat_id:
        return
    if current_game_state != "guessing":
        return

    # Handle game state messages
    text = event.raw_text.lower()

    # Handle game completion messages first
    if ("congrats" in text and "guessed it correctly" in text) or \
       ("correct" in text and "leaderboard" in text) or \
       ("start with /new" in text):
        print("🎉 Game completed successfully!")
        await handle_game_finished(success=True)
        return

    # Handle "already in progress" message - continue with current game
    if "already a game in progress" in text:
        print("🔄 Game already in progress, continuing...")
        return

    # Handle "already guessed" message - continue with next candidate
    if "someone has already guessed" in text or "already guessed" in text:
        print("⚠️ Word already guessed, getting next candidate...")
        # Remove the rejected word from candidates
        if last_sent_guess and last_sent_guess in solver.candidates:
            solver.candidates.remove(last_sent_guess)
        # Get next guess and continue
        next_guess = solver.get_next_guess()
        if next_guess:
            last_sent_guess = next_guess
            # Smart delay to avoid flooding
            await intelligent_delay()
            await client.send_message(target_chat_id, next_guess)
            print(f"📤 Sent alternative: {next_guess} (candidates: {len(solver.candidates)})")
        else:
            print("😞 No more alternatives available")
            await handle_game_finished(success=False)
        return

    # Only process messages with Wordle emojis (support multiple variants)
    wordle_emojis = "🟥🟨🟩⬛⬜⬛️⬜️🟫"
    if not any(emoji in event.raw_text for emoji in wordle_emojis):
        return

    # Only avoid processing exact duplicate messages within a short timeframe
    if event.raw_text == last_processed_message:
        print(f"⚠️ Skipping exact duplicate message")
        return

    try:
        word, pattern = solver.parse_feedback(event.raw_text)
        if not word or not pattern:
            print(f"❌ Failed to parse: {event.raw_text[:50]}...")
            return

        # Only process NEW word feedback we haven't seen in THIS game
        # But always process if it's a new pattern for the same word
        word_pattern_key = f"{word}-{pattern}"
        if word_pattern_key in processed_words:
            print(f"⚠️ Already processed this exact feedback: {word} -> {pattern}")
            return

        processed_words.add(word_pattern_key)
        last_processed_message = event.raw_text
        print(f"📥 Parsed: {word} -> {pattern}")

        # Check if game is solved (all green)
        if solver.is_solved(pattern):
            print(f"🎉 Found the word: {word}!")
            await handle_game_finished(success=True)
            return

        # Process feedback and get next guess
        solver.process_feedback(word, pattern)
        next_guess = solver.get_next_guess()

        # Check for explicit game over messages (only if clearly stated)
        if "you win" in text or "correct!" in text or "well done" in text:
            await handle_game_finished(success=True)
            return
        elif "game over" in text or "you lose" in text or "the word was" in text:
            await handle_game_finished(success=False)
            return

        if next_guess:
            last_sent_guess = next_guess
            # Smart delay to avoid flooding
            await intelligent_delay()
            await client.send_message(target_chat_id, next_guess)
            print(f"📤 Sent: {next_guess} (candidates: {len(solver.candidates)})")
        else:
            print("😞 No more candidates available!")
            await handle_game_finished(success=False)

    except Exception as e:
        print(f"⚠️ Error processing response: {e}")
        # Handle flooding/blocking errors
        if "flooding" in str(e).lower() or "blocked" in str(e).lower():
            await handle_rate_limit_block()
        elif "flood" in str(e).lower():
            await handle_rate_limit_block()

async def handle_game_finished(success=True):
    """Handle when a game finishes"""
    global games_solved, current_game_state
    games_solved += 1
    if success:
        print(f"✅ Game {games_solved} solved in {solver.guess_count} guesses!")
    else:
        print(f"❌ Game {games_solved} failed after {solver.guess_count} guesses")

    # Check if we need to solve more games
    if games_solved < games_to_solve:
        current_game_state = "waiting"
        print(f"📤 Starting game {games_solved + 1}/{games_to_solve}...")
        # For bulk solving, send /new for next game
        await asyncio.sleep(1)
        await client.send_message(target_chat_id, "/new")
        await asyncio.sleep(1)
        # Start solving next game
        await start_new_game()
    else:
        # All games completed - reset silently
        reset_session()

# ==========================
# 🌐 FLASK WEB SERVER (for 24/7 hosting)
# ==========================

app = Flask(__name__)

@app.route('/')
def home():
    """Health check endpoint"""
    global uptime_start, health_status
    uptime_seconds = int(time.time() - uptime_start) if uptime_start else 0
    uptime_hours = uptime_seconds // 3600
    uptime_minutes = (uptime_seconds % 3600) // 60
    is_blocked = blocked_until > time.time()
    time_until_unblock = max(0, int(blocked_until - time.time())) if is_blocked else 0
    status = {
        "status": "blocked" if is_blocked else "online",
        "health": health_status,
        "bot": "Telegram Wordle Solver 24/7",
        "uptime": f"{uptime_hours}h {uptime_minutes}m",
        "uptime_seconds": uptime_seconds,
        "is_active": is_active,
        "games_solved": games_solved,
        "games_to_solve": games_to_solve,
        "words_loaded": len(WORDS),
        "is_blocked": is_blocked,
        "unblock_in_seconds": time_until_unblock,
        "rate_limit_delay": rate_limit_delay,
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(status)

@app.route('/health')
def health():
    """Detailed health check"""
    global uptime_start, health_status
    is_blocked = blocked_until > time.time()
    return jsonify({
        "healthy": health_status == "healthy" and not is_blocked,
        "status": health_status,
        "uptime_start": uptime_start,
        "is_blocked": is_blocked,
        "blocked_until": blocked_until if is_blocked else None,
        "solver_active": is_active,
        "version": "2.1-24/7",
        "features": ["auto_restart", "rate_limiting", "flood_protection", "health_monitoring"]
    })

@app.route('/ping')
def ping():
    """Simple ping endpoint for uptime monitoring"""
    return "pong", 200

@app.route('/stats')
def stats():
    """Detailed statistics"""
    return jsonify({
        "total_games_solved": games_solved,
        "current_session_games": games_to_solve,
        "solver_candidates": len(solver.candidates) if solver else 0,
        "guess_count": solver.guess_count if solver else 0,
        "database_size": len(WORDS),
        "last_request_time": last_request_time,
        "rate_limit_delay": rate_limit_delay
    })

def run_flask_server():
    """Run Flask server in background thread"""
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"⚠️ Flask server error: {e}")

# ==========================
# 🚀 MAIN
# ==========================

async def main():
    """Main function"""
    if not WORDS:
        print("❌ No words loaded! Check your word list.")
        return

    try:
        # Initialize uptime tracking
        global uptime_start, health_status
        uptime_start = time.time()
        health_status = "healthy"

        # Start Flask server in background thread for 24/7 hosting
        flask_thread = threading.Thread(target=run_flask_server, daemon=True)
        flask_thread.start()
        print("🌐 Flask server started on port 5000")

        await client.start()
        print("✅ Telegram Wordle Bot Ready! (24/7 Enhanced)")
        print("📋 Commands:")
        print("   /new - Start solving one game")
        print("   /new [number] - Solve multiple games")
        print("   /stop - Stop current solving session")
        print("   /status - Show current status")
        print("   +reboot - Restart the bot (24/7 hosting)")
        print("🌐 Web interface: http://0.0.0.0:5000")
        print("🛡️ Features: Rate limiting, Auto-recovery, Health monitoring")

        # Start auto-recovery system in background
        recovery_task = asyncio.create_task(auto_recovery_check())
        print("🔄 Auto-recovery system started")

        # Auto-start functionality after reboot
        if auto_start_enabled and os.getenv('AUTO_START_GAMES'):
            try:
                games_count = int(os.getenv('AUTO_START_GAMES', '1'))
                print(f"🚀 Auto-starting {games_count} games after reboot...")
                # Simulate /new command for auto-start
                global is_active, target_chat_id, games_to_solve, games_solved, current_game_state
                is_active = True
                target_chat_id = int(os.getenv('AUTO_TARGET_CHAT_ID', '7061016027'))  # WordSeek bot
                games_to_solve = games_count
                games_solved = 0
                current_game_state = "waiting"
                await start_new_game()
            except Exception as e:
                print(f"⚠️ Auto-start failed: {e}")

        await client.run_until_disconnected()

    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
