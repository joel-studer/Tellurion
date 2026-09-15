"""FUTURE-ONLY session-calendar wrapper.

USE pandas_market_calendars for XNYS (same package the frozen lane
qualifies, but this wrapper is future-only and independent).
WRAP exchange_calendars for multi-venue breadth behind an availability
probe. Unknown venues stay UNKNOWN (never guessed).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def pandas_mc_available() -> bool:
    try:
        import pandas_market_calendars  # noqa: F401
        return True
    except Exception:
        return False


def exchange_calendars_available() -> bool:
    try:
        import exchange_calendars  # noqa: F401
        return True
    except Exception:
        return False


def xnys_session(day: str) -> Dict[str, Any]:
    """XNYS day classification via pandas_market_calendars (or UNKNOWN)."""
    if not pandas_mc_available():
        return {"venue": "XNYS", "day": day, "state": "UNKNOWN",
                "basis": "UNKNOWN", "note": "pandas_market_calendars absent"}
    import pandas_market_calendars as mcal
    cal = mcal.get_calendar("XNYS")
    try:
        import pandas as pd
        ts = pd.Timestamp(day)
        sched = cal.schedule(start_date=ts, end_date=ts)
        if sched.empty:
            return {"venue": "XNYS", "day": day, "state": "CLOSED",
                    "basis": "OBSERVED", "note": "no session (holiday/weekend)"}
        return {"venue": "XNYS", "day": day, "state": "REGULAR",
                "basis": "OBSERVED",
                "open": str(sched.iloc[0]["market_open"]),
                "close": str(sched.iloc[0]["market_close"])}
    except Exception as e:
        return {"venue": "XNYS", "day": day, "state": "UNKNOWN",
                "basis": "UNKNOWN", "note": f"calendar error: {type(e).__name__}"}


def venue_session_xcals(mic: str, day: str) -> Dict[str, Any]:
    """Breadth helper via exchange_calendars MIC (or UNKNOWN when absent)."""
    if not exchange_calendars_available():
        return {"venue": mic, "day": day, "state": "UNKNOWN",
                "basis": "UNKNOWN", "note": "exchange_calendars absent"}
    try:
        import exchange_calendars as xcals
        cal = xcals.get_calendar(mic)
        import pandas as pd
        ts = pd.Timestamp(day)
        sess = cal.is_session(ts)
        return {"venue": mic, "day": day,
                "state": "REGULAR" if bool(sess) else "CLOSED",
                "basis": "OBSERVED", "note": "exchange_calendars"}
    except Exception as e:
        return {"venue": mic, "day": day, "state": "UNKNOWN",
                "basis": "UNKNOWN", "note": f"calendar error: {type(e).__name__}"}
