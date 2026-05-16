# Docker Setup for Network Monitor

Run the network monitor in a Docker container for easy deployment and management.

## Prerequisites

- Docker installed on your Raspberry Pi
- Docker Compose (optional but recommended)

### Install Docker on Raspberry Pi

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

Log out and back in for group changes to take effect.

## Setup

### 1. Prepare Configuration

Edit `config.json` with your location and settings:

```json
{
  "location": "home",
  "s3_bucket": "s3bucket",
  "s3_region": "eu-west-2",
  "ping_targets": [
    {"name": "Router", "host": "192.168.1.1"},
    {"name": "Google DNS", "host": "8.8.8.8"}
  ],
  "ping_count": 4,
  "speedtest_enabled": true,
  "local_data_dir": "/data"
}
```

### 2. Set AWS Credentials

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your AWS credentials:

```bash
AWS_ACCESS_KEY_ID=xxxx
AWS_SECRET_ACCESS_KEY=xxxx
AWS_DEFAULT_REGION=eu-west-2
```

## Running with Docker Compose (Recommended)

### Start the monitor:

```bash
docker-compose up -d
```

### View logs:

```bash
docker-compose logs -f
```

### Stop the monitor:

```bash
docker-compose down
```

### Restart after config or script changes:

```bash
docker-compose restart
```

**Note:** Since the script is mounted as a volume, you can edit `network_monitor.py` or `config.json` on the host and just restart the container - no need to rebuild!

## Running with Docker (Without Compose)

### Build the image:

```bash
docker build -t network-monitor .
```

### Run the container:

```bash
docker run -d \
  --name network-monitor \
  --restart unless-stopped \
  --network host \
  -v $(pwd)/network_monitor.py:/app/network_monitor.py:ro \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/network_monitor_data:/data \
  -e AWS_ACCESS_KEY_ID=your_access_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret_key \
  -e AWS_DEFAULT_REGION=eu-west-2 \
  network-monitor
```

### View logs:

```bash
docker logs -f network-monitor
```

### Stop the container:

```bash
docker stop network-monitor
docker rm network-monitor
```

## Multi-Location Setup with Docker

### Home Location

Create `docker-compose.home.yml`:

```yaml
version: '3.8'

services:
  network-monitor-home:
    build: .
    container_name: network-monitor-home
    restart: unless-stopped
    volumes:
      - ./network_monitor.py:/app/network_monitor.py:ro
      - ./config.home.json:/app/config.json:ro
      - ./data_home:/data
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
    network_mode: host
```

Run with:
```bash
docker-compose -f docker-compose.home.yml up -d
```

### Office Location

Create `docker-compose.office.yml` and `config.office.json` with `"location": "office"`.

Run with:
```bash
docker-compose -f docker-compose.office.yml up -d
```

## Useful Commands

### Check container status:
```bash
docker ps
```

### View recent logs:
```bash
docker logs --tail 50 network-monitor
```

### Execute commands in container:
```bash
docker exec -it network-monitor sh
```

### Update and restart:
```bash
docker-compose pull
docker-compose up -d
```

### Remove everything and start fresh:
```bash
docker-compose down
docker rmi network-monitor
docker-compose up -d --build
```

## Troubleshooting

### Container keeps restarting

Check logs:
```bash
docker logs network-monitor
```

Common issues:
- AWS credentials not set correctly
- config.json has syntax errors
- Network connectivity issues

### Ping not working

The container uses `network_mode: host` to access the local network. If ping still doesn't work:

```bash
docker run --rm --network host alpine ping -c 4 192.168.1.1
```

### Speed test failing

Speed test requires good internet connectivity. Test manually:

```bash
docker exec -it network-monitor speedtest-cli
```

### Can't access local network devices

Make sure you're using `network_mode: host` in docker-compose.yml.

## Benefits of Docker

- **Isolated environment**: No conflicts with system packages
- **Easy updates**: Edit script/config and restart (no rebuild needed!)
- **Portable**: Same setup works on any system
- **Auto-restart**: Container restarts if it crashes
- **Resource limits**: Can set CPU/memory limits if needed
- **Multiple instances**: Run multiple locations on one device
- **Read-only scripts**: Scripts are mounted read-only for safety

## Resource Usage

The container is very lightweight:
- Image size: ~100MB
- Memory usage: ~50MB
- CPU usage: Minimal (only during tests)

## Security Notes

- Never commit `.env` file to git (it's in .gitignore)
- Use read-only mount for config.json (`:ro`)
- Container runs as non-root user
- Only necessary ports exposed
