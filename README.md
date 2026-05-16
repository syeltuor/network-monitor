# Network Monitor

A complete network monitoring solution that runs on Raspberry Pi, uploads data to AWS S3, and displays results in a web dashboard.

## Features

- **Ping Tests**: Monitor latency to multiple configurable targets (router, DNS servers, websites)
- **Speed Tests**: Track download/upload speeds using speedtest-cli
- **Packet Loss Tracking**: Monitor connection stability
- **Historical Data**: View 24-hour, 7-day, and 30-day trends
- **Real-time Dashboard**: Beautiful web interface with interactive charts
- **S3 Storage**: Reliable cloud storage for all test results

## Architecture

```
Raspberry Pi → AWS S3 → Static Website
   (Monitor)    (Storage)   (Dashboard)
```

## Setup Instructions

### 1. AWS Setup

First, configure your AWS S3 bucket:

```bash
# Edit the bucket name in setup_aws.sh
nano setup_aws.sh
# Change: BUCKET_NAME="your-network-monitor-bucket"

# Make it executable and run
chmod +x setup_aws.sh
./setup_aws.sh
```

This script will:
- Create an S3 bucket
- Configure it for static website hosting
- Set up CORS and public access policies
- Create an IAM user for the Raspberry Pi
- Provide AWS credentials

**Save the AWS credentials** shown at the end - you'll need them for the Raspberry Pi.

### 2. Upload Dashboard to S3

```bash
# Update config in dashboard.js
nano dashboard.js
# Change: bucketName: 'your-network-monitor-bucket'
# Change: region: 'us-east-1'

# Upload to S3
aws s3 cp index.html s3://your-network-monitor-bucket/
aws s3 cp dashboard.js s3://your-network-monitor-bucket/
```

Your dashboard will be available at:
`http://your-network-monitor-bucket.s3-website-us-east-1.amazonaws.com`

### 3. Raspberry Pi Setup

On your Raspberry Pi:

```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y python3-pip awscli

# Install Python dependencies
pip3 install boto3 speedtest-cli

# Configure AWS credentials (use the credentials from step 1)
aws configure
# Enter: Access Key ID
# Enter: Secret Access Key
# Enter: Region (e.g., us-east-1)
# Enter: Output format (json)

# Copy the monitoring script
# Transfer network_monitor.py and config.json to your Pi

# Edit configuration
nano config.json
# Update: s3_bucket, ping_targets, etc.

# Make the script executable
chmod +x network_monitor.py

# Test it manually
./network_monitor.py
```

### 4. Set Up Automated Monitoring

Create a cron job to run tests every 5 minutes:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path as needed):
*/5 * * * * /usr/bin/python3 /home/pi/network_monitor.py >> /home/pi/monitor.log 2>&1
```

Or every 15 minutes for less frequent testing:
```bash
*/15 * * * * /usr/bin/python3 /home/pi/network_monitor.py >> /home/pi/monitor.log 2>&1
```

## Configuration

### config.json

```json
{
  "s3_bucket": "your-network-monitor-bucket",
  "s3_region": "us-east-1",
  "ping_targets": [
    {"name": "Router", "host": "192.168.1.1"},
    {"name": "Google DNS", "host": "8.8.8.8"},
    {"name": "Cloudflare DNS", "host": "1.1.1.1"},
    {"name": "Google", "host": "google.com"}
  ],
  "ping_count": 4,
  "speedtest_enabled": true,
  "local_data_dir": "/home/pi/network_monitor_data"
}
```

**Customization:**
- `ping_targets`: Add/remove targets as needed. Update your router IP if different.
- `ping_count`: Number of ping packets to send (default: 4)
- `speedtest_enabled`: Set to `false` to disable speed tests (saves time)
- `local_data_dir`: Local backup location for test results

## Monitoring

### View Logs

```bash
# View recent logs
tail -f /home/pi/monitor.log

# Check if cron job is running
grep CRON /var/log/syslog | tail
```

### Manual Test

```bash
# Run a single test
./network_monitor.py

# Check local data
ls -lh /home/pi/network_monitor_data/
```

### Dashboard

Open your S3 website URL in a browser:
- View current status
- Switch between 24h, 7d, and 30d views
- Interactive charts for ping, speed, and packet loss

## Troubleshooting

### No data showing on dashboard

1. Check if tests are running: `tail /home/pi/monitor.log`
2. Verify AWS credentials: `aws s3 ls s3://your-bucket-name/`
3. Check S3 bucket has data: `aws s3 ls s3://your-bucket-name/summaries/`

### Speed test failing

```bash
# Test speedtest-cli manually
speedtest-cli --json

# If it fails, try reinstalling
pip3 install --upgrade speedtest-cli
```

### Ping tests failing

- Verify target hosts are reachable: `ping -c 4 8.8.8.8`
- Check your router IP: `ip route | grep default`
- Update `config.json` with correct router IP

### AWS upload failing

```bash
# Test AWS credentials
aws s3 ls

# Reconfigure if needed
aws configure
```

## Cost Estimate

AWS S3 costs are minimal for this use case:
- Storage: ~$0.023/GB/month (expect < 1GB for months of data)
- Requests: ~$0.0004 per 1,000 PUT requests
- Data transfer: Free for uploads, minimal for dashboard views

**Estimated monthly cost: < $0.50**

## Files

- `network_monitor.py` - Main monitoring script for Raspberry Pi
- `config.json` - Configuration file
- `setup_aws.sh` - AWS S3 setup script
- `index.html` - Dashboard HTML
- `dashboard.js` - Dashboard JavaScript
- `README.md` - This file

## License

Free to use and modify for personal or commercial use.
