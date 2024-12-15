FROM python:3.11-slim

# Install netcat for database check
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY web/ web/
COPY docker/web/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"] 