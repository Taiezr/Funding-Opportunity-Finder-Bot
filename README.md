# Energy R&D Funding Watch

A small bot that checks federal and foundation funding sources every morning and
publishes a dashboard of open **energy R&D** opportunities — highlighting what's
new since the last run and how soon each one closes.

It runs free on **GitHub Actions** and publishes to **GitHub Pages**, so there's
no server to maintain and the report updates whether or not your computer is on.

---

## What it pulls

- **Federal — Grants.gov** via the public Search2 + fetchOpportunity APIs (no key).
  Grants.gov aggregates postings from DOE, ARPA-E, NSF, EPA, USDA and others. The
  bot searches the Energy category plus each keyword, then reads each candidate's
  full record to (a) keep only opportunities whose text actually matches one of
  your keywords and (b) capture the **award amount** per project.
- **Foundations** — any RSS feed of funding opportunities you list in
  `config.yaml`. Items are kept only if they mention one of your keywords. A dead
  or malformed feed is logged and skipped, never breaking the run.

The dashboard itself is interactive: filter by funding organization, keyword,
days left, or days since released, and toggle to new items only.

---

## Try it locally first

```bash
pip install -r requirements.txt
python run.py --demo      # writes docs/index.html with sample data — no network
```

Open `docs/index.html` in a browser. Then do a real run:

```bash
python run.py             # hits Grants.gov + your feeds, updates data/seen.json
```

---

## Deploy on GitHub (recommended)

1. **Create a repo** and push this folder to it.
2. **Enable write permissions for Actions:** repo **Settings → Actions → General
   → Workflow permissions →** select **Read and write permissions →** Save.
   (The workflow commits the updated report and the "seen" list back to the repo.)
3. **Do one run** so `docs/index.html` exists: go to the **Actions** tab, open
   **Daily Energy Funding Report**, and click **Run workflow**. (Or run
   `python run.py` locally and commit the result.)
4. **Turn on Pages:** **Settings → Pages → Source: Deploy from a branch →**
   Branch **main**, folder **/docs →** Save.
5. Your dashboard is live at `https://<your-username>.github.io/<repo-name>/`.
   Bookmark it. It refreshes itself every morning.

The schedule is **13:00 UTC** (~6:00 AM Pacific). Change the `cron` line in
`.github/workflows/daily.yml` to whatever you like —
[crontab.guru](https://crontab.guru) helps. Note GitHub's scheduler can lag by a
few minutes to an hour at busy times.

---

## Customize

Everything lives in **`config.yaml`**:

- **`keywords`** — the main knob. Drives the Grants.gov searches and filters the
  foundation feeds. Add the technologies and terms you care about.
- **`foundation_feeds`** — add any RSS feed of opportunities (`name` + `url`).
  Many foundations and aggregators publish program/RFP feeds; verify the URL in a
  browser first. The one shipped is a starting point, not a guarantee.
- **`closing_soon_days`** — deadline threshold for the "closing soon" count.

---

## How "new" is decided

`data/seen.json` records the first date each opportunity was seen (keyed by a
stable id). Anything not already in that file is flagged **New** in the report,
then added. The file is committed back each run, so "new" means "new to you."
Delete the file to reset and treat everything as new again.

---

## Notes & limits

- This uses official **APIs and RSS** rather than HTML scraping wherever possible
  — far more reliable, since scrapers break when a site's layout changes. If you
  later want a source with no API/feed, add a small scraper module under
  `sources/` that returns the same item shape and merge it in `run.py`.
- Foundation deadlines are often not machine-readable in RSS, so those rows show
  "Rolling" instead of a countdown. Click through to confirm dates.
- Always confirm eligibility and deadlines on the official opportunity page before
  relying on them.

## File map

```
config.yaml              keywords, feeds, settings  ← edit this
run.py                   orchestrator (use --demo to preview)
report.py                builds the HTML dashboard
state.py                 "seen" tracking
sources/federal.py       Grants.gov Search2 client
sources/foundations.py   RSS feed reader
.github/workflows/daily.yml   the daily schedule
docs/index.html          the generated dashboard (served by Pages)
data/seen.json           memory of what's been seen
```
