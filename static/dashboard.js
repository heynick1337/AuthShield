document.getElementById('logoutBtn').addEventListener('click', () => {
  window.location.href = "/logout";
});

// ── countdown timer ──
let remaining = 600; // 10 minutes in seconds
const display = document.getElementById('timeoutDisplay');

function formatTime(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
}

function resetTimer() {
  remaining = 600;
  if (display) display.textContent = formatTime(remaining);
}

const tick = setInterval(() => {
  remaining--;
  if (display) display.textContent = formatTime(remaining);
  if (remaining <= 0) {
    clearInterval(tick);
    window.location.href = "/login";
  }
}, 1000);

document.addEventListener('mousemove', resetTimer);
document.addEventListener('keypress', resetTimer);
document.addEventListener('click', resetTimer);
