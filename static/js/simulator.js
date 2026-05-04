/* CargoBridge AI — Resilience Simulator JS */

let simChart = null;

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('simulator-form');
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Running…';

    const payload = {
      rainfall_mm:       parseFloat(document.getElementById('rainfall_mm').value) || 0,
      wind_speed_kmh:    parseFloat(document.getElementById('wind_speed_kmh').value) || 0,
      vessel_queue_count:parseInt(document.getElementById('vessel_queue_count').value) || 0,
      traffic_density:   parseFloat(document.getElementById('traffic_density').value) || 0,
      time_of_day:       document.getElementById('time_of_day').value || 'morning',
    };

    try {
      const resp = await fetch('/api/simulate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(payload),
      });
      const result = await resp.json();
      renderSimResults(result);
    } catch (err) {
      console.error('Simulation error:', err);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Run Simulation';
    }
  });
});

function renderSimResults(data) {
  const panel = document.getElementById('sim-results');
  if (!panel) return;
  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Congestion level
  const congLabel = document.getElementById('sim-congestion');
  if (congLabel) {
    const cls = { Low: 'badge-congestion-low', Medium: 'badge-congestion-medium', High: 'badge-congestion-high' };
    congLabel.className = `congestion-badge ${cls[data.gate_congestion] || ''}`;
    congLabel.innerHTML = `<span class="congestion-dot dot-${data.gate_congestion?.toLowerCase()}"></span>${data.gate_congestion}`;
  }

  // Index
  const idx = document.getElementById('sim-index');
  if (idx) idx.textContent = data.congestion_index?.toFixed(1) + '/100';

  // D&D risk
  const ddUsd = document.getElementById('sim-dd-usd');
  const ddAed = document.getElementById('sim-dd-aed');
  if (ddUsd) ddUsd.textContent = '$' + data.dd_risk_usd?.toFixed(2);
  if (ddAed) ddAed.textContent = 'AED ' + data.dd_risk_aed?.toFixed(2);

  // Dispatch windows
  const windows = document.getElementById('sim-windows');
  if (windows && data.dispatch_windows) {
    windows.innerHTML = data.dispatch_windows.map(w => `
      <div class="sim-window">
        <span class="font-mono text-accent-green">${w.time} <small style="color:#4a5568">${w.date}</small></span>
        <span class="text-accent-blue">${w.suitability}% suitable</span>
      </div>
    `).join('');
  }

  // Sectoral impact chart
  if (data.sectoral_impact) {
    buildSectorChart(data.sectoral_impact);
  }
}

function buildSectorChart(sectoral) {
  const ctx = document.getElementById('sim-sector-chart');
  if (!ctx) return;
  if (simChart) simChart.destroy();

  const labels = Object.keys(sectoral);
  const values = Object.values(sectoral);

  simChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: 'Impact Score',
        data: values,
        borderColor: '#00d4ff',
        backgroundColor: 'rgba(0,212,255,0.12)',
        pointBackgroundColor: '#00d4ff',
        pointRadius: 5,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#8892b0' } } },
      scales: {
        r: {
          ticks: { color: '#4a5568', backdropColor: 'transparent', stepSize: 20 },
          grid: { color: 'rgba(255,255,255,0.06)' },
          pointLabels: { color: '#8892b0', font: { size: 12 } },
          min: 0, max: 100,
        },
      },
    },
  });
}

function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || '';
}
