(function () {
  var csrf = document.querySelector('meta[name=csrf-token]').content;
  var box = document.getElementById('result');
  var last = { code: null, at: 0 };

  async function check(code) {
    var eventId = document.getElementById('event').value;
    if (!eventId) { show(false, 'No event selected'); return; }
    // the camera sees the same QR many times per second: ignore repeats for 4 s
    if (code === last.code && Date.now() - last.at < 4000) return;
    last = { code: code, at: Date.now() };
    try {
      var r = await fetch('/staff/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify({ code: code, event_id: parseInt(eventId, 10) })
      });
      var j = await r.json();
      if (j.detail) show(false, j.detail); else show(j.ok, j.ok ? 'ADMIT - ' + j.reason : 'REJECT - ' + j.reason);
    } catch (e) { show(false, 'Network error'); }
  }
  function show(ok, text) {
    box.className = 'alert alert-' + (ok ? 'success' : 'danger');
    box.textContent = text;
    if (navigator.vibrate) navigator.vibrate(ok ? 80 : [80, 60, 80]);
  }

  document.getElementById('manualBtn').onclick = function () {
    var v = document.getElementById('manual').value.trim();
    if (v) { last = { code: null, at: 0 }; check(v); }
  };
})();
