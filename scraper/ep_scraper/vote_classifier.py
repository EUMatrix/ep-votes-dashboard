"""Classify VoteRecord fields into the exact Dorian database format.

Maps raw XML fields → Type of Vote, Leg/Non/Bud, Subject, Final vote,
Vote outcome, and document link.
"""

from __future__ import annotations

import re
from ep_scraper.vot_parser import VoteRecord


# ── Type of Vote ─────────────────────────────────────────────────────────────

def classify_type_of_vote(rec: VoteRecord) -> str:
    """Derive the 'Type of Vote' column (H) from the vote-level label.

    Uses ``rec.vote_label`` (the ``<vote><label>`` text) and
    ``rec.title`` / ``rec.doc_codes`` for disambiguation.
    """
    label = rec.vote_label
    title_lower = rec.title.lower()
    label_lower = label.lower()

    if label_lower.startswith("report:"):
        if "legislative resolution" in title_lower:
            return "Draft legislative resolution"
        # EP convention: asterisk(s) after title indicate legislative procedure
        # (consultation *, consent **, ordinary legislative procedure ***)
        if rec.title.rstrip().endswith("*"):
            return "Draft legislative resolution"
        return "Motion for resolution"

    if label_lower.startswith("recommendation:"):
        return "Draft recommendation"

    # Handle both singular and plural forms
    if (label_lower.startswith("motion for a resolution:")
            or label_lower.startswith("motions for resolutions:")):
        # RC-B10 codes may appear only in the label, not in doc_codes
        has_rc = ("rc-b10" in label_lower
                  or any(c.upper().startswith("RC-B10") for c in rec.doc_codes))
        if has_rc:
            return "Joint motion for a resolution"
        return "Motion for resolution"

    if "proposal for a decision" in label_lower or "proposal for a decision" in title_lower:
        return "Proposal for a decision"

    if "explanatory statement" in label_lower or "explanatory statement" in title_lower:
        return "Explanatory statement"

    # Fallback for RESOLUTION type without a matching label prefix
    if rec.vote_type == "RESOLUTION":
        has_rc = ("rc-b10" in label_lower
                  or any(c.upper().startswith("RC-B10") for c in rec.doc_codes))
        if has_rc:
            return "Joint motion for a resolution"
        return "Motion for resolution"

    return "Motion for resolution"


# ── Leg / Non-Leg / Bud ─────────────────────────────────────────────────────

_BUDGET_KEYWORDS = ["budget", "discharge", "estimates"]


def classify_leg_non_bud(type_of_vote: str, title: str, committee: str) -> str:
    """Return ``"Leg"``, ``"Non"``, or ``"Bud"``."""
    if type_of_vote == "Draft legislative resolution":
        return "Leg"

    lower_title = title.lower()
    lower_committee = committee.lower()
    for kw in _BUDGET_KEYWORDS:
        if kw in lower_title or kw in lower_committee:
            return "Bud"

    return "Non"


# ── Subject ──────────────────────────────────────────────────────────────────

