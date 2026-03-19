# EP Plenary Votes Scraper

Python scripts that collect European Parliament plenary vote data from the EP website.

## Two pipelines

### 1. Aggregate votes (`main.py`)
Collects roll-call vote metadata (dossier, subject, tally, outcome) from VOT XML files.
Writes to a local Excel file (`RCVs 2024-2029.xlsx`).

```bash
python main.py                       # Last 30 days
python main.py --date 2026-03-12     # Specific date
python main.py --backfill            # All dates since July 2024
python main.py --dry-run             # Preview without writing
```

### 2. Individual MEP votes (`rcv_collector.py`)
Collects how each MEP voted on every roll-call item from RCV XML files.
Stores in local SQLite (`mep_votes.db`), exportable to CSV for Supabase import.

```bash
python rcv_collector.py --date 2026-03-12     # Specific date
python rcv_collector.py --lookback 60         # Last 60 days
python rcv_collector.py --export-csv          # Export for Supabase
python rcv_collector.py --stats               # DB summary
python rcv_collector.py --dry-run             # Preview only
```

**Workflow:** Run `main.py` first (assigns vote_ids), then `rcv_collector.py` (collects MEP votes).

## Setup

```bash
pip install -r requirements.txt
```

Place `RCVs 2024-2029.xlsx` in the parent directory (or update `config.py` paths).

## Data sources

- **VOT XML:** `https://www.europarl.europa.eu/doceo/document/PV-10-{date}-VOT_EN.xml` (aggregate tallies)
- **RCV XML:** `https://www.europarl.europa.eu/doceo/document/PV-10-{date}-RCV_EN.xml` (individual MEP votes)

## Key files

| File | Purpose |
|---|---|
| `main.py` | CLI for aggregate vote collection |
| `rcv_collector.py` | CLI for individual MEP vote collection |
| `ep_scraper/vot_parser.py` | Parse VOT XML into VoteRecord objects |
| `ep_scraper/rcv_parser.py` | Parse RCV XML into MepVote objects |
| `ep_scraper/vote_classifier.py` | Classify votes (type, subject, leg/non/bud) |
| `ep_scraper/config.py` | URLs, paths, column mappings |
| `ep_scraper/excel_writer.py` | Excel read/write operations |
| `ep_scraper/date_discovery.py` | Find new plenary dates |
| `mep_cache.json` | MEP details lookup (732 MEPs) |
