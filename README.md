# statpadded

A collection of small sports-data / stats projects. Each project is self-contained
under `projects/<name>/`, with its own scripts, cached data, and README — so
unrelated projects don't tangle together as this repo grows.

## Layout

```
projects/
  <project-name>/
    README.md      what it does, data sources, how to run it
    scripts/        fetch / parse / analyze scripts
    data/
      raw/          cached raw HTML/API responses (not re-fetched once cached)
      *.csv         cleaned, parsed datasets
venv/                shared Python virtualenv (gitignored)
```

## Projects

- [`projects/adp-win-correlation`](projects/adp-win-correlation/) — does a team's
  count of recognizable fantasy-football (ADP) players predict its win total, or
  is that already priced into the Vegas win-total line?

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas beautifulsoup4 scipy matplotlib lxml
```

Each project's README has its own run instructions from there.
