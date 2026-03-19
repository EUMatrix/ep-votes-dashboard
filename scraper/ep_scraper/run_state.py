"""JSON-based progress tracking for Dorian scraper runs."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from ep_scraper.config import STATE_FILE

log = logging.getLogger(__name__)


def read_state() -> dict:
    """Read the current run state from *run_state.json*.

    Returns an empty dict if the file doesn't exist yet.
    """
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Could not read state file: %s", e)
        return {}


def write_state(step: str, data: dict | None = None) -> None:
    """Update or insert a run-state entry for *step*.

    The *data* dict is merged into the step's existing entry (if any).
    A ``last_run_at`` timestamp is always added automatically.
    """
    state = read_state()
    entry = state.get(step, {})
    if data:
        entry.update(data)
    entry["last_run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state[step] = entry
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Updated run state: step=%s %s", step, entry)
