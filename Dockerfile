# ==============================================================================
# SIH26166 Scientific Lunar Image Registration - Production Dockerfile
# ==============================================================================

FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install system dependencies required by OpenCV, Scientific libraries, and Build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libspatialindex-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt pyproject.toml /app/

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application codebase
COPY . /app

# Create necessary runtime directories
RUN mkdir -p /app/experiments/runs /app/data/raw /app/data/processed /app/reports

# Expose web server port
EXPOSE 8080

# Healthcheck to monitor container status
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Start the dashboard server
CMD ["python", "dashboard_server.py"]
