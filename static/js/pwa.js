/* CargoBridge AI — PWA Service Worker registration */

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('CargoBridge SW registered:', reg.scope))
      .catch(err => console.warn('SW registration failed:', err));
  });
}

// Install prompt (show Add to Home Screen button if available)
let deferredPrompt;
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  deferredPrompt = e;
  const btn = document.getElementById('install-btn');
  if (btn) {
    btn.style.display = 'inline-flex';
    btn.addEventListener('click', () => {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(() => { deferredPrompt = null; btn.style.display = 'none'; });
    });
  }
});

window.addEventListener('appinstalled', () => {
  deferredPrompt = null;
  console.log('CargoBridge AI installed as PWA');
});
