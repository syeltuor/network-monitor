#!/usr/bin/env python3
"""
Network Monitor for Raspberry Pi
Performs ping tests and speed tests, uploads results to S3
"""

import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
import boto3
from pathlib import Path
import statistics
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal

# Load configuration from file
def load_config():
    """Load configuration from config.json or use defaults"""
    config_path = Path(__file__).parent / "config.json"
    
    # Default configuration
    default_config = {
        "location": "home",
        "s3_bucket": "your-network-monitor-bucket",
        "s3_region": "us-east-1",
        "ping_targets": [
            {"name": "Router", "host": "192.168.1.1"},
            {"name": "Google DNS", "host": "8.8.8.8"},
            {"name": "Cloudflare DNS", "host": "1.1.1.1"},
            {"name": "Google", "host": "google.com"}
        ],
        "ping_count": 4,
        "ping_parallel": True,
        "continuous_mode": False,
        "continuous_interval_seconds": 30,
        "speedtest_enabled": True,
        "speedtest_interval_minutes": 60,
        "local_data_dir": "/home/pi/network_monitor_data"
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                print(f"Loaded configuration from {config_path}")
                return config
        except Exception as e:
            print(f"Error loading config.json: {e}")
            print("Using default configuration")
            return default_config
    else:
        print(f"config.json not found at {config_path}")
        print("Using default configuration")
        return default_config

CONFIG = load_config()


def ping_test(host, count=4):
    """Perform ping test and return results"""
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "2", host],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            # Parse statistics line: "rtt min/avg/max/mdev = 1.234/2.345/3.456/0.123 ms"
            for line in lines:
                if "rtt min/avg/max/mdev" in line or "round-trip" in line:
                    stats = line.split('=')[1].strip().split()[0]
                    min_ms, avg_ms, max_ms, mdev = stats.split('/')
                    
                    # Parse packet loss
                    packet_loss = 0
                    for l in lines:
                        if "packet loss" in l:
                            packet_loss = float(l.split('%')[0].split()[-1])
                            break
                    
                    return {
                        "success": True,
                        "min_ms": float(min_ms),
                        "avg_ms": float(avg_ms),
                        "max_ms": float(max_ms),
                        "packet_loss": packet_loss
                    }
        
        return {"success": False, "error": "No response"}
    
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def speedtest():
    """Perform speed test using speedtest-cli"""
    try:
        result = subprocess.run(
            ["speedtest-cli", "--json"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "success": True,
                "download_mbps": round(data["download"] / 1_000_000, 2),
                "upload_mbps": round(data["upload"] / 1_000_000, 2),
                "ping_ms": data["ping"],
                "server": data["server"]["sponsor"],
                "server_location": f"{data['server']['name']}, {data['server']['country']}"
            }
        
        return {"success": False, "error": "Speed test failed"}
    
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_tests():
    """Run all network tests"""
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    print(f"Running tests at {timestamp} for location: {CONFIG['location']}")
    
    # Ping tests - parallel or sequential based on config
    ping_results = []
    if CONFIG.get("ping_parallel", True):
        # Run pings in parallel
        with ThreadPoolExecutor(max_workers=len(CONFIG["ping_targets"])) as executor:
            future_to_target = {
                executor.submit(ping_test, target["host"], CONFIG["ping_count"]): target
                for target in CONFIG["ping_targets"]
            }
            
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    result = future.result()
                    print(f"  Pinged {target['name']} ({target['host']}): {'✓' if result['success'] else '✗'}")
                    ping_results.append({
                        "name": target["name"],
                        "host": target["host"],
                        **result
                    })
                except Exception as e:
                    print(f"  Error pinging {target['name']}: {e}")
                    ping_results.append({
                        "name": target["name"],
                        "host": target["host"],
                        "success": False,
                        "error": str(e)
                    })
    else:
        # Run pings sequentially (original behavior)
        for target in CONFIG["ping_targets"]:
            print(f"  Pinging {target['name']} ({target['host']})...")
            result = ping_test(target["host"], CONFIG["ping_count"])
            ping_results.append({
                "name": target["name"],
                "host": target["host"],
                **result
            })
    
    # Speed test
    speed_result = None
    if CONFIG["speedtest_enabled"]:
        print("  Running speed test...")
        speed_result = speedtest()
    
    return {
        "timestamp": timestamp,
        "location": CONFIG["location"],
        "ping_tests": ping_results,
        "speed_test": speed_result
    }


def save_local(data):
    """Save data locally"""
    data_dir = Path(CONFIG["local_data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Save individual result with location
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y/%m/%d")
    location_dir = data_dir / CONFIG["location"] / date_str
    location_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    result_file = location_dir / f"result_{timestamp}.json"
    
    with open(result_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return result_file


def upload_to_s3(data):
    """Upload results to S3"""
    try:
        s3 = boto3.client('s3', region_name=CONFIG["s3_region"])
        
        # Upload individual result with location prefix
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y/%m/%d")
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        location = CONFIG["location"]
        key = f"results/{location}/{date_str}/result_{timestamp}.json"
        
        s3.put_object(
            Bucket=CONFIG["s3_bucket"],
            Key=key,
            Body=json.dumps(data),
            ContentType="application/json"
        )
        
        print(f"  Uploaded to s3://{CONFIG['s3_bucket']}/{key}")
        
        # Update rolling summaries
        update_summaries(s3, data)
        
        return True
    
    except Exception as e:
        print(f"  Error uploading to S3: {e}")
        return False


def aggregate_results(results, interval_minutes):
    """
    Aggregate results into time buckets
    
    Args:
        results: List of test results
        interval_minutes: Size of time buckets in minutes (e.g., 5, 60, 720)
    
    Returns:
        List of aggregated results
    """
    if not results:
        return []
    
    # Group results by time bucket
    buckets = {}
    
    for result in results:
        timestamp = datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        
        # Calculate bucket key (round down to nearest interval)
        bucket_timestamp = timestamp.replace(second=0, microsecond=0)
        minutes_since_epoch = int(bucket_timestamp.timestamp() / 60)
        bucket_minutes = (minutes_since_epoch // interval_minutes) * interval_minutes
        bucket_key = bucket_minutes
        
        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(result)
    
    # Aggregate each bucket
    aggregated = []
    
    for bucket_minutes in sorted(buckets.keys()):
        bucket_results = buckets[bucket_minutes]
        
        # Use the middle timestamp of the bucket as representative time
        bucket_timestamp = datetime.fromtimestamp(bucket_minutes * 60, tz=timezone.utc)
        
        # Aggregate ping tests
        ping_aggregates = {}
        
        for result in bucket_results:
            for ping in result.get("ping_tests", []):
                name = ping["name"]
                if name not in ping_aggregates:
                    ping_aggregates[name] = {
                        "name": name,
                        "host": ping["host"],
                        "avg_ms_values": [],
                        "min_ms_values": [],
                        "max_ms_values": [],
                        "packet_loss_values": [],
                        "success_count": 0,
                        "total_count": 0
                    }
                
                ping_aggregates[name]["total_count"] += 1
                
                if ping.get("success"):
                    ping_aggregates[name]["success_count"] += 1
                    ping_aggregates[name]["avg_ms_values"].append(ping.get("avg_ms", 0))
                    ping_aggregates[name]["min_ms_values"].append(ping.get("min_ms", 0))
                    ping_aggregates[name]["max_ms_values"].append(ping.get("max_ms", 0))
                    ping_aggregates[name]["packet_loss_values"].append(ping.get("packet_loss", 0))
        
        # Calculate averages for each ping target
        aggregated_pings = []
        for name, agg in ping_aggregates.items():
            if agg["success_count"] > 0:
                aggregated_pings.append({
                    "name": name,
                    "host": agg["host"],
                    "success": True,
                    "avg_ms": round(statistics.mean(agg["avg_ms_values"]), 2),
                    "min_ms": round(min(agg["min_ms_values"]), 2),
                    "max_ms": round(max(agg["max_ms_values"]), 2),
                    "packet_loss": round(statistics.mean(agg["packet_loss_values"]), 2),
                    "sample_count": agg["success_count"]
                })
            else:
                aggregated_pings.append({
                    "name": name,
                    "host": agg["host"],
                    "success": False,
                    "error": "All tests failed in this interval",
                    "sample_count": agg["total_count"]
                })
        
        # Aggregate speed tests (if any)
        speed_tests = [r.get("speed_test") for r in bucket_results if r.get("speed_test") and r["speed_test"].get("success")]
        aggregated_speed = None
        
        if speed_tests:
            aggregated_speed = {
                "success": True,
                "download_mbps": round(statistics.mean([s["download_mbps"] for s in speed_tests]), 2),
                "upload_mbps": round(statistics.mean([s["upload_mbps"] for s in speed_tests]), 2),
                "ping_ms": round(statistics.mean([s["ping_ms"] for s in speed_tests]), 2),
                "server": speed_tests[0]["server"],  # Use first server name
                "sample_count": len(speed_tests)
            }
        
        # Create aggregated result
        aggregated.append({
            "timestamp": bucket_timestamp.isoformat().replace('+00:00', 'Z'),
            "location": bucket_results[0]["location"],
            "ping_tests": aggregated_pings,
            "speed_test": aggregated_speed,
            "aggregated": True,
            "interval_minutes": interval_minutes,
            "sample_count": len(bucket_results)
        })
    
    return aggregated


def update_summaries(s3, new_data):
    """Update rolling summary files (1h, 24h, 7d, 30d)"""
    now = datetime.now(timezone.utc)
    location = CONFIG["location"]
    
    # Define periods with their time windows and aggregation intervals
    # (period_name, hours_to_keep, aggregation_minutes)
    periods = [
        ("1h", 1, None),      # 1 hour - no aggregation (raw data)
        ("24h", 24, 10),      # 24 hours - 10 minute averages
        ("7d", 24*7, 60),     # 7 days - 1 hour averages
        ("30d", 24*30, 360)   # 30 days - 6 hour averages
    ]
    
    for period, hours, agg_minutes in periods:
        try:
            # Try to get existing summary for this location
            try:
                response = s3.get_object(
                    Bucket=CONFIG["s3_bucket"],
                    Key=f"summaries/{location}/summary_{period}.json"
                )
                summary = json.loads(response['Body'].read())
            except s3.exceptions.NoSuchKey:
                summary = {"location": location, "results": []}
            
            # Add new data
            summary["results"].append(new_data)
            
            # Filter to keep only data within the period
            cutoff = now - timedelta(hours=hours)
            summary["results"] = [
                r for r in summary["results"]
                if datetime.fromisoformat(r["timestamp"].replace('Z', '+00:00')).replace(tzinfo=timezone.utc) > cutoff
            ]
            
            # Aggregate if needed
            if agg_minutes:
                summary["results"] = aggregate_results(summary["results"], agg_minutes)
            
            # Upload updated summary
            s3.put_object(
                Bucket=CONFIG["s3_bucket"],
                Key=f"summaries/{location}/summary_{period}.json",
                Body=json.dumps(summary),
                ContentType="application/json"
            )
            
            result_count = len(summary["results"])
            agg_info = f" (aggregated to {agg_minutes}min intervals)" if agg_minutes else ""
            print(f"  Updated {period} summary ({result_count} results{agg_info})")
        
        except Exception as e:
            print(f"  Error updating {period} summary: {e}")
    
    # Update locations list
    update_locations_list(s3)


def update_locations_list(s3):
    """Update the list of available locations"""
    try:
        # List all location folders in summaries/
        response = s3.list_objects_v2(
            Bucket=CONFIG["s3_bucket"],
            Prefix="summaries/",
            Delimiter="/"
        )
        
        locations = []
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                location = prefix['Prefix'].replace('summaries/', '').replace('/', '')
                if location:
                    locations.append(location)
        
        # Upload locations list
        s3.put_object(
            Bucket=CONFIG["s3_bucket"],
            Key="locations.json",
            Body=json.dumps({"locations": sorted(locations)}),
            ContentType="application/json"
        )
        
        print(f"  Updated locations list: {locations}")
    
    except Exception as e:
        print(f"  Error updating locations list: {e}")


def main():
    """Main execution"""
    print("=" * 50)
    print("Network Monitor Starting")
    print(f"Mode: {'Continuous' if CONFIG.get('continuous_mode', False) else 'Single Run'}")
    print(f"Location: {CONFIG['location']}")
    print(f"Ping Mode: {'Parallel' if CONFIG.get('ping_parallel', True) else 'Sequential'}")
    print("=" * 50)
    
    if CONFIG.get("continuous_mode", False):
        run_continuous()
    else:
        run_single()


def run_single():
    """Run tests once and exit"""
    # Run tests
    results = run_tests()
    
    # Save locally
    local_file = save_local(results)
    print(f"  Saved locally to {local_file}")
    
    # Upload to S3
    upload_to_s3(results)
    
    print("=" * 50)
    print("Tests completed")
    print("=" * 50)


def run_continuous():
    """Run tests continuously in a loop"""
    interval = CONFIG.get("continuous_interval_seconds", 30)
    speedtest_interval = CONFIG.get("speedtest_interval_minutes", 60)
    last_speedtest = datetime.now(timezone.utc)
    
    print(f"Running continuously every {interval} seconds")
    print(f"Speed tests every {speedtest_interval} minutes (if enabled)")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n" + "=" * 50)
        print("Shutting down gracefully...")
        print("=" * 50)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    iteration = 0
    while True:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        
        try:
            # Check if we should run speed test this iteration
            now = datetime.now(timezone.utc)
            run_speedtest = False
            
            if CONFIG["speedtest_enabled"]:
                minutes_since_last = (now - last_speedtest).total_seconds() / 60
                if minutes_since_last >= speedtest_interval:
                    run_speedtest = True
                    last_speedtest = now
            
            # Temporarily override speedtest setting for this run
            original_speedtest_setting = CONFIG["speedtest_enabled"]
            CONFIG["speedtest_enabled"] = run_speedtest
            
            # Run tests
            results = run_tests()
            
            # Restore original setting
            CONFIG["speedtest_enabled"] = original_speedtest_setting
            
            # Save locally
            local_file = save_local(results)
            print(f"  Saved locally to {local_file}")
            
            # Upload to S3
            upload_to_s3(results)
            
            print(f"  Waiting {interval} seconds until next run...")
            time.sleep(interval)
            
        except Exception as e:
            print(f"  Error in iteration {iteration}: {e}")
            print(f"  Continuing... waiting {interval} seconds")
            time.sleep(interval)


if __name__ == "__main__":
    main()
