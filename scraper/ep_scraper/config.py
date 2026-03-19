"""Constants, URL patterns, and column mappings for Dorian EP vote scraping."""

from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = PROJECT_DIR / "RCVs 2024-2029.xlsx"
CACHE_DIR = PROJECT_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
STATE_FILE = PROJECT_DIR / "run_state.json"

# ── Sheet names ──────────────────────────────────────────────────────────────
SHEET_VOTES = "RCVs"
SHEET_POLICY_MAP = "Sheet6"

# ── URL templates ────────────────────────────────────────────────────────────
VOT_XML_URL = (
    "https://www.europarl.europa.eu/doceo/document/"
    "PV-10-{date}-VOT_EN.xml"
)

# ── Column indices (1-based, matching Excel A–AA) ────────────────────────────
COL = {
    "vote_id":         1,   # A
    "file":            2,   # B
    "order_of_vote":   3,   # C  (formula)
    "date":            4,   # D
    "title":           5,   # E
    "procedure":       6,   # F
    "leg_non_bud":     7,   # G
    "type_of_vote":    8,   # H
    "voting_rule":     9,   # I
    "rapporteur":      10,  # J
    "code":            11,  # K
    "interinst_file":  12,  # L
    "link":            13,  # M
    "committee":       14,  # N
    "policy_area":     15,  # O
    "part":            16,  # P
    "subject":         17,  # Q
    "final_vote":      18,  # R
    "am_no":           19,  # S
    "author":          20,  # T
    "rcv":             21,  # U
    "vote":            22,  # V
    "yes":             23,  # W
    "no":              24,  # X
    "abs":             25,  # Y
    "access_type":     26,  # Z
    "subject_of_vote": 27,  # AA
}

# ── Committee → Policy area mapping (from Sheet6) ───────────────────────────
COMMITTEE_POLICY_MAP = {
    "Committee on Agriculture and Rural Development": "Agriculture",
    "Committee on Budgets": "Budget",
    "Committee on Budgetary Control": "Budgetary control",
    "Committee on Civil Liberties, Justice and Home Affairs": "Civil liberties, justice & home affairs",
    "Committee on Constitutional Affairs": "Constitutional and inter-institutional affairs",
    "Committee on Culture and Education": "Culture & education",
    "Committee on Development": "Development",
    "Committee on Economic and Monetary Affairs": "Economic & monetary affairs",
    "Committee on Employment and Social Affairs": "Employment & Social Affairs",
    "Committee on Environment, Climate and Food Safety": "Environment & public health",
    "Committee on Public Health": "Environment & public health",
    "Committee on Fisheries": "Fisheries",
    "Committee on Foreign Affairs": "Foreign & security policy",
    "Committee on Women's Rights and Gender Equality": "Gender equality",
    "Committee on Industry, Research and Energy": "Industry, Research & Energy",
    "Committee on Internal Market and Consumer Protection": "Internal market & consumer protection",
    "Committee on International Trade": "International trade",
    "Committee on Legal Affairs": "Legal affairs",
    "Committee on Petitions": "Petitions",
    "Committee on Regional Development": "Regional development",
    "Committee on Transport and Tourism": "Transport & tourism",
}
DEFAULT_POLICY_AREA = "Internal regulations of the EP"

# ── Request settings ─────────────────────────────────────────────────────────
REQUEST_DELAY = 1.0          # seconds between HTTP requests
REQUEST_TIMEOUT = 30         # seconds
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}

# ── Term boundaries ──────────────────────────────────────────────────────────
TERM_START = "2024-07-16"  # 10th term start
