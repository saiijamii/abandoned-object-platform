FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements-phase9.txt /app/backend/requirements-phase9.txt
RUN pip install --no-cache-dir -r /app/backend/requirements-phase9.txt
COPY backend /app/backend
COPY backend/config /app/backend/config
CMD ["uvicorn", "app.api:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
