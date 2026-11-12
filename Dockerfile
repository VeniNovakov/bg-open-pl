# One image: the Angular build plus the FastAPI app that serves it and the API.
# The data (xlsx files, hide.txt) is NOT in the image: mount it at /data.

FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build:app

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    BGOPL_DATA_DIR=/data \
    BGOPL_SUPPRESS_FILE=/data/hide.txt \
    BGOPL_FRONTEND_DIR=/app/frontend
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[web]"
COPY --from=frontend /build/dist/frontend/browser /app/frontend
RUN useradd --system --uid 10001 app
USER app
EXPOSE 8000
CMD ["uvicorn", "bgopl.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]