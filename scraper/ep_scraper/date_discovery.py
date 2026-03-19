"""Discover plenary dates with unprocessed VOT XML files."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta

import requests

from ep_scraper.config import (
    CACHE_DIR, HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT,
    TERM_START, VOT_XML_URL,
)

log = logging.getLogger(__name__)


def _vot_url(d: date) -> str:
    return VOT_XML_URL.format(date=d.strftime("%Y-%m-%d"))


def _check_vot_exists(d: date, session: requests.Session) -> bool:
    """Return True if a VOT XML exists for this date (HTTP 200)."""
    url = _vot_url(d)
    try:
        r = session.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return r.status_code == 200
    except requests.RequestException:
        return False


def fetch_vot_xml(d: date, session: requests.Session | None = None) -> str | None:
    """Download VOT XML for a date.  Returns XML string or None.

    Results are cached to disk under ``cache/``.
    """
    cache_file = CACHE_DIR / f"PV-10-{d.strftime('%Y-%m-%d')}-VOT_EN.xml"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)

    url = _vot_url(d)
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200 and r.text.strip().startswith("<?xml"):
            cache_file.write_text(r.text, encoding="utf-8")
            log.info("Downloaded VOT XML for %s (%d bytes)", d, len(r.text))
            return r.text
        log.debug("No VOT XML for %s (status %d)", d, r.status_code)
        return None
    except requests.RequestException as e:
        log.warning("Failed to fetch VOT XML for %s: %s", d, e)
        return None


def discover_new_dates(
    existing_dates: set[str],
    start: date | None = None,
    end: date | None = None,
) -> list[date]:
    """Find plenary dates that have VOT XML but are not yet in the database.

    Args:
        existing_dates: Set of ``YYYY-MM-DD`` strings already processed.
        start: Earliest date to check (default: TERM_START).
        end: Latest date to check (default: today).

    Returns:
        Sorted list of new dates.
    """
    if start is None:
        start = datetime.strptime(TERM_START, "%Y-%m-%d").date()
    if end is None:
        end = date.today()

    session = requests.Session()
    session.headers.update(HEADERS)

    new_dates: list[date] = []
    d = start
    while d <= end:
        if d.weekday() >= 5:          # skip weekends
            d += timedelta(days=1)
            continue

        date_str = d.strftime("%Y-%m-%d")
        if date_str in existing_dates:
            d += timedelta(days=1)
            continue

        if _check_vot_exists(d, session):
            log.info("Found new VOT XML for %s", date_str)
            new_dates.append(d)

        time.sleep(REQUEST_DELAY)
        d += timedelta(days=1)

    return sorted(new_dates)


def discover_recent_dates(
    existing_dates: set[str],
    lookback_days: int = 30,
) -> list[date]:
    """Check only the last *lookback_days* days for new VOT XMLs."""
    end = date.today()
    start = end - timedelta(days=lookback_days)
    return discover_new_dates(existing_dates, start=start, end=end)
