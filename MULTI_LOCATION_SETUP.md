# Multi-Location Setup Guide

Your network monitor now supports multiple locations! Each Raspberry Pi can monitor a different location (home, office, etc.) and the dashboard lets you switch between them.

## How It Works

- Each location's data is stored separately in S3 under `summaries/{location}/`
- The dashboard automatically detects available locations
- A dropdown menu lets you switch between locations
- All locations share the same S3 bucket

## Setting Up Multiple Locations

### Location 1: Home

1. On your home Raspberry Pi, edit `config.json`:
```json
{
  "location": "home",
  "s3_bucket": "s3bucket",
  "s3_region": "eu-west-2",
  "ping_targets": [
    {"name": "Router", "host": "192.168.1.1"},
    {"name": "Google DNS", "host": "8.8.8.8"}
  ],
  ...
}
```

2. Run the monitor:
```bash
while true; do python3 network_monitor.py; sleep 300; done
```

### Location 2: Office

1. On your office Raspberry Pi, edit `config.json`:
```json
{
  "location": "office",
  "s3_bucket": "s3bucket",
  "s3_region": "eu-west-2",
  "ping_targets": [
    {"name": "Router", "host": "192.168.0.1"},
    {"name": "Google DNS", "host": "8.8.8.8"}
  ],
  ...
}
```

2. Configure AWS credentials (same as home):
```bash
aws configure
# Use the same Access Key and Secret Key
```

3. Run the monitor:
```bash
while true; do python3 network_monitor.py; sleep 300; done
```

### Location 3: Vacation Home, etc.

Repeat the same process with `"location": "vacation"` or any other name.

## Dashboard Usage

1. Open your dashboard: `http://s3bucket.s3-website-eu-west-2.amazonaws.com`

2. You'll see a dropdown menu at the top showing all available locations

3. Select a location to view its data

4. The dashboard will show:
   - Current status for that location
   - Historical charts for that location
   - You can switch time periods (24h, 7d, 30d) for each location

## Location Names

- Use lowercase, no spaces (e.g., "home", "office", "vacation")
- Keep them short and descriptive
- They'll be capitalized automatically in the dropdown

## Data Structure

```
S3 Bucket:
├── locations.json (auto-generated list of all locations)
├── summaries/
│   ├── home/
│   │   ├── summary_24h.json
│   │   ├── summary_7d.json
│   │   └── summary_30d.json
│   ├── office/
│   │   ├── summary_24h.json
│   │   ├── summary_7d.json
│   │   └── summary_30d.json
└── results/
    ├── home/
    │   └── 2026/02/07/result_*.json
    └── office/
        └── 2026/02/07/result_*.json
```

## Troubleshooting

### Location not showing in dropdown

- Make sure the Raspberry Pi has run at least once
- Check S3: `aws s3 ls s3://your-bucket/summaries/`
- Verify locations.json exists: `aws s3 cp s3://your-bucket/locations.json -`

### Wrong location showing data

- Check the `location` field in config.json on each Pi
- Restart the monitoring script after changing config

### Both locations showing same data

- Verify each Pi has a different `location` value in config.json
- Check the uploaded files: `aws s3 ls s3://your-bucket/summaries/ --recursive`

## Tips

- Each location can have different ping targets (different router IPs, local servers, etc.)
- All locations share the same AWS credentials
- You can add/remove locations at any time
- The dashboard automatically updates the location list
