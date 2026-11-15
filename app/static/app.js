document.querySelectorAll('.countdown').forEach(function (el) {
  var secs = parseInt(el.dataset.secs, 10);
  (function tick() {
    if (secs <= 0) { el.textContent = 'expired'; setTimeout(function () { location.reload(); }, 1500); return; }
    el.textContent = Math.floor(secs / 60) + ':' + String(secs % 60).padStart(2, '0');
    secs -= 1; setTimeout(tick, 1000);
  })();
});