def classify_subject(rec: VoteRecord) -> str:
    """Derive the 'Subject' column (Q) value.

    Patterns:
      - "Amendment N"  /  "Amendment N/K" (split)
      - "Paragraph N"  /  "Paragraph N/K"
      - "Recital X"    /  "Recital X/K"
      - "Citation N"
      - "single vote"
      - "Procedural vote" / "Procedural motion"
      - "vote: resolution (as a whole)"
      - "vote: Commission proposal"
      - "vote: consent"
      - "vote: decision (as a whole)"
      - etc.
    """
    label = rec.voting_label
    am_num = rec.amendment_number.strip()
    am_subj = rec.amendment_subject.strip()
    vtitle = rec.voting_title.strip()
    split = rec.split_part

    # Strip leading document-code prefixes from labels
    label = _strip_doc_code_prefix(label)

    # ── Procedural / agenda votes (EUGI type) ────────────────────────────
    if rec.vote_type == "EUGI":
        return "Procedural vote"

    # ── PROPOSAL type (no amendments) ────────────────────────────────────
    if rec.vote_type == "PROPOSAL" and not am_num:
        return _classify_proposal_subject(label, vtitle)

    # ── Final / whole-text votes ─────────────────────────────────────────
    label_lower = label.lower()

    if "proposal to vote on amendments" in label_lower:
        return "Procedural motion"

    if "motion for a resolution (as a whole)" in label_lower:
        return "vote: resolution (as a whole)"

    if "motion for a resolution" in label_lower and "as a whole" in label_lower:
        return "vote: resolution (as a whole)"

    m = re.search(
        r"(?:(\w+)\s+committee\s+)?resolution\s*\(as a whole\)",
        label_lower,
    )
    if m:
        return "vote: resolution (as a whole)"

    if "single vote" in label_lower:
        return "single vote"

    # ── Single/consent votes on whole report ─────────────────────────────
    if rec.vote_type == "REPORT" and not am_num and not am_subj:
        vtitle_lower = vtitle.lower()
        if "draft council decision" in vtitle_lower:
            return "vote: consent"
        if "interinstitutional negotiations" in vtitle_lower:
            return "vote: decision to enter interinstitutional negotiations"
        if vtitle_lower == "commission proposal":
            return "vote: Commission proposal"
        if "legislative resolution" in vtitle_lower:
            return "vote: Commission proposal"
        if vtitle_lower == "motion for a resolution":
            return "vote: resolution (as a whole)"
        if "proposal for a decision" in vtitle_lower or "proposals for decisions" in vtitle_lower:
            return "vote: decision (as a whole)"
        if vtitle and not rec.is_final_vote:
            return "single vote"
        if "november" in label_lower or "calendar" in label_lower:
            return label.strip()

    if vtitle.lower() == "motion for a resolution":
        return "vote: resolution (as a whole)"

    if "draft council decision" in label_lower or "draft council decision" in vtitle.lower():
        return "vote: consent"

    if "proposal for a council decision" in label_lower or "proposal for a council" in label_lower:
        return "vote: consent"

    if "proposal for a council regulation" in label_lower:
        return "vote: Commission proposal"

    if "draft legislative resolution" in label_lower or "draft legislative resolution" in vtitle.lower():
        return "vote: Commission proposal"

    if "commission proposal" in label_lower:
        if "reject" in label_lower:
            return "Proposal to reject the Commission proposal"
        return "vote: Commission proposal"

    if "proposal for a decision" in label_lower:
        return "vote: proposal for a decision"

    if "decision (as a whole)" in label_lower or "decision (as a whole)" in vtitle.lower():
        return "vote: decision (as a whole)"

    if "interinstitutional negotiations" in label_lower:
        return "vote: decision to enter interinstitutional negotiations"

    if "referral back" in label_lower:
        return "vote: referral back"

    if "request for urgent" in label_lower:
        return "vote: request for urgent decision"

    if "joint text" in label_lower:
        return "Joint text"

    # ── Paragraph / Recital / Citation votes (from amendmentSubject) ────
    # When an amendment has both a number and a subject description,
    # the subject (e.g. "After § 4" → "After paragraph 4") is more
    # informative — the amendment number goes to column S (Am No.).
    if am_subj:
        return _classify_from_subject(am_subj, split)

    # ── Amendment votes (number only, no subject description) ────────────
    if am_num and am_num != "§" and am_num != "–":
        am_num_clean = " ".join(am_num.split())
        return f"Amendment {am_num_clean}"

    # ── Fallback: try to parse from label ────────────────────────────────
    return _classify_from_label(label, split)


def _strip_doc_code_prefix(label: str) -> str:
    """Strip leading document codes like ``C10-0005/2026 –`` from labels."""
    return re.sub(r"^[A-Z]\d+-\d+/\d+\s*[–—-]\s*", "", label)


def _normalize_section_refs(text: str) -> str:
    """Normalize ``§`` → ``paragraph`` and collapse whitespace/newlines."""
    text = text.replace("sub§", "subparagraph")
    text = re.sub(r"§\s*", "paragraph ", text)
    # Collapse newlines and multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _classify_from_subject(am_subj: str, split: int | None) -> str:
    """Convert amendmentSubject like ``§ 3`` to ``Paragraph 3``.

    Split part numbers are NOT appended here — they go to column P (Part).
    """
    m = re.match(r"§\s*(\d+),?\s*point\s*\(?([a-z]+)\)?", am_subj, re.IGNORECASE)
    if m:
        return f"Paragraph {m.group(1)}, point {m.group(2)}"

    m = re.match(r"§\s*(\d+),?\s*(sub§|subparagraph)\s*(\d+)", am_subj, re.IGNORECASE)
    if m:
        return f"Paragraph {m.group(1)}, subparagraph {m.group(3)}"

    m = re.match(r"§\s*(\d+)$", am_subj)
    if m:
        return f"Paragraph {m.group(1)}"

    m = re.match(r"After\s+§\s*(\d+)", am_subj)
    if m:
        return f"After paragraph {m.group(1)}"

    m = re.match(r"[Rr]ecital\s+([A-Z]+)", am_subj)
    if m:
        return f"Recital {m.group(1)}"

    m = re.match(r"After\s+[Rr]ecital\s+([A-Z]+)", am_subj)
    if m:
        return f"After recital {m.group(1)}"

    m = re.match(r"[Cc]itation\s+(\d+)", am_subj)
    if m:
        return f"Citation {m.group(1)}"

    m = re.match(r"§\s*(\d+)(.*)", am_subj)
    if m:
        rest = m.group(2).strip().lstrip(",").strip()
        rest = _normalize_section_refs(rest)
        if rest:
            return f"Paragraph {m.group(1)}, {rest}"
        return f"Paragraph {m.group(1)}"

    if am_subj.lower().startswith("article"):
        return _normalize_section_refs(am_subj)

    if am_subj.lower().startswith("annex"):
        return _normalize_section_refs(am_subj)

    # "Before § 1" → "Before paragraph 1"  (lowercase 'p' for non-leading §)
    normalized = _normalize_section_refs(am_subj)
    return normalized


