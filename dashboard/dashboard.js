// Network Monitor Dashboard JavaScript
// Configuration - update this with your S3 bucket details
const CONFIG = {
    bucketName: 'xxx-network-monitor-bucket',
    region: 'eu-west-2',
    baseUrl: null // Will be set automatically
};

CONFIG.baseUrl = `https://${CONFIG.bucketName}.s3.${CONFIG.region}.amazonaws.com`;

let currentPeriod = '1h';
let currentLocation = null;
let charts = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadLocations();
});

function setupEventListeners() {
    // Period buttons
    document.querySelectorAll('.controls button[data-period]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.controls button[data-period]').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentPeriod = e.target.dataset.period;
            loadData();
        });
    });
    
    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', () => {
        loadData();
    });
    
    // Location selector
    document.getElementById('locationSelector').addEventListener('change', (e) => {
        currentLocation = e.target.value;
        loadData();
    });
}

async function loadLocations() {
    try {
        const url = `${CONFIG.baseUrl}/locations.json?t=${Date.now()}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Failed to load locations: ${response.status}`);
        }
        
        const data = await response.json();
        const selector = document.getElementById('locationSelector');
        
        if (data.locations && data.locations.length > 0) {
            selector.innerHTML = data.locations.map(loc => 
                `<option value="${loc}">${loc.charAt(0).toUpperCase() + loc.slice(1)}</option>`
            ).join('');
            
            currentLocation = data.locations[0];
            loadData();
        } else {
            selector.innerHTML = '<option value="">No locations available</option>';
            showError('No monitoring locations found. Make sure the Raspberry Pi is running.');
        }
    } catch (error) {
        showError(`Error loading locations: ${error.message}`);
        console.error('Load locations error:', error);
    }
}

