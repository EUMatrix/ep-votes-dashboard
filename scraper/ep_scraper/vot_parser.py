"""Parse VOT XML files into VoteRecord dataclass objects."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from lxml import etree

log = logging.getLogger(__name__)


@dataclass
class VoteRecord:
    """One roll-call vote extracted from VOT XML."""
    date: str                          # YYYY-MM-DD
    title: str                         # <vote><title>
    vote_label: str                    # <vote><label>
    vote_type: str                     # <vote type="...">
    vote_author: str                   # <vote author="..."> (rapporteur)
    committee: str                     # cleaned committee name
    doc_codes: list[str] = field(default_factory=list)
    voting_label: str = ""             # <voting><label>
    voting_title: str = ""             # <voting><title>
    result: str = ""                   # ADOPTED / REJECTED
    yes: Optional[int] = None
    no: Optional[int] = None
    abstentions: Optional[int] = None
    observations: str = ""             # raw "525, 5, 34" string
    amendment_number: str = ""
    amendment_subject: str = ""
    amendment_author: str = ""
    split_part: Optional[int] = None
    is_final_vote: bool = False
    voting_id: str = ""                # votingId attribute from <voting>


def _text(el: Optional[etree._Element]) -> str:
    """Get stripped text from an element, or empty string."""
    if el is None:
        return ""
    return (el.text or "").strip()


def _detect_split_part(label: str) -> Optional[int]:
    """Detect split part number from label suffix like '/1', '/2'."""
    m = re.search(r"/(\d+)\s*$", label)
    if m:
        return int(m.group(1))
    return None


def _parse_tally(
    observations: str,
) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Parse '525, 5, 34' → (525, 5, 34)."""
    if not observations:
        return None, None, None
    parts = [p.strip() for p in observations.split(",")]
    if len(parts) >= 3:
        try:
            return int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            pass
    return None, None, None


def _clean_committee(raw: str) -> str:
    """Extract committee name from 'Committee: Committee on ...'."""
    raw = raw.strip()
    if not raw or raw == "Committee:":
        return ""
    raw = re.sub(r"^Committee:\s*", "", raw)
    return raw.strip()


def _is_final_vote(voting_el: etree._Element, label: str) -> bool:
    """Detect whether this voting is a final / 'as a whole' vote."""
    label_lower = label.lower()
    if "as a whole" in label_lower:
        return True
    if "single vote" in label_lower:
        return True
    title = _text(voting_el.find("title"))
    title_lower = title.lower()
    if "draft council decision" in title_lower:
        return True
    if "draft legislative resolution" in title_lower:
        return True
    return False


def parse_vot_xml(xml_content: str, date_str: str) -> list[VoteRecord]:
    """Parse VOT XML content and return VoteRecord objects for all roll-call votes.

    Args:
        xml_content: Raw XML string.
        date_str: Date string ``YYYY-MM-DD``.

    Returns:
        List of VoteRecord objects, one per roll-call voting.
    """
    root = etree.fromstring(xml_content.encode("utf-8"))
    records: list[VoteRecord] = []

    for vote_el in root.findall(".//vote"):
        vote_type = vote_el.get("type", "")
        vote_title = _text(vote_el.find("title"))
        vote_label = _text(vote_el.find("label"))
        vote_author = vote_el.get("author", "")
        committee_raw = vote_el.get("committee", "")
        committee = _clean_committee(committee_raw)

        doc_codes: list[str] = []
        for doc_el in vote_el.findall(".//document"):
            doc_num = doc_el.get("documentNumber", "")
            if doc_num:
                doc_codes.append(doc_num)

        for voting_el in vote_el.findall(".//voting"):
            result_type = voting_el.get("resultType", "")
            if result_type != "ROLL_CALL":
                continue

            result = voting_el.get("result", "")
            if result == "LAPSED":
                continue

            label = _text(voting_el.find("label"))
            vtitle = _text(voting_el.find("title"))
            am_number = _text(voting_el.find("amendmentNumber"))
            am_subject = _text(voting_el.find("amendmentSubject"))
            am_author = _text(voting_el.find("amendmentAuthor"))
            obs = _text(voting_el.find("observations"))

            yes, no, abstentions = _parse_tally(obs)
            split_part = _detect_split_part(label)
            is_final = _is_final_vote(voting_el, label)

            rec = VoteRecord(
                date=date_str,
                title=vote_title,
                vote_label=vote_label,
                vote_type=vote_type,
                vote_author=vote_author,
                committee=committee,
                doc_codes=list(doc_codes),
                voting_label=label,
                voting_title=vtitle,
                result=result,
                yes=yes,
                no=no,
                abstentions=abstentions,
                observations=obs,
                amendment_number=am_number,
                amendment_subject=am_subject,
                amendment_author=am_author,
                split_part=split_part,
                is_final_vote=is_final,
                voting_id=voting_el.get("votingId", ""),
            )
            records.append(rec)

    log.info("Parsed %d roll-call records from VOT XML for %s", len(records), date_str)
    return records
