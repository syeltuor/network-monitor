FROM python:3.12-alpine

# Install system dependencies for ping and speedtest
RUN apk add --no-cache \
    iputils \
    curl \
    && pip install --no-cache-dir boto3 speedtest-cli

# Create app and data directories
WORKDIR /app
RUN mkdir -p /data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the monitor in a loop
CMD ["sh", "-c", "while true; do python3 /app/network_monitor.py; sleep 3600; done"]
