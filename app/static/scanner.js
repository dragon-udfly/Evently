(function () {
  var csrf = document.querySelector('meta[name=csrf-token]').content;
  var box = document.getElementById('result');
  var last = { code: null, at: 0 };

  function show(ok, text) {
    box.className = 'alert alert-' + (ok ? 'success' : 'danger');
    box.textContent = text;
    if (navigator.vibrate) navigator.vibrate(ok ? 80 : [80, 60, 80]);
  }
})();
