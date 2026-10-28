# Multi-stage optimized Dockerfile for Choir Pitch Tracker Backend (multif0 port)
FROM python:3.12-slim-bookworm

# System dependencies for audio decoding and model retrieval
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone original multif0 repository for model architecture weights
RUN git clone --depth 1 https://github.com/helenacuesta/multif0-estimation-polyvocals /app/multif0-estimation-polyvocals

# Install pinned Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and only the preset assets required by the API.
COPY backend /app/backend
COPY frontend/sample_transcription.json frontend/sample_audio.wav /app/frontend/

# Create non-root system user for security compliance (CIS benchmark)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Configure environment
ENV PYTHONUNBUFFERED=1 \
    MF0_REPO=/app/multif0-estimation-polyvocals \
    PYTHONPATH=/app/backend

WORKDIR /app/backend
USER appuser

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
