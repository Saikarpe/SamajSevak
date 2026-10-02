# Single-container build: React UI is built and served by FastAPI
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
# bake the multilingual embedding model into the image so the container starts offline;
# skipped when the service runs with SAMAJSEVAK_EMBEDDINGS=0 (Render passes env vars as build args)
ARG SAMAJSEVAK_EMBEDDINGS=1
RUN if [ "$SAMAJSEVAK_EMBEDDINGS" = "1" ]; then cd backend && python -c "from app.ml import embed; assert embed.available()"; fi
COPY --from=web /web/dist frontend/dist
WORKDIR /app/backend
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
