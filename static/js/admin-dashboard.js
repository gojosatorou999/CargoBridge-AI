/* ═══════════════════════════════════════════════════════════════════════════
   CargoBridge AI — Admin Dashboard
   AISStream live WebSocket map + VesselFinder fallback + analytics charts
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── Helpers ────────────────────────────────────────────────────────────── */
function jsonTag(id) {
  try { return JSON.parse(document.getElementById(id).textContent); }
  catch (_) { return []; }
}
function el(id) { return document.getElementById(id); }
function setText(id, v) { const e = el(id); if (e) e.textContent = v; }

/* ── Tab switching ──────────────────────────────────────────────────────── */
function switchTab(tab, btn) {
  document.querySelectorAll('.adm-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.adm-map-pane').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  el('pane-' + tab).classList.add('active');

  el('ais-toolbar').style.display = tab === 'ais' ? 'flex' : 'none';

  if (tab === 'ais') {
    if (!aisMapReady) initAisMap();
    else if (aisMap) setTimeout(() => aisMap.invalidateSize(), 60);
  } else if (tab === 'vf') {
    initVesselFinder();
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   AIS STREAM MAP
   ═══════════════════════════════════════════════════════════════════════════ */
let aisMap, aisMapReady = false, aisWs = null;
let heatLayer;
let showHeat = true;

const VESSEL_COLORS = {
  cargo:     '#22c55e',
  tanker:    '#f97316',
  passenger: '#a855f7',
  tug:       '#22d3ee',
  fishing:   '#eab308',
  highspeed: '#ef4444',
  sailing:   '#f1f5f9',
  other:     '#94a3b8',
};

const hiddenTypes = new Set();
const markers     = {};          /* mmsi → { marker, cat } */
const metaCache   = {};          /* mmsi → { name, type, dest } */
const counts = { total:0, cargo:0, tanker:0, passenger:0 };

function shipCat(code) {
  const t = Number(code);
  if (t >= 70 && t <= 79) return 'cargo';
  if (t >= 80 && t <= 89) return 'tanker';
  if (t >= 60 && t <= 69) return 'passenger';
  if (t === 30)            return 'fishing';
  if ([31,32,52].includes(t)) return 'tug';
  if (t >= 40 && t <= 49) return 'highspeed';
  if (t === 36 || t === 37) return 'sailing';
  return 'other';
}

/* ── Init Leaflet ────────────────────────────────────────────────────────── */
function initAisMap() {
  if (aisMapReady) return;
  const div = el('ais-live-map');
  if (!div || typeof L === 'undefined') return;

  aisMap = L.map(div, { zoomControl: true, preferCanvas: true }).setView([20, 20], 2);

  /* Dark tile layer */
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CartoDB',
    maxZoom: 19,
  }).addTo(aisMap);

  heatLayer = L.layerGroup().addTo(aisMap);
  loadHeatmap();

  aisMapReady = true;
  startAisStream();
}

/* ── Heatmap ─────────────────────────────────────────────────────────────── */
function loadHeatmap() {
  if (!aisMap) return;
  heatLayer.clearLayers();

  const pts = jsonTag('db-reports-data')
    .filter(r => r.lat && r.lon && r.status === 'approved')
    .map(r => [r.lat, r.lon, 0.8]);

  fetch('/api/reports?status=approved')
    .then(r => r.json())
    .then(d => {
      (d.reports || []).forEach(r => { if (r.lat && r.lon) pts.push([r.lat, r.lon, 0.8]); });
      renderHeat(pts);
    })
    .catch(() => renderHeat(pts));
}
function renderHeat(pts) {
  if (typeof L.heatLayer !== 'undefined' && pts.length && showHeat) {
    L.heatLayer(pts, {
      radius: 35, blur: 25, maxZoom: 13,
      gradient: { 0.25: '#3b82f6', 0.6: '#8b5cf6', 1.0: '#ef4444' },
    }).addTo(heatLayer);
  }
}

