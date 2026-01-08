"""
Configuration Constants

Centralized configuration for all magic numbers and intervals.
"""

import os
from datetime import timedelta

# ============== Background Task Intervals ==============

# News fetching interval (30 minutes)
NEWS_FETCH_INTERVAL = 30 * 60  # seconds

# Telegram message fetching interval (30 minutes - increased from 15 to reduce API load)
TELEGRAM_FETCH_INTERVAL = 30 * 60  # seconds

# Recommendation generation interval (2 hours - increased from 1 to reduce load)
RECOMMENDATION_INTERVAL = 120 * 60  # seconds

# Database cleanup interval (24 hours)
CLEANUP_INTERVAL = 24 * 60 * 60  # seconds


# ============== Data Retention ==============

# Days to keep recommendations before cleanup
RECOMMENDATION_RETENTION_DAYS = 7

# Days to keep analysis records before cleanup
ANALYSIS_RETENTION_DAYS = 7

# Days to keep system logs before cleanup
LOG_RETENTION_DAYS = 3

# Days to keep fetch logs before cleanup
FETCH_LOG_RETENTION_DAYS = 3


# ============== Recommendation Engine Limits ==============

# Maximum total recommendations to keep in database
MAX_RECOMMENDATIONS = 50

# Maximum stocks to process per analysis cycle
MAX_STOCKS_PER_CYCLE = 5

# Minimum confidence threshold for recommendations
MIN_CONFIDENCE_THRESHOLD = 65.0

# Minimum message mentions required for a stock to be considered
MIN_MESSAGE_MENTIONS = 2


# ============== Telegram Configuration ==============

# Maximum retry attempts for Telegram operations
TELEGRAM_MAX_RETRIES = 3

# Base delay for exponential backoff (seconds)
TELEGRAM_BASE_DELAY = 2

# Maximum backoff delay (seconds)
TELEGRAM_MAX_DELAY = 300

# Circuit breaker settings
TELEGRAM_CIRCUIT_BREAKER_THRESHOLD = 5
TELEGRAM_CIRCUIT_BREAKER_TIMEOUT = 300  # 5 minutes


# ============== API Rate Limiting ==============

# News API request timeout (seconds)
NEWS_API_TIMEOUT = 10

# Stock API request timeout (seconds)
STOCK_API_TIMEOUT = 5

# Maximum concurrent API requests
MAX_CONCURRENT_REQUESTS = 5


# ============== Database Configuration ==============

# Query timeout (seconds)
DB_QUERY_TIMEOUT = 30

# Connection pool size
DB_POOL_SIZE = 10


# ============== Timeframes ==============

# Available recommendation timeframes
RECOMMENDATION_TIMEFRAMES = ["next_day", "next_week", "next_month", "1yr"]

# All Star Picks validity period (hours)
ALLSTAR_VALIDITY_HOURS = 24


# ============== Circuit Breaker Defaults ==============

# Default failure threshold before opening circuit
DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5

# Default timeout before attempting to close circuit (seconds)
DEFAULT_CIRCUIT_BREAKER_TIMEOUT = 60


# ============== Health Check ==============

# Maximum age for a task to be considered healthy (seconds)
TASK_HEALTH_THRESHOLD = 3600  # 1 hour

# Maximum age for Telegram connection to be considered healthy (seconds)
TELEGRAM_HEALTH_THRESHOLD = 1800  # 30 minutes


# ============== Environment Variables ==============

def get_env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.getenv(key, default)


# Telegram API credentials (from environment or database)
TELEGRAM_API_ID = get_env("TELEGRAM_API_ID")
TELEGRAM_API_HASH = get_env("TELEGRAM_API_HASH")
TELEGRAM_PHONE = get_env("TELEGRAM_PHONE")

# LLM API key
GEMINI_API_KEY = get_env("GEMINI_API_KEY")
