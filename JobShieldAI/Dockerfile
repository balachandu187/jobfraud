FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py ./
COPY model/ ./model/
COPY utils/ ./utils/
COPY database/__init__.py database/db_manager.py ./database/
COPY saved_models/ ./saved_models/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-10000}"]