/* ── Layer toggles ───────────────────────────────────────────────────────── */
function toggleType(cat, btn) {
  btn.classList.toggle('active');
  if (hiddenTypes.has(cat)) {
    hiddenTypes.delete(cat);
    Object.values(markers).forEach(v => { if (v.cat === cat) aisMap.addLayer(v.marker); });
  } else {
    hiddenTypes.add(cat);
    Object.values(markers).forEach(v => { if (v.cat === cat) aisMap.removeLayer(v.marker); });
  }
}
function toggleHeatmap(btn) {
  btn.classList.toggle('active');
  showHeat = btn.classList.contains('active');
  if (showHeat) loadHeatmap();
  else heatLayer.clearLayers();
}

/* ── AISStream WebSocket ─────────────────────────────────────────────────── */
function startAisStream() {
  fetch('/api/aisstream/key')
    .then(r => r.json())
    .then(d => {
      if (!d.available || !d.key) {
        setWsPill('nokey', 'No API key');
        el('aisstream-banner').style.display = 'block';
        plotDbVessels();
        return;
      }
      openWs(d.key);
    })
    .catch(() => { setWsPill('error', 'Key fetch failed'); plotDbVessels(); });
}

function openWs(key) {
  if (aisWs) { try { aisWs.close(); } catch (_) {} }
  setWsPill('connecting', 'Connecting…');

  aisWs = new WebSocket('wss://stream.aisstream.io/v0/stream');

  aisWs.onopen = () => {
    setWsPill('connected', 'Live');
    aisWs.send(JSON.stringify({
      APIKey: key,
      BoundingBoxes: [[[-90, -180], [90, 180]]],
      FilterMessageTypes: ['PositionReport'],
    }));
  };

  aisWs.onmessage = e => {
    try { onAisMsg(JSON.parse(e.data)); } catch (_) {}
  };

  aisWs.onerror = () => setWsPill('error', 'WS error');

  aisWs.onclose = ev => {
    setWsPill('error', `Closed (${ev.code}) — retry 15s`);
    setTimeout(() => { if (aisMapReady) openWs(key); }, 15000);
  };
}

function onAisMsg(msg) {
  if (!msg || !msg.Message) return;
  const meta = msg.MetaData || {};
  const mmsi = String(meta.MMSI || '');
  if (!mmsi) return;

  /* Cache static data */
  if (msg.MessageType === 'ShipStaticData') {
    const sd = msg.Message.ShipStaticData || {};
    metaCache[mmsi] = {
      name: (sd.Name || meta.ShipName || '').trim(),
      type: sd.Type || 0,
      dest: (sd.Destination || '').trim(),
    };
    return;
  }

  const pos = msg.Message.PositionReport || msg.Message.StandardClassBPositionReport;
  if (!pos) return;

  const lat = pos.Latitude ?? pos.Lat;
  const lon = pos.Longitude ?? pos.Lon;
  if (lat == null || lon == null) return;
  if (lat === 0 && lon === 0) return;
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return;

  const cached  = metaCache[mmsi] || {};
  const hdg     = (pos.TrueHeading < 511 ? pos.TrueHeading : null) ?? pos.Cog ?? 0;
  const speed   = (pos.Sog || 0).toFixed(1);
  const name    = cached.name || (meta.ShipName || '').trim() || ('MMSI ' + mmsi);
  const cat     = shipCat(cached.type || meta.ShipType || 0);
  const color   = VESSEL_COLORS[cat] || VESSEL_COLORS.other;
  const dest    = cached.dest || (meta.Destination || '').trim() || '—';

  setText('last-msg', new Date().toLocaleTimeString());

  if (hiddenTypes.has(cat)) return;

  if (markers[mmsi]) {
    markers[mmsi].marker.setLatLng([lat, lon]);
    const iconEl = markers[mmsi].marker.getElement();
    if (iconEl) {
      const a = iconEl.querySelector('.va');
      if (a) a.style.transform = `rotate(${hdg}deg)`;
    }
  } else {
    const icon = makeIcon(color, hdg);
    const marker = L.marker([lat, lon], { icon })
      .addTo(aisMap)
      .bindPopup(makePopup(name, mmsi, cat, speed, lat, lon, dest, hdg), { maxWidth: 240 });

    markers[mmsi] = { marker, cat };

    counts.total++;
    if (cat === 'cargo')          counts.cargo++;
    else if (cat === 'tanker')    counts.tanker++;
    else if (cat === 'passenger') counts.passenger++;

    updateCounts();
  }
}

