"""Parse RCV XML files to extract individual MEP voting records.

The RCV XML (PV-10-{date}-RCV_EN.xml) contains how each MEP voted on
every roll-call item: For, Against, or Abstention, grouped by political
group.  This module parses that structure into flat MepVote records.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from lxml import etree

log = logging.getLogger(__name__)


@dataclass
class MepVote:
    """A single MEP's vote on a single roll-call item."""

    rcv_id: str            # RollCallVote.Result Identifier (= votingId in VOT XML)
    date: str              # YYYY-MM-DD
    timestamp: str         # YYYY-MM-DD HH:MM:SS (from RCV Date attr)
    description: str       # Vote description text
    mep_id: str            # MepId attribute
    pers_id: str           # PersId attribute
    mep_name: str          # MEP name text
    political_group: str   # Political group code (PPE, S&D, ECR, etc.)
    position: str          # "For", "Against", "Abstention"


@dataclass
class VoteIntention:
    """A vote-correction / intention declared after the vote."""

    rcv_id: str
    date: str
    mep_id: str
    pers_id: str
    mep_name: str
    intended_position: str  # "For", "Against", "Abstention"


def parse_rcv_xml(xml_text: str | bytes, date_str: str) -> tuple[list[MepVote], list[VoteIntention]]:
    """Parse an RCV XML file and return individual MEP votes and intentions.

    Args:
        xml_text: Raw XML content (str or bytes).
        date_str: Date in YYYY-MM-DD format (used as fallback).

    Returns:
        Tuple of (mep_votes, vote_intentions).
    """
    if isinstance(xml_text, str):
        xml_text = xml_text.encode("utf-8")
    root = etree.fromstring(xml_text)

    sitting_date = root.get("Sitting.Date", date_str)

    votes: list[MepVote] = []
    intentions: list[VoteIntention] = []
    n_items = 0

    for result in root.iter("RollCallVote.Result"):
        n_items += 1
        rcv_id = result.get("Identifier", "")
        timestamp = result.get("Date", sitting_date)

        desc_el = result.find("RollCallVote.Description.Text")
        description = (desc_el.text or "").strip() if desc_el is not None else ""

        # ── Actual votes: For / Against / Abstention ─────────────────────
        for section_tag, position in [
            ("Result.For", "For"),
            ("Result.Against", "Against"),
            ("Result.Abstention", "Abstention"),
        ]:
            section = result.find(section_tag)
            if section is None:
                continue

            for group_list in section.findall("Result.PoliticalGroup.List"):
                group_code = group_list.get("Identifier", "")

                for member in group_list.findall("PoliticalGroup.Member.Name"):
                    votes.append(MepVote(
                        rcv_id=rcv_id,
                        date=sitting_date,
                        timestamp=timestamp,
                        description=description,
                        mep_id=member.get("MepId", ""),
                        pers_id=member.get("PersId", ""),
                        mep_name=(member.text or "").strip(),
                        political_group=group_code,
                        position=position,
                    ))

        # ── Intentions / corrections ─────────────────────────────────────
        for intent_el in result.findall("Intentions"):
            for sub_tag, pos in [
                ("Intentions.Result.For", "For"),
                ("Intentions.Result.Against", "Against"),
                ("Intentions.Result.Abstention", "Abstention"),
            ]:
                sub = intent_el.find(sub_tag)
                if sub is None:
                    continue
                for member in sub.findall("Member.Name"):
                    intentions.append(VoteIntention(
                        rcv_id=rcv_id,
                        date=sitting_date,
                        mep_id=member.get("MepId", ""),
                        pers_id=member.get("PersId", ""),
                        mep_name=(member.text or "").strip(),
                        intended_position=pos,
                    ))

    log.info(
        "Parsed %d MEP votes + %d intentions from %d roll-call items for %s",
        len(votes), len(intentions), n_items, sitting_date,
    )
    return votes, intentions
