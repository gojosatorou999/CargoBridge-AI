/* CargoBridge AI — Analyst Dashboard JS: AIS map, heatmap, Chart.js charts */

let analystMap, heatLayer, vesselLayer;
let chartType, chartTimeline, chartThroughput, chartSavings;

// ── Map init ─────────────────────────────────────────────────────────────────
function initAnalystMap() {
  const el = document.getElementById('analyst-map');
  if (!el || typeof L === 'undefined') return;

  analystMap = L.map('analyst-map').setView([20.5937, 78.9629], 5);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '©OpenStreetMap ©CartoDB',
    maxZoom: 19,
  }).addTo(analystMap);

  // Heatmap layer
  heatLayer = L.layerGroup().addTo(analystMap);

  // Vessel marker layer
  vesselLayer = L.layerGroup().addTo(analystMap);

  loadHeatmap();
  loadVessels();
}

// ── Heatmap ───────────────────────────────────────────────────────────────────
function loadHeatmap() {
  fetch('/api/reports?status=approved')
    .then(r => r.json())
    .then(data => {
      heatLayer.clearLayers();
      const pts = data.reports
        .filter(r => r.lat && r.lon)
        .map(r => [r.lat, r.lon, 0.6]);
      if (typeof L.heatLayer !== 'undefined' && pts.length) {
        const heat = L.heatLayer(pts, { radius: 35, blur: 25, maxZoom: 14,
          gradient: { 0.2: '#00d4ff', 0.6: '#7b2fff', 1.0: '#ff4757' } });
        heatLayer.addLayer(heat);
      }
    })
    .catch(() => {});
}

// ── AIS vessel markers ────────────────────────────────────────────────────────
function loadVessels() {
  fetch('/api/ais/vessels')
    .then(r => r.json())
    .then(vessels => {
      vesselLayer.clearLayers();
      vessels.forEach(v => {
        if (!v.lat || !v.lon) return;
        const icon = L.divIcon({
          className: '',
          html: `<div style="
            width:28px;height:28px;
            background:rgba(0,212,255,0.2);
            border:2px solid #00d4ff;
            border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            font-size:14px;cursor:pointer;
            box-shadow:0 0 10px rgba(0,212,255,0.5);">🚢</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });
        const marker = L.marker([v.lat, v.lon], { icon });
        marker.bindPopup(`
          <div style="background:#0f1629;color:#e8eaf6;padding:8px;border-radius:8px;min-width:180px;border:1px solid rgba(0,212,255,0.3)">
            <b style="color:#00d4ff">${v.vessel_name || 'Unknown'}</b><br>
            <span style="color:#8892b0;font-size:11px">MMSI: ${v.mmsi || '—'}</span><br>
            Dest: ${v.dest || '—'}<br>
            ETA: ${v.eta ? new Date(v.eta).toLocaleString() : '—'}<br>
            Speed: ${v.speed || 0} kn
          </div>
        `, { className: 'dark-popup' });
        vesselLayer.addLayer(marker);
      });
    })
    .catch(() => {});
}

// ── Layer toggles ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('toggle-heat')?.addEventListener('change', e => {
    e.target.checked ? analystMap?.addLayer(heatLayer) : analystMap?.removeLayer(heatLayer);
  });
  document.getElementById('toggle-vessels')?.addEventListener('change', e => {
    e.target.checked ? analystMap?.addLayer(vesselLayer) : analystMap?.removeLayer(vesselLayer);
  });
});

// ── Charts ────────────────────────────────────────────────────────────────────
function initCharts() {
  fetch('/api/analytics/charts')
    .then(r => r.json())
    .then(data => {
      buildTypeChart(data.type_distribution || []);
      buildTimelineChart(data.timeline || []);
      buildThroughputChart(data.throughput || []);
      buildSavingsChart(data.savings || []);
    })
    .catch(() => {});
}

const CHART_COLORS = ['#00d4ff','#7b2fff','#00ff88','#ff6b35','#ffd700','#ff4757','#9c27b0','#4caf50'];

function buildTypeChart(data) {
  const ctx = document.getElementById('chart-type');
  if (!ctx || !data.length) return;
  if (chartType) chartType.destroy();
  chartType = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.type.replace(/_/g, ' ')),
      datasets: [{ data: data.map(d => d.count), backgroundColor: CHART_COLORS,
        borderColor: 'rgba(255,255,255,0.05)', borderWidth: 2 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#8892b0', font: { size: 12 } } },
      },
    },
  });
}

function buildTimelineChart(data) {
  const ctx = document.getElementById('chart-timeline');
  if (!ctx) return;
  if (chartTimeline) chartTimeline.destroy();
  chartTimeline = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.date),
      datasets: [{
        label: 'Reports',
        data: data.map(d => d.count),
        borderColor: '#00d4ff',
        backgroundColor: 'rgba(0,212,255,0.1)',
        tension: 0.4, fill: true, pointRadius: 3,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#8892b0' } } },
      scales: {
        x: { ticks: { color: '#4a5568' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#4a5568' }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
      },
    },
  });
}

function buildThroughputChart(data) {
  const ctx = document.getElementById('chart-throughput');
  if (!ctx) return;
  if (chartThroughput) chartThroughput.destroy();
  chartThroughput = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => `${d.hour}:00`),
      datasets: [{
        label: 'Crane moves/hr',
        data: data.map(d => d.moves),
        backgroundColor: 'rgba(123,47,255,0.5)',
        borderColor: '#7b2fff',
        borderWidth: 1, borderRadius: 4,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#8892b0' } } },
      scales: {
        x: { ticks: { color: '#4a5568' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#4a5568' }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
      },
    },
  });
}

function buildSavingsChart(data) {
  const ctx = document.getElementById('chart-savings');
  if (!ctx) return;
  if (chartSavings) chartSavings.destroy();
  chartSavings = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.date),
      datasets: [{
        label: 'Cumulative D&D Savings ($)',
        data: data.map(d => d.savings),
        borderColor: '#00ff88',
        backgroundColor: 'rgba(0,255,136,0.08)',
        tension: 0.4, fill: true, pointRadius: 3,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#8892b0' } } },
      scales: {
        x: { ticks: { color: '#4a5568' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#4a5568', callback: v => '$' + v },
             grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
      },
    },
  });
}

// ── Init on load ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initAnalystMap();
  initCharts();
  // Refresh vessels and charts every 15 min
  setInterval(() => { loadVessels(); loadHeatmap(); }, 15 * 60 * 1000);
  setInterval(initCharts, 15 * 60 * 1000);
});