function makeIcon(color, hdg) {
  return L.divIcon({
    className: '',
    html: `<div class="va" style="
      width:0;height:0;
      border-left:5px solid transparent;
      border-right:5px solid transparent;
      border-bottom:14px solid ${color};
      transform:rotate(${hdg}deg);
      filter:drop-shadow(0 0 3px ${color}66);
      cursor:pointer;"></div>`,
    iconSize: [10, 14], iconAnchor: [5, 7],
  });
}

function makePopup(name, mmsi, cat, speed, lat, lon, dest, hdg) {
  const c = VESSEL_COLORS[cat] || '#94a3b8';
  return `<div style="background:#0f172a;color:#e2e8f0;padding:11px 13px;
    border-radius:10px;min-width:200px;border:1px solid ${c}44;font-size:0.82rem;">
    <b style="color:${c};font-size:0.9rem;">${name}</b><br>
    <span style="color:#334155;font-size:0.7rem;">MMSI: ${mmsi}</span>
    <hr style="border-color:rgba(255,255,255,0.07);margin:6px 0;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:0.75rem;">
      <div><span style="color:#334155;">Type</span><br><b style="color:${c};">${cat}</b></div>
      <div><span style="color:#334155;">Speed</span><br>${speed} kn</div>
      <div><span style="color:#334155;">Dest</span><br>${dest}</div>
      <div><span style="color:#334155;">Heading</span><br>${Math.round(hdg)}°</div>
      <div><span style="color:#334155;">Lat</span><br>${lat.toFixed(4)}°</div>
      <div><span style="color:#334155;">Lon</span><br>${lon.toFixed(4)}°</div>
    </div>
  </div>`;
}

/* Plot local DB vessels when no AISStream key */
function plotDbVessels() {
  if (!aisMap) return;
  jsonTag('db-vessels-data').forEach(v => {
    if (v.lat == null || v.lon == null) return;
    const icon = makeIcon('#60a5fa', 0);
    const eta  = v.eta ? new Date(v.eta).toLocaleString() : '—';
    L.marker([v.lat, v.lon], { icon })
     .addTo(aisMap)
     .bindPopup(`<div style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:8px;
       border:1px solid #60a5fa44;font-size:0.8rem;">
       <b style="color:#60a5fa;">${v.name || 'Unknown'}</b><br>
       <span style="color:#334155;font-size:0.7rem;">MMSI: ${v.mmsi||'—'}</span><br>
       Speed: ${Number(v.speed).toFixed(1)} kn<br>
       Dest: ${(v.dest||'—').replace(/_/g,' ')}<br>ETA: ${eta}
     </div>`);
    counts.total++;
    updateCounts();
  });
}

function updateCounts() {
  setText('cnt-total',     counts.total);
  setText('cnt-cargo',     counts.cargo);
  setText('cnt-tanker',    counts.tanker);
  setText('cnt-passenger', counts.passenger);
  setText('kpi-live',      counts.total);
}

