/* CargoBridge AI — Core JS: notifications, maps, polling, UI */

// ── Notification bell polling (every 5s) ─────────────────────────────────────
function startNotificationPolling() {
  const badge = document.getElementById('notif-badge');
  if (!badge) return;
  setInterval(() => {
    fetch('/api/notifications/unread-count')
      .then(r => r.json())
      .then(data => {
        const count = data.count || 0;
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
      })
      .catch(() => {});
  }, 5000);
}

// ── Flash auto-dismiss ───────────────────────────────────────────────────────
function initFlashMessages() {
  document.querySelectorAll('.flash-msg').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });
}

// ── Mark notification read ───────────────────────────────────────────────────
function markRead(id) {
  fetch(`/api/notification/${id}/read`, { method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() } })
    .then(() => document.getElementById(`notif-${id}`)?.classList.add('read'))
    .catch(() => {});
}

// ── Clear all notifications ──────────────────────────────────────────────────
function clearAllNotifications() {
  fetch('/api/notifications/clear', { method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() } })
    .then(() => location.reload())
    .catch(() => {});
}

// ── Accept slot ──────────────────────────────────────────────────────────────
function acceptSlot(slotId) {
  fetch(`/api/slot/${slotId}/accept`, { method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() } })
    .then(r => r.json())
    .then(d => {
      if (d.success) {
        showToast('Slot accepted!', 'success');
        document.getElementById(`slot-card-${slotId}`)?.classList.add('accepted');
        setTimeout(() => location.reload(), 1200);
      }
    })
    .catch(() => {});
}

// ── Request alternate slot ───────────────────────────────────────────────────
function requestAlternate(slotId) {
  fetch(`/api/slot/${slotId}/request-alternate`, { method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() } })
    .then(r => r.json())
    .then(d => {
      if (d.success) {
        showToast('Alternate slot generated. Check your updates.', 'info');
        setTimeout(() => location.reload(), 1500);
      }
    })
    .catch(() => {});
}

// ── Like post ────────────────────────────────────────────────────────────────
function likePost(postId) {
  fetch(`/post/${postId}/like`, { method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() } })
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById(`likes-${postId}`);
      if (el) el.textContent = d.likes;
      document.querySelector(`.like-btn[data-post="${postId}"]`)?.classList.toggle('liked');
    })
    .catch(() => {});
}

// ── Report form: GPS auto-fill ───────────────────────────────────────────────
function initGPSAutoFill() {
  const btn = document.getElementById('gps-btn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (!navigator.geolocation) return;
    btn.disabled = true;
    btn.textContent = 'Getting location…';
    navigator.geolocation.getCurrentPosition(pos => {
      document.getElementById('latitude').value  = pos.coords.latitude.toFixed(6);
      document.getElementById('longitude').value = pos.coords.longitude.toFixed(6);
      const loc = document.getElementById('location_name');
      if (loc && !loc.value) loc.value = `${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`;
      btn.textContent = 'Location set ✓';
      initReportMap(pos.coords.latitude, pos.coords.longitude);
    }, () => {
      btn.textContent = 'Location unavailable';
      btn.disabled = false;
    });
  });
}

// ── Report form map (Leaflet pin-drop) ───────────────────────────────────────
function initReportMap(lat, lon) {
  const el = document.getElementById('report-map');
  if (!el || typeof L === 'undefined') return;
  lat = lat || 18.95;
  lon = lon || 72.84;
  if (window._reportMap) { window._reportMap.remove(); }
  const map = L.map('report-map', { zoomControl: true }).setView([lat, lon], 13);
  window._reportMap = map;
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '©OpenStreetMap ©CartoDB', maxZoom: 19,
  }).addTo(map);
  const marker = L.marker([lat, lon], { draggable: true }).addTo(map);
  const updateCoords = (latlng) => {
    document.getElementById('latitude').value  = latlng.lat.toFixed(6);
    document.getElementById('longitude').value = latlng.lng.toFixed(6);
  };
  marker.on('dragend', e => updateCoords(e.target.getLatLng()));
  map.on('click', e => { marker.setLatLng(e.latlng); updateCoords(e.latlng); });
}

// ── Camera toggle (front/back) ───────────────────────────────────────────────
function initCameraToggle() {
  const toggle = document.getElementById('cam-toggle');
  const fileInput = document.getElementById('image');
  if (!toggle || !fileInput) return;
  let useFront = false;
  toggle.addEventListener('click', () => {
    useFront = !useFront;
    fileInput.setAttribute('capture', useFront ? 'user' : 'environment');
    toggle.textContent = useFront ? '📷 Front Cam' : '📷 Back Cam';
  });
}

// ── Toast helper ─────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const container = document.querySelector('.flash-container') || (() => {
    const c = document.createElement('div');
    c.className = 'flash-container';
    document.body.appendChild(c);
    return c;
  })();
  const el = document.createElement('div');
  el.className = `flash-msg flash-${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 400); }, 3500);
}

// ── CSRF token ────────────────────────────────────────────────────────────────
function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

// ── Offline detection ─────────────────────────────────────────────────────────
function initOfflineDetection() {
  const banner = document.getElementById('offline-banner');
  if (!banner) return;
  window.addEventListener('offline', () => { banner.style.display = 'block'; });
  window.addEventListener('online',  () => { banner.style.display = 'none'; });
}

// ── Init on DOM ready ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  startNotificationPolling();
  initFlashMessages();
  initGPSAutoFill();
  initCameraToggle();
  initOfflineDetection();
  if (document.getElementById('report-map')) initReportMap();
});