def _classify_from_label(label: str, split: int | None) -> str:
    """Last-resort: extract subject from the label string.

    Split suffixes in labels (e.g. ``/2``) are ignored here — split
    part is recorded in column P.
    """
    m = re.search(r"–\s*§\s*(\d+)(?:/\d+)?\s*$", label)
    if m:
        return f"Paragraph {m.group(1)}"

    m = re.search(r"–\s*Am\s*(\d+)(?:/\d+)?\s*$", label)
    if m:
        return f"Amendment {m.group(1)}"

    if "procedural" in label.lower():
        return "Procedural vote"

    return label.strip() if label.strip() else "Procedural vote"


def _classify_proposal_subject(label: str, vtitle: str) -> str:
    """Classify PROPOSAL-type votes."""
    label_lower = label.lower()
    vtitle_lower = vtitle.lower()

    if "decision to maintain" in label_lower or "decision to maintain" in vtitle_lower:
        return "vote: decision to maintain the action before the Court of Justice"
    if "referral back" in label_lower:
        return "vote: referral back"
    if "adjournment" in label_lower:
        return "Demande d'ajournement du vote"
    if "request for" in label_lower and "urgent" in label_lower:
        return "vote: request for urgent decision"
    if "commission proposal" in label_lower or "commission proposal" in vtitle_lower:
        return "vote: Commission proposal"
    if "council decision" in label_lower or "council decision" in vtitle_lower:
        return "vote: consent"
    if "council regulation" in label_lower or "council regulation" in vtitle_lower:
        return "vote: Commission proposal"
    if "legislative resolution" in label_lower or "legislative resolution" in vtitle_lower:
        return "vote: Commission proposal"

    return label.strip() if label.strip() else "Procedural vote"


# ── Final vote flag ──────────────────────────────────────────────────────────

def classify_final_vote(rec: VoteRecord) -> int:
    """Return ``1`` for final/whole-text votes, ``0`` otherwise."""
    label_lower = rec.voting_label.lower()
    vtitle_lower = rec.voting_title.lower()

    if "as a whole" in label_lower:
        return 1
    if "single vote" in label_lower:
        return 1
    if "draft legislative resolution" in label_lower or "draft legislative resolution" in vtitle_lower:
        return 1
    # Single/whole-text vote on a report with no amendments
    if (rec.vote_type == "REPORT"
            and not rec.amendment_number.strip()
            and not rec.amendment_subject.strip()):
        return 1
    return 0


# ── Vote outcome ─────────────────────────────────────────────────────────────

def classify_vote_outcome(result: str) -> str:
    """Return ``"+"`` for ADOPTED, ``"-"`` for REJECTED."""
    if result == "ADOPTED":
        return "+"
    return "-"


# ── Document link ────────────────────────────────────────────────────────────

def build_link(code: str) -> str | int:
    """Construct EP document URL from a document code.

    Transforms codes like ``A10-0022/2025`` → URL, or returns ``0`` if
    the code is empty or unparseable.
    """
    if not code or code == "0":
        return 0

    m = re.match(r"(RC-)?([AB])(\d+)-(\d+)/(\d+)", code)
    if not m:
        return 0

    prefix = m.group(1) or ""   # "RC-" or ""
    letter = m.group(2)         # "A" or "B"
    term = m.group(3)           # "10"
    num = m.group(4)            # "0022"
    year = m.group(5)           # "2025"

    if prefix:
        # RC-B10-0156/2025 → RC-10-2025-0156
        html_code = f"RC-{term}-{year}-{num}"
    else:
        # A10-0022/2025 → A-10-2025-0022
        html_code = f"{letter}-{term}-{year}-{num}"

    return (
        f"https://www.europarl.europa.eu/doceo/document/"
        f"{html_code}_EN.html"
    )
