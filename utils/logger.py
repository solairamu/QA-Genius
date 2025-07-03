import logging
import os
from pathlib import Path

# --- Log directory & file ---
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "qa_genius.log"

# Ensure log folder exists
os.makedirs(LOG_DIR, exist_ok=True)

# --- Logging Format ---
LOG_FORMAT = "[%(asctime)s] %(levelname)s — %(name)s — %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Configure Root Logger ---
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler()  # Also logs to console
    ]
)

# Usage: import this file and create named loggers
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)