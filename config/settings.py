import os

# --- Environment detection ---
IS_CI = os.getenv("CI", "false").lower() == "true"
FETCH_HISTORY_IN_CI = os.getenv("FETCH_HISTORY_IN_CI", "false").lower() == "true"

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

SYMBOLS_CSV = os.path.join(DATA_DIR, "symbols.csv")
SYMBOLS_JSON = os.path.join(DATA_DIR, "symbols.json")
INDICATORS_CSV = os.path.join(DATA_DIR, "indicators.csv")
TOP10_CSV = os.path.join(OUTPUT_DIR, "top10_initial.csv")
DECISION_REPORT_CSV = os.path.join(OUTPUT_DIR, "decision_report.csv")

# --- Data source ---
LIVE_DATA_URL = "https://tradersarena.ir/data/mainwatch/symbols"

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Screening thresholds ---
TOP_N = 35
MIN_SCORE = 0

# --- Decision engine thresholds ---
ENTRY_CANDIDATE_SCORE = 75
ENTRY_CANDIDATE_TREND = 4
ENTRY_CANDIDATE_RSI_LOW = 45
ENTRY_CANDIDATE_RSI_HIGH = 70
ENTRY_CANDIDATE_VOL_RATIO = 1.2

OVERBOUGHT_RSI = 80
PULLBACK_RSI_LOW = 70
PULLBACK_RSI_HIGH = 80

# --- History staleness warning (days) ---
STALE_HISTORY_DAYS = 5

# --- Telegram message max length ---
TELEGRAM_MAX_CHARS = 4000