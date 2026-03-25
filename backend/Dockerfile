# Use Python 3.11 slim image
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies including Playwright browser deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Chromium browser
RUN pip install playwright && playwright install chromium

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Create non-root user and set ownership (include Playwright browser cache)
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app \
    && if [ -d /root/.cache/ms-playwright ]; then \
         mkdir -p /home/appuser/.cache && \
         cp -r /root/.cache/ms-playwright /home/appuser/.cache/ && \
         chown -R appuser:appuser /home/appuser/.cache; \
       fi

# Playwright needs --no-sandbox when running as non-root
ENV PLAYWRIGHT_CHROMIUM_SANDBOX=0

USER appuser

# Expose port (Railway uses dynamic $PORT)
EXPOSE 8000

# Start the application (railway.toml startCommand overrides this)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
