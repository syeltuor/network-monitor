# Continuous Monitoring Mode

The network monitor now supports continuous monitoring mode for catching network blips and intermittent issues.

## New Configuration Options

Add these to your `scripts/config.json`:

```json
{
  "ping_parallel": true,                    // Run pings in parallel (faster)
  "continuous_mode": false,                 // Enable continuous monitoring
  "continuous_interval_seconds": 30,        // Time between test runs
  "speedtest_interval_minutes": 60          // Run speed test every N minutes
}
```

## Modes

### Single Run Mode (default)
- `continuous_mode: false`
- Runs once and exits
- Use with cron for scheduled testing
- Original behavior

### Continuous Mode
- `continuous_mode: true`
- Runs indefinitely in a loop
- Pings all targets every `continuous_interval_seconds`
- Speed tests run every `speedtest_interval_minutes` (if enabled)
- Better for catching transient network issues

## Parallel vs Sequential Pings

### Parallel (recommended)
- `ping_parallel: true`
- All targets pinged simultaneously
- Faster execution (~10 seconds vs 30-40 seconds)
- Better for frequent monitoring

### Sequential
- `ping_parallel: false`
- Targets pinged one at a time
- More precise timing per target
- Use if you need to isolate measurements

## Running Continuous Mode

### Option 1: Manually (for testing)
```bash
cd scripts
# Edit config.json and set continuous_mode: true
python3 network_monitor.py
# Press Ctrl+C to stop
```

### Option 2: As a systemd service (recommended for production)

1. Copy the service file:
```bash
sudo cp network-monitor.service /etc/systemd/system/
```

2. Edit the service file if needed (adjust paths):
```bash
sudo nano /etc/systemd/system/network-monitor.service
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable network-monitor
sudo systemctl start network-monitor
```

4. Check status:
```bash
sudo systemctl status network-monitor
```

5. View logs:
```bash
sudo journalctl -u network-monitor -f
```

6. Stop the service:
```bash
sudo systemctl stop network-monitor
```

## Example Configurations

### High-frequency blip detection (no speed tests)
```json
{
  "ping_parallel": true,
  "continuous_mode": true,
  "continuous_interval_seconds": 15,
  "speedtest_enabled": false
}
```
Pings every 15 seconds, no speed tests.

### Balanced monitoring
```json
{
  "ping_parallel": true,
  "continuous_mode": true,
  "continuous_interval_seconds": 30,
  "speedtest_enabled": true,
  "speedtest_interval_minutes": 60
}
```
Pings every 30 seconds, speed test every hour.

### Traditional cron mode
```json
{
  "ping_parallel": true,
  "continuous_mode": false,
  "speedtest_enabled": true
}
```
Run via cron, parallel pings for speed.

## Monitoring Coverage

With different configurations:
- Every 5 minutes (cron): ~2.7% coverage
- Every 1 minute (cron): ~15% coverage
- Every 30 seconds (continuous): ~30% coverage
- Every 15 seconds (continuous): ~60% coverage

Higher coverage = better chance of catching brief network issues.