async function loadData() {
    if (!currentLocation) {
        return;
    }
    
    try {
        showLoading();
        const url = `${CONFIG.baseUrl}/summaries/${currentLocation}/summary_${currentPeriod}.json?t=${Date.now()}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.results || data.results.length === 0) {
            showError('No data available yet. Make sure the Raspberry Pi is running.');
            return;
        }
        
        hideError();
        updateStatus(data.results);
        updateCharts(data.results);
        
    } catch (error) {
        showError(`Error loading data: ${error.message}`);
        console.error('Load error:', error);
    }
}

function updateStatus(results) {
    const latest = results[results.length - 1];
    const timestamp = new Date(latest.timestamp);
    
    let updateText = `Last updated: ${timestamp.toLocaleString()}`;
    if (latest.aggregated) {
        updateText += ` (${latest.interval_minutes}min averages)`;
    }
    
    document.getElementById('lastUpdate').textContent = updateText;
    
    const statusGrid = document.getElementById('statusGrid');
    statusGrid.innerHTML = '';
    
    // Ping status cards
    if (latest.ping_tests) {
        latest.ping_tests.forEach(ping => {
            let label = ping.success ? `Loss: ${ping.packet_loss}%` : ping.error;
            if (ping.sample_count && ping.sample_count > 1) {
                label += ` (${ping.sample_count} samples)`;
            }
            
            const card = createStatusCard(
                ping.name,
                ping.success ? `${ping.avg_ms.toFixed(1)} ms` : 'Failed',
                ping.success ? (ping.avg_ms < 50 ? 'success' : ping.avg_ms < 100 ? 'warning' : 'error') : 'error',
                label
            );
            statusGrid.appendChild(card);
        });
    }
    
    // Speed test status
    if (latest.speed_test && latest.speed_test.success) {
        const speed = latest.speed_test;
        
        let downloadLabel = `Server: ${speed.server}`;
        let uploadLabel = `Ping: ${speed.ping_ms} ms`;
        
        if (speed.sample_count && speed.sample_count > 1) {
            downloadLabel += ` (${speed.sample_count} samples)`;
        }
        
        // Download card
        const downloadCard = createStatusCard(
            'Download Speed',
            `${speed.download_mbps} Mbps`,
            'success',
            downloadLabel
        );
        statusGrid.appendChild(downloadCard);
        
        // Upload card
        const uploadCard = createStatusCard(
            'Upload Speed',
            `${speed.upload_mbps} Mbps`,
            'success',
            uploadLabel
        );
        statusGrid.appendChild(uploadCard);
    }
}

function createStatusCard(title, value, status, label) {
    const card = document.createElement('div');
    card.className = `status-card ${status}`;
    card.innerHTML = `
        <h3>${title}</h3>
        <div class="status-value">${value}</div>
        <div class="status-label">${label}</div>
    `;
    return card;
}

function updateCharts(results) {
    const timestamps = results.map(r => new Date(r.timestamp));
    
    // Ping chart
    updatePingChart(results, timestamps);
    
    // Speed chart
    updateSpeedChart(results, timestamps);
    
    // Packet loss chart
    updatePacketLossChart(results, timestamps);
}

function updatePingChart(results, timestamps) {
    const datasets = [];
    const colors = ['#60a5fa', '#34d399', '#fbbf24', '#f87171'];
    
    // Get unique ping targets
    const targets = results[0].ping_tests.map(p => p.name);
    
    targets.forEach((target, idx) => {
        const data = results.map(r => {
            const ping = r.ping_tests.find(p => p.name === target);
            return ping && ping.success ? ping.avg_ms : null;
        });
        
        datasets.push({
            label: target,
            data: data,
            borderColor: colors[idx % colors.length],
            backgroundColor: colors[idx % colors.length] + '20',
            tension: 0.3,
            spanGaps: true
        });
    });
    
    createOrUpdateChart('pingChart', 'line', timestamps, datasets, 'Latency (ms)');
}

function updateSpeedChart(results, timestamps) {
    const downloadData = results.map(r => 
        r.speed_test && r.speed_test.success ? r.speed_test.download_mbps : null
    );
    
    const uploadData = results.map(r => 
        r.speed_test && r.speed_test.success ? r.speed_test.upload_mbps : null
    );
    
    const datasets = [
        {
            label: 'Download',
            data: downloadData,
            borderColor: '#60a5fa',
            backgroundColor: '#60a5fa20',
            tension: 0.3,
            spanGaps: true
        },
        {
            label: 'Upload',
            data: uploadData,
            borderColor: '#34d399',
            backgroundColor: '#34d39920',
            tension: 0.3,
            spanGaps: true
        }
    ];
    
    createOrUpdateChart('speedChart', 'line', timestamps, datasets, 'Speed (Mbps)');
}

function updatePacketLossChart(results, timestamps) {
    const datasets = [];
    const colors = ['#60a5fa', '#34d399', '#fbbf24', '#f87171'];
    
    const targets = results[0].ping_tests.map(p => p.name);
    
    targets.forEach((target, idx) => {
        const data = results.map(r => {
            const ping = r.ping_tests.find(p => p.name === target);
            return ping && ping.success ? ping.packet_loss : null;
        });
        
        datasets.push({
            label: target,
            data: data,
            borderColor: colors[idx % colors.length],
            backgroundColor: colors[idx % colors.length] + '20',
            tension: 0.3,
            spanGaps: true
        });
    });
    
    createOrUpdateChart('packetLossChart', 'line', timestamps, datasets, 'Packet Loss (%)');
}

function createOrUpdateChart(canvasId, type, labels, datasets, yAxisLabel) {
    const ctx = document.getElementById(canvasId);
    
    // Determine time format based on current period
    const timeUnit = currentPeriod === '1h' ? 'minute' : currentPeriod === '24h' ? 'hour' : 'day';
    const displayFormats = {
        minute: 'HH:mm',
        hour: 'HH:mm',
        day: 'MMM d'
    };
    const tooltipFormat = currentPeriod === '1h' || currentPeriod === '24h' ? 'MMM d, HH:mm' : 'MMM d, yyyy HH:mm';
    
    if (charts[canvasId]) {
        charts[canvasId].data.labels = labels;
        charts[canvasId].data.datasets = datasets;
        // Update time scale options
        charts[canvasId].options.scales.x.time.unit = timeUnit;
        charts[canvasId].options.scales.x.time.displayFormats = displayFormats;
        charts[canvasId].options.scales.x.time.tooltipFormat = tooltipFormat;
        charts[canvasId].update();
    } else {
        charts[canvasId] = new Chart(ctx, {
            type: type,
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#e2e8f0'
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: timeUnit,
                            displayFormats: displayFormats,
                            tooltipFormat: tooltipFormat
                        },
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: '#334155'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: yAxisLabel,
                            color: '#e2e8f0'
                        },
                        ticks: {
                            color: '#94a3b8'
                        },
                        grid: {
                            color: '#334155'
                        }
                    }
                }
            }
        });
    }
}

function showLoading() {
    document.getElementById('statusGrid').innerHTML = '<div class="loading">Loading...</div>';
}

function showError(message) {
    const container = document.getElementById('errorContainer');
    container.innerHTML = `<div class="error-message">${message}</div>`;
}

function hideError() {
    document.getElementById('errorContainer').innerHTML = '';
}
