# EP Plenary Votes Dashboard

Interactive dashboard for exploring European Parliament roll-call votes, including how individual MEPs voted on each item.

## Setup

1. Install [Node.js](https://nodejs.org/) (v18+)
2. Open a terminal in this folder and run:

```bash
npm install
npm run dev
```

3. Open http://localhost:5173 in your browser

## Deploy to production

```bash
npm run build
```

This creates a `dist/` folder with static files you can deploy to Netlify, Vercel, or any static hosting.

## Data source

The dashboard reads live from the Supabase database (`ep_plenary_votes` schema). The Supabase connection is configured in `src/supabaseClient.js`. Tables used:

- `Plenary_votes_main` - vote metadata (dossier, date, subject, outcome, amendment text, summary)
- `meps_rcv_votes` - individual MEP votes (name, country, party, group, vote value)
- `epg_rcv_votes` - political group aggregates per vote

## Features

- Browse plenary sessions by date or search dossiers by name
- Filter by policy category, report type, or specific date
- Click a dossier to see all votes (amendments, paragraphs, final votes)
- Each vote shows political group positions with icons
- Click a vote to see the full tally bar, amendment text, summary, and every individual MEP's vote
- Filter MEPs by political group (click group card) or country
