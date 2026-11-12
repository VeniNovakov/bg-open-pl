# BG Open Powerlifting: backend

Reads Bulgarian powerlifting meet protocols (xlsx, standard layout), checks the data, and serves
the results through a REST API. The same server also serves the Angular site under `/app/`.

## What it does

- **Parses** the federation's spreadsheets into typed objects (lifters, attempts, totals, points).
- **Validates** every file: totals, IPF GL points, place order, weight classes, team points.
  Problems become findings with a severity (error, warning, info) and are never silently dropped.
- **Serves** meets, rankings, weight classes and athlete histories as JSON.

## Requirements

Python 3.11 or newer.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[web,dev]"
```

## Run it

With the synthetic sample data (no personal data involved):

```bash
BGOPL_DATA_DIR=test_data uvicorn bgopl.web.app:create_app --factory --reload
```

- API docs: http://127.0.0.1:8000/docs
- Site: http://127.0.0.1:8000/app/ (needs the Angular build, see `frontend/`)

A bigger dataset for analysis is in `sample-large/` (12 meets, about 140 athletes).

With real protocols, put the xlsx files in `data/` (git-ignored) and start without
`BGOPL_DATA_DIR`.

## Docker

```bash
docker build -t bgopl .
docker run --rm -p 8000:8000 -v "$PWD/sample:/data:ro" bgopl
```

The data is never part of the image. It is mounted at `/data`.

## Settings (environment variables)

| Variable | Meaning | Default |
|---|---|---|
| `BGOPL_DATA_DIR` | folder with the xlsx files | `data` |
| `BGOPL_SUPPRESS_FILE` | removal-request list | none (`/data/hide.txt` in Docker) |
| `BGOPL_CONTACT` | contact address shown by `/api/info` | "(contact address not set)" |
| `BGOPL_FRONTEND_DIR` | folder with the built Angular app | `frontend/dist/frontend/browser` |

## API

| Endpoint | Returns |
|---|---|
| `GET /api/meets` | all meets |
| `GET /api/meets/{slug}` | one meet with its lifters (slug is the date, e.g. `2026-01-10`) |
| `GET /api/meets/{slug}/findings` | validation findings for that file |
| `GET /api/rankings` | best result per lifter; filters `sex`, `equipment`, `division`, `weight_class`, `limit` |
| `GET /api/rankings/classes` | weight classes that exist for the given filters |
| `GET /api/athletes/{sex}/{name}` | every appearance of one athlete |
| `GET /api/info` | counts and the contact address |

Full details and a try-it-out form are at `/docs`.

## Tests

```bash
pytest src/bgopl/tests      # or just `pytest` if testpaths points there
ruff check .
```

The tests build small synthetic workbooks, so they need no real data. One test
(`test_real_standard_file.py`) is skipped unless a real protocol is available.

## Project layout

```
src/bgopl/
  models.py            data classes (Lifter, Attempt, Issue, ...)
  parse_standard.py    xlsx -> objects
  validate_standard.py checks and findings
  points.py            IPF GL and Wilks formulas
  main.py, views.py    command-line output
  web/
    app.py             create_app()
    api.py             REST endpoints
    routes.py          serves the Angular build under /app/
    store.py           loads the files, answers the queries
  test_data synthetic workbooks (invented names)
```

## Data and privacy

Athlete names, birth years and bodyweights are personal data. Real protocols stay out of git
and out of the Docker image (`data/`, `*.xlsx`, `hide.txt` are ignored). The sample data
is entirely invented. Athletes can be removed by adding a line to `hide.txt`
(`M|Name Surname`, or just the name to match either sex).