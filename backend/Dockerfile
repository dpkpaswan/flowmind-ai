FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run uses PORT env variable (default 8080)
ENV PORT=8080

EXPOSE 8080

# Run with uvicorn on the correct port
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