function setWsPill(state, text) {
  const p = el('ws-pill');
  if (!p) return;
  p.className = 'adm-ws-pill ' + state;
  p.innerHTML = `<span class="ws-dot"></span> ${text}`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   VESSEL FINDER (Tab 2)
   ═══════════════════════════════════════════════════════════════════════════ */
let vfLoaded = false;
function initVesselFinder() {
  if (vfLoaded) return;
  vfLoaded = true;
  const c = el('vf-map-container');
  if (!c) return;

  window.vf_cfg = { width: '100%', height: '560px', latitude: 20, longitude: 0, zoom: 2, names: true };
  const s = document.createElement('script');
  s.src = 'https://www.vesselfinder.com/aismap.js';
  s.async = true;
  s.onerror = () => showVfFallback(c);
  c.appendChild(s);
}

function showVfFallback(c) {
  if (typeof L === 'undefined') return;
  const d = document.createElement('div');
  d.style.cssText = 'width:100%;height:560px;border-radius:12px;';
  c.innerHTML = '';
  c.appendChild(d);

  const m = L.map(d).setView([20, 0], 2);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap', maxZoom: 18,
  }).addTo(m);
  L.tileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenSeaMap', maxZoom: 18, opacity: 0.8,
  }).addTo(m);

  jsonTag('db-vessels-data').forEach(v => {
    if (v.lat == null || v.lon == null) return;
    L.circleMarker([v.lat, v.lon], {
      radius: 5, color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.7, weight: 1.5,
    }).addTo(m).bindPopup(`<b>${v.name||'Unknown'}</b><br>${Number(v.speed).toFixed(1)} kn`);
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   VESSEL TABLE FILTER
   ═══════════════════════════════════════════════════════════════════════════ */
function filterVessels() {
  const s = (el('v-search')?.value || '').toLowerCase();
  const d = (el('v-dest')?.value   || '').toLowerCase();
  document.querySelectorAll('#vessel-table .vrow').forEach(r => {
    const ok = (!s || r.dataset.name.includes(s) || r.dataset.mmsi.includes(s))
            && (!d || r.dataset.dest.includes(d));
    r.style.display = ok ? '' : 'none';
  });
}

/* ── Speed bars ─────────────────────────────────────────────────────────── */
function initSpeedBars() {
  document.querySelectorAll('.adm-spd-bar[data-spd]').forEach(b => {
    b.style.width = Math.min(Math.round(parseFloat(b.dataset.spd) / 25 * 55), 55) + 'px';
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   ANALYTICS CHARTS
   ═══════════════════════════════════════════════════════════════════════════ */
const CC = ['#3b82f6','#8b5cf6','#22c55e','#f97316','#facc15','#ef4444','#ec4899','#22d3ee'];
let cType, cTimeline, cSavings;

function initCharts() {
  fetch('/api/analytics/charts')
    .then(r => r.json())
    .then(d => {
      buildType(d.type_distribution || []);
      buildTimeline(d.timeline || []);
      buildSavings(d.savings || []);
    }).catch(() => {});
}

const gridOpts = {
  x: { ticks:{color:'#334155'}, grid:{color:'rgba(255,255,255,0.04)'} },
  y: { ticks:{color:'#334155'}, grid:{color:'rgba(255,255,255,0.04)'}, beginAtZero:true },
};

function buildType(data) {
  const ctx = el('chart-type'); if (!ctx) return;
  if (cType) cType.destroy();
  cType = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.type.replace(/_/g,' ')),
      datasets: [{ data: data.map(d => d.count), backgroundColor: CC,
        borderColor:'rgba(255,255,255,0.05)', borderWidth:2 }],
    },
    options: { responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ color:'#64748b', font:{size:11} } } } },
  });
}

function buildTimeline(data) {
  const ctx = el('chart-timeline'); if (!ctx) return;
  if (cTimeline) cTimeline.destroy();
  cTimeline = new Chart(ctx, {
    type: 'line',
    data: { labels: data.map(d=>d.date), datasets:[{
      label:'Reports', data: data.map(d=>d.count),
      borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,0.1)',
      tension:0.4, fill:true, pointRadius:3,
    }] },
    options: { responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ color:'#64748b' } } }, scales: gridOpts },
  });
}

function buildSavings(data) {
  const ctx = el('chart-savings'); if (!ctx) return;
  if (cSavings) cSavings.destroy();
  cSavings = new Chart(ctx, {
    type: 'line',
    data: { labels: data.map(d=>d.date), datasets:[{
      label:'Savings ($)', data: data.map(d=>d.savings),
      borderColor:'#22c55e', backgroundColor:'rgba(34,197,94,0.08)',
      tension:0.4, fill:true, pointRadius:3,
    }] },
    options: { responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ color:'#64748b' } } },
      scales: { ...gridOpts, y:{ ticks:{color:'#334155', callback:v=>'$'+v},
        grid:{color:'rgba(255,255,255,0.04)'}, beginAtZero:true } } },
  });
}

/* ── Boot ───────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initSpeedBars();
  initCharts();
  initAisMap();    /* AISStream tab is active — start immediately */
  setInterval(initCharts, 15 * 60 * 1000);
});
