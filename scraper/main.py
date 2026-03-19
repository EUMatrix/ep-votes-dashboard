"""CLI orchestrator for Dorian EP plenary votes metadata collection.

Usage:
    python main.py                       # Process all new dates (last 30 days)
    python main.py --date 2026-02-12     # Process specific date
    python main.py --backfill            # All dates since July 2024
    python main.py --dry-run             # Parse and display without writing
    python main.py --verbose             # Enable debug logging
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime

import requests

from ep_scraper.config import (
    COMMITTEE_POLICY_MAP,
    DEFAULT_POLICY_AREA,
    HEADERS,
)
from ep_scraper.date_discovery import (
    discover_new_dates,
    discover_recent_dates,
    fetch_vot_xml,
)
from ep_scraper.excel_writer import (
    get_existing_dates,
    get_existing_keys,
    get_last_file_number,
    get_last_vote_id,
    write_records,
)
from ep_scraper.run_state import write_state
from ep_scraper.vote_classifier import (
    build_link,
    classify_final_vote,
    classify_leg_non_bud,
    classify_subject,
    classify_type_of_vote,
    classify_vote_outcome,
)
from ep_scraper.vot_parser import VoteRecord, parse_vot_xml

log = logging.getLogger("ep_scraper")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ── Record builder ───────────────────────────────────────────────────────────

def _build_record(
    rec: VoteRecord,
    vote_id: int,
    file_number: int,
    date_ddmmyyyy: str,
) -> dict:
    """Transform a parsed VoteRecord into a flat dict ready for Excel."""

    # First document code (or 0)
    code = rec.doc_codes[0] if rec.doc_codes else 0

    # Classifications
    type_of_vote = classify_type_of_vote(rec)
    leg_non_bud = classify_leg_non_bud(type_of_vote, rec.title, rec.committee)
    subject = classify_subject(rec)
    final_vote = classify_final_vote(rec)
    vote_outcome = classify_vote_outcome(rec.result)
    link = build_link(code) if code != 0 else 0

    # Policy area from committee map
    policy_area = COMMITTEE_POLICY_MAP.get(rec.committee, 0)
    if rec.committee == "" and policy_area == 0:
        policy_area = DEFAULT_POLICY_AREA

    # Amendment number → int if possible, else 0
    # "§" and "–" are non-numeric markers used for paragraph/recital votes
    am_no: int | str = 0
    raw_am = rec.amendment_number.strip()
    if raw_am and raw_am not in ("§", "–"):
        try:
            am_no = int(raw_am)
        except ValueError:
            am_no = raw_am

    return {
        "vote_id":       vote_id,
        "file":          file_number,
        # order_of_vote is a formula — written by excel_writer
        "date":          date_ddmmyyyy,
        "title":         rec.title,
        "procedure":     0,
        "leg_non_bud":   leg_non_bud,
        "type_of_vote":  type_of_vote,
        "voting_rule":   "s",
        "rapporteur":    rec.vote_author if rec.vote_author else 0,
        "code":          code,
        "interinst_file": 0,
        "link":          link,
        "committee":     rec.committee if rec.committee else 0,
        "policy_area":   policy_area,
        "part":          rec.split_part if rec.split_part else 0,
        "subject":       subject,
        "final_vote":    final_vote,
        "am_no":         am_no,
        "author":        rec.amendment_author if rec.amendment_author else 0,
        "rcv":           "RCV",
        "vote":          vote_outcome,
        "yes":           rec.yes if rec.yes is not None else 0,
        "no":            rec.no if rec.no is not None else 0,
        "abs":           rec.abstentions if rec.abstentions is not None else 0,
        # access_type and subject_of_vote are not written (left empty)
    }


def _am_no_str(val) -> str:
    """Consistent string for dedup key.

    Non-numeric markers like ``§`` and ``–`` normalize to ``"0"``.
    """
    if val is None or val == 0:
        return "0"
    s = str(val).strip()
    if s in ("§", "–", ""):
        return "0"
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s


# ── Per-date processing ──────────────────────────────────────────────────────

def process_date(
    d: date,
    session: requests.Session,
    existing_keys: set[tuple[str, str, str, str]],
    start_vote_id: int,
    file_number: int,
    dry_run: bool = False,
) -> list[dict]:
    """Process a single plenary date: fetch XML, parse, classify.

    Returns list of record dicts ready for :func:`write_records`.
    """
    date_iso = d.strftime("%Y-%m-%d")
    date_ddmmyyyy = d.strftime("%d.%m.%Y")
    log.info("Processing date: %s", date_iso)

    xml = fetch_vot_xml(d, session)
    if not xml:
        log.warning("No VOT XML available for %s", date_iso)
        return []

    records = parse_vot_xml(xml, date_iso)
    log.info("Parsed %d roll-call records for %s", len(records), date_iso)

    output: list[dict] = []
    vote_id = start_vote_id

    for rec in records:
        subject = classify_subject(rec)
        am_no_key = _am_no_str(
            rec.amendment_number.strip() if rec.amendment_number.strip() else 0
        )

        # Dedup
        key = (date_ddmmyyyy, rec.title, subject, am_no_key)
        if key in existing_keys:
            log.debug("Skipping duplicate: %s", key)
            continue

        vote_id += 1
        existing_keys.add(key)

        row = _build_record(rec, vote_id, file_number, date_ddmmyyyy)
        output.append(row)

    log.info("Produced %d new records for %s", len(output), date_iso)

    if dry_run and output:
        _display_records(output)

    return output


def _display_records(records: list[dict]) -> None:
    """Display records for dry-run inspection."""
    for i, rec in enumerate(records):
        print(f"\n--- Record {i + 1} (ID {rec['vote_id']}) ---")
        print(f"  Date:        {rec['date']}")
        print(f"  File:        {rec['file']}")
        print(f"  Title:       {rec['title'][:80]}")
        print(f"  Type:        {rec['type_of_vote']}")
        print(f"  Leg/Non/Bud: {rec['leg_non_bud']}")
        print(f"  Subject:     {rec['subject']}")
        print(f"  Final vote:  {rec['final_vote']}")
        print(f"  Rapporteur:  {rec['rapporteur']}")
        print(f"  Code:        {rec['code']}")
        print(f"  Committee:   {rec['committee']}")
        print(f"  Policy area: {rec['policy_area']}")
        print(f"  Am No:       {rec['am_no']}   Author: {rec['author']}")
        print(f"  Vote:        {rec['vote']}   Yes: {rec['yes']}  No: {rec['no']}  Abs: {rec['abs']}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dorian EP Plenary Votes Metadata Collection",
    )
    parser.add_argument(
        "--date", type=str,
        help="Process a specific date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--backfill", action="store_true",
        help="Process all dates since July 2024",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and display without writing to Excel",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    session = requests.Session()
    session.headers.update(HEADERS)

    # ── Determine dates to process ────────────────────────────────────────
    existing_dates = get_existing_dates()
    log.info("Found %d existing dates in database", len(existing_dates))

    dates_to_process: list[date] = []

    if args.date:
        d = datetime.strptime(args.date, "%Y-%m-%d").date()
        dates_to_process = [d]
    elif args.backfill:
        log.info("Backfill mode: discovering all plenary dates since July 2024")
        dates_to_process = discover_new_dates(existing_dates)
    else:
        log.info("Checking last 30 days for new plenary dates...")
        dates_to_process = discover_recent_dates(existing_dates)

    if not dates_to_process:
        log.info("No new dates to process")
        return

    log.info(
        "Dates to process: %s",
        [d.strftime("%Y-%m-%d") for d in dates_to_process],
    )

    # ── Process each date ─────────────────────────────────────────────────
    existing_keys = get_existing_keys()
    vote_id = get_last_vote_id()
    file_number = get_last_file_number()
    all_records: list[dict] = []

    for d in dates_to_process:
        file_number += 1
        records = process_date(
            d,
            session=session,
            existing_keys=existing_keys,
            start_vote_id=vote_id,
            file_number=file_number,
            dry_run=args.dry_run,
        )
        if records:
            vote_id = records[-1]["vote_id"]
            all_records.extend(records)
        else:
            # No records for this date → don't consume a file number
            file_number -= 1

    if not all_records:
        log.info("No new records produced")
        return

    log.info("Total new records: %d", len(all_records))

    # ── Write to Excel ────────────────────────────────────────────────────
    if not args.dry_run:
        written = write_records(all_records)
        write_state("last_write", {
            "last_vote_id": vote_id,
            "last_file_number": file_number,
            "records_written": written,
        })
        log.info("Done. Wrote %d records. Last Vote ID: %d", written, vote_id)
    else:
        log.info("DRY RUN complete. Would write %d records", len(all_records))


if __name__ == "__main__":
    main()
