# GitHub Repository & Open-Source Contribution Analytics

A final-year data analytics project that pulls real data from the GitHub
API for any public repository and analyzes its health: commit activity,
PR merge times, issue resolution times, contributor concentration
("bus factor"), and more — all via straightforward aggregation and
statistics, **no machine learning**.

## Why this is a good final-year project
- Uses a **real, live, public API** (GitHub) — not a static/fake dataset.
- Every metric is a **defined formula** you can explain line by line
  (averages, medians, percentages, ratios) — nothing is a black box.
- Produces genuinely useful insights: "is this project healthy?",
  "is it too dependent on one person?", "are bugs piling up?"
- Has a clear structure: **data collection → data cleaning → analysis →
  visualization**, which maps directly onto a standard "data analytics
  pipeline" you can describe in your report.

## Tech Stack
- **Python** — core language
- **requests** — call the GitHub REST API
- **pandas** — data cleaning & aggregation
- **Streamlit** — interactive dashboard
- **plotly** — charts (used inside Streamlit)

## Project Structure
```
github-analytics/
├── data/
│   └── (cached JSON/CSV pulled from GitHub, generated at runtime)
├── github_client.py     # talks to the GitHub API, handles pagination & rate limits
├── analytics.py         # pure functions: takes raw data -> computes metrics
├── fetch_data.py         # CLI script: pulls & caches data for a given repo
├── app.py                 # Streamlit dashboard
├── requirements.txt
└── README.md
```

## 1. Get a GitHub API token (recommended, not strictly required)
Unauthenticated requests are limited to 60/hour, which you'll hit fast.
With a free personal access token you get 5,000/hour.

1. GitHub → Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token (no special scopes needed for
   public repo data).
2. Set it as an environment variable before running anything:
   ```bash
   export GITHUB_TOKEN=your_token_here      # macOS/Linux
   set GITHUB_TOKEN=your_token_here         # Windows (cmd)
   ```

## 2. Install dependencies
```bash
pip install -r requirements.txt
```

## 3. Fetch data for a repository
```bash
python fetch_data.py --owner facebook --repo react
```
This pulls commits, pull requests, issues, and contributors for the repo
and caches them as JSON in `data/`, so you don't hit the API repeatedly
while developing the dashboard.

## 4. Run the dashboard
```bash
streamlit run app.py
```
Pick a cached repo from the dropdown (or fetch a new one) and explore:
- **Commit activity** over time (daily/weekly)
- **PR merge time** distribution and trend
- **Issue resolution time** by label
- **Contributor concentration** ("bus factor" — what % of commits come
  from the top 1/3/5 contributors)
- **Issue reopen rate**

## Metrics explained (for your report/viva)

| Metric | Formula / Definition |
|---|---|
| Commit frequency | Commits grouped by day/week — a simple `groupby().count()` |
| PR merge time | `merged_at - created_at` for each merged PR, then mean/median |
| Issue resolution time | `closed_at - created_at` for each closed issue |
| Bus factor (simplified) | Sort contributors by commit count descending; find the smallest number of top contributors whose combined commits ≥ 50% of total |
| Contribution concentration | % of total commits made by the top N contributors (e.g. top 1, top 3, top 5) |
| Issue reopen rate | (issues reopened at least once) / (total closed issues) |

None of these require training a model — they're direct calculations on
the raw data, which makes them easy to defend: you can trace any number
on the dashboard back to the exact rows and formula that produced it.

## Next steps / extensions (optional, for a stronger project)
- Compare multiple repositories side-by-side (e.g. React vs Vue vs Svelte)
- Add a "health score" that combines several metrics into one number
  (still just a weighted formula, not ML)
- Cache data in a real database (SQLite/PostgreSQL) instead of JSON files
- Schedule periodic re-fetching to show trends over time (cron job)
- Export a PDF report summarizing a repo's health
