# Running with Docker

One image holds everything: the Angular site and the FastAPI server that serves it and the API.
The data (xlsx files) is **not** in the image. You mount it when you run.

## Build and run

```bash
docker build -t bgopl .
docker run --rm -p 8000:8000 -v "$PWD/test_data:/data:ro" bgopl
```

Open http://localhost:8000/app/ for the site and http://localhost:8000/docs for the API.

The first build takes a few minutes: it builds the Angular app in a Node image, then installs
the API in a slim Python image. Later builds reuse cached layers.

## Use your own data

```bash
docker run --rm -p 8000:8000 \
  -v "$PWD/data:/data:ro" \
  -e BGOPL_CONTACT="you@example.com" \
  bgopl
```

- Put the xlsx protocols in `data/`. The folder is git-ignored and is not copied into the image.
- `:ro` mounts the folder read-only. The container never changes your files.

## Settings

| Variable | Meaning | Default in the image |
|---|---|---|
| `BGOPL_DATA_DIR` | folder with the xlsx files | `/data` |
| `BGOPL_SUPPRESS_FILE` | removal-request list | `/data/hide.txt` |
| `BGOPL_FRONTEND_DIR` | built Angular app | `/app/frontend` |
| `BGOPL_CONTACT` | contact address shown by `/api/info` | not set |

Pass them with `-e NAME=value`. Don't put a personal address in the source or the image.

## Run in the background

```bash
docker run -d --name bgopl -p 8000:8000 -v "$PWD/data:/data:ro" bgopl
docker logs bgopl        # output of the server
docker stop bgopl        # stop it
docker rm bgopl          # remove the container
```

Use another port with `-p 9000:8000` (the container always listens on 8000).

## What is in the image

- Two stages: `node:22-slim` builds the frontend, `python:3.13-slim` runs the app.
- Only `pyproject.toml`, `src/` and the built frontend are copied in. Tests, docs, notebooks,
  `data/` are excluded by `.dockerignore`.
- The server runs as a non-root user (uid 10001) with `uvicorn` on port 8000.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The site loads but there are no meets | No data mounted. Check the `-v` path, and `docker logs bgopl` for "data folder not found". |
| `/` redirects to `/docs`, not the site | The frontend is missing from the image. Rebuild it: `docker build --no-cache -t bgopl .` |
| "port is already allocated" | Something else uses 8000. Use `-p 9000:8000`. |
| An athlete still shows after adding them to `hide.txt` | Restart the container. The files are read at startup. |
| Browser says "error loading dynamically imported module" | An old page is cached after a rebuild. Hard refresh (Cmd/Ctrl+Shift+R). |
| Permission denied reading `/data` | Make the folder and files readable by others (`chmod -R a+rX data`). |