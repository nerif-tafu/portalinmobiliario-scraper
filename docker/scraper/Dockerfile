FROM python:3.11-slim

# Install Chrome, VNC, and other dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    xvfb \
    x11vnc \
    fluxbox \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Set display port to avoid crash
ENV DISPLAY=:99
ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy both web and scraper modules
COPY web/ web/
COPY scraper/ scraper/

COPY docker/scraper/start.sh /start.sh
RUN chmod +x /start.sh

# Expose VNC port
EXPOSE 5900

CMD ["/start.sh"] 