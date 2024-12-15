FROM python:3.11-slim

# Install Chrome and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    xvfb \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Set display port to avoid crash
ENV DISPLAY=:99
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy both web and scraper modules
COPY web/ web/
COPY scraper/ scraper/

COPY docker/scraper/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"] 