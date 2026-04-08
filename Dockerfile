# ── Stage 1: Build React + Vite frontend ──
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build
# Vite outputs to /frontend/dist

# ── Stage 2: Python backend ──
FROM python:3.13-slim AS backend
WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY data /app/data

# app.py looks for /app/frontend/index.html — put dist there
COPY --from=frontend-build /frontend/dist /app/frontend

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]