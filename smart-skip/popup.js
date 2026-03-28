// Load settings
chrome.storage.sync.get(['autoSkip', 'notifications', 'timeSaved'], (result) => {
  document.getElementById('autoSkip').checked = result.autoSkip !== false;
  document.getElementById('notifications').checked = result.notifications !== false;
  document.getElementById('timeSaved').textContent = Math.round(result.timeSaved || 0);
});

// Save auto-skip setting
document.getElementById('autoSkip').addEventListener('change', (e) => {
  chrome.storage.sync.set({ autoSkip: e.target.checked });
});

// Save notifications setting
document.getElementById('notifications').addEventListener('change', (e) => {
  chrome.storage.sync.set({ notifications: e.target.checked });
});