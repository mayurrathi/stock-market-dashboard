"""
Trading Hours Utility
Determines if Indian stock market is currently open for trading.

NSE/BSE Trading Hours (IST):
- Pre-open: 9:00 AM - 9:15 AM
- Normal Trading: 9:15 AM - 3:30 PM
- Closing Session: 3:30 PM - 4:00 PM
- Trading Days: Monday to Friday (excluding holidays)
"""

from datetime import datetime, time
import pytz

# Indian Standard Time
IST = pytz.timezone('Asia/Kolkata')

# Trading hours
MARKET_OPEN = time(9, 15)   # 9:15 AM
MARKET_CLOSE = time(15, 30)  # 3:30 PM

# Extended hours (for pre-market and closing session)
PRE_MARKET = time(9, 0)      # 9:00 AM
POST_MARKET = time(16, 0)     # 4:00 PM


def is_market_open() -> bool:
    """
    Check if Indian stock market is currently open for trading.
    Returns True during normal trading hours (9:15 AM - 3:30 PM IST) on weekdays.
    """
    now = datetime.now(IST)
    
    # Check if it's a weekday (Monday = 0, Friday = 4)
    if now.weekday() > 4:  # Saturday or Sunday
        return False
    
    current_time = now.time()
    
    # Check if within trading hours
    return MARKET_OPEN <= current_time <= MARKET_CLOSE


def is_extended_market_hours() -> bool:
    """
    Check if we're in extended market hours (pre-market or closing session).
    Returns True during 9:00 AM - 9:15 AM or 3:30 PM - 4:00 PM IST on weekdays.
    """
    now = datetime.now(IST)
    
    if now.weekday() > 4:
        return False
    
    current_time = now.time()
    
    # Pre-market or closing session
    return (PRE_MARKET <= current_time < MARKET_OPEN) or \
           (MARKET_CLOSE < current_time <= POST_MARKET)


def should_use_realtime_data() -> bool:
    """
    Determine if we should prioritize real-time data.
    Returns True during market hours or extended hours, False otherwise.
    
    During trading hours: Always try for real-time data
    Outside trading hours: Use cached data (market is closed anyway)
    """
    return is_market_open() or is_extended_market_hours()


def get_market_status() -> dict:
    """
    Get current market status with details.
    """
    now = datetime.now(IST)
    is_open = is_market_open()
    is_extended = is_extended_market_hours()
    
    if now.weekday() > 4:
        status = "Closed (Weekend)"
        next_open = "Monday 9:15 AM IST"
    elif is_open:
        status = "Open"
        next_open = None
    elif is_extended:
        current_time = now.time()
        if current_time < MARKET_OPEN:
            status = "Pre-Market"
            next_open = "9:15 AM IST"
        else:
            status = "Closing Session"
            next_open = "Tomorrow 9:15 AM IST"
    else:
        current_time = now.time()
        if current_time < PRE_MARKET:
            status = "Closed (Pre-Open)"
            next_open = "9:15 AM IST"
        else:
            status = "Closed"
            next_open = "Tomorrow 9:15 AM IST"
    
    return {
        "is_open": is_open,
        "is_extended_hours": is_extended,
        "status": status,
        "next_open": next_open,
        "current_time": now.strftime("%H:%M IST"),
        "current_date": now.strftime("%Y-%m-%d"),
        "day_of_week": now.strftime("%A"),
        "use_realtime": should_use_realtime_data()
    }
