# Build the React frontend.
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./package.json
COPY frontend/vite.config.js ./vite.config.js
COPY frontend/index.html ./index.html
COPY frontend/src ./src
RUN npm install --no-audit --no-fund && npm run build

# Ship the frontend as static assets from the FastAPI service.
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    SCRAPSHIFT_DB_PATH=/app/backend/data/scrapshift.db
WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend-build /app/frontend/dist ./app/static
RUN mkdir -p /app/backend/data && useradd --create-home --uid 10001 scrapshift && chown -R scrapshift:scrapshift /app/backend
USER scrapshift
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
