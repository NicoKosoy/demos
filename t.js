/* Registro de visitas de demos.resolviendokos.com
   Uso en cada demo: <script defer src="https://visitas.resolviendokos.com/v/t.js" data-negocio="Nombre del negocio"></script>
   ?yo=1 marca este navegador como tuyo y no cuenta más sus visitas (?yo=0 lo desmarca). */
(function () {
  try {
    var URL_C = 'https://visitas.resolviendokos.com/v/c.php';
    var q = location.search, ls = null;
    try { ls = window.localStorage; } catch (e) {}
    if (/[?&]yo=1(&|$)/.test(q)) { try { ls.setItem('rk_yo', '1'); } catch (e) {} return; }
    if (/[?&]yo=0(&|$)/.test(q)) { try { ls.removeItem('rk_yo'); } catch (e) {} }
    try { if (ls && ls.getItem('rk_yo') === '1') return; } catch (e) {}
    if (navigator.webdriver) return;

    var prospecto = location.pathname.split('/').filter(Boolean)[0];
    if (!prospecto) return;
    var yo = document.currentScript;
    var negocio = (yo && yo.getAttribute('data-negocio')) || '';
    if (!negocio) {
      var m = (document.body ? document.body.textContent : '').match(/preparado para\s+(.{2,80}?)(?:\s+por\s+Resolviendo|\.\s|\.$|\n|$)/i);
      negocio = (m && m[1]) || document.title || '';
    }

    function enviar(d) {
      var s = JSON.stringify(d);
      if (navigator.sendBeacon && navigator.sendBeacon(URL_C, new Blob([s], { type: 'text/plain' }))) return;
      try { fetch(URL_C, { method: 'POST', body: s, keepalive: true, mode: 'no-cors' }); } catch (e) {}
    }

    var id = Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
    var acumulado = 0, desde = document.visibilityState === 'visible' ? Date.now() : 0, ultimo = -1;
    function segundos() { return Math.round((acumulado + (desde ? Date.now() - desde : 0)) / 1000); }
    function ping() { var s = segundos(); if (s !== ultimo) { ultimo = s; enviar({ e: 'ping', v: id, s: s }); } }

    enviar({
      e: 'inicio', v: id, p: prospecto, n: negocio.trim().slice(0, 120),
      w: screen.width + 'x' + screen.height,
      t: ('ontouchstart' in window || navigator.maxTouchPoints > 1) ? 1 : 0,
      r: (document.referrer || '').slice(0, 200)
    });
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') { if (desde) { acumulado += Date.now() - desde; desde = 0; } ping(); }
      else { desde = Date.now(); }
    });
    window.addEventListener('pagehide', ping);
    setInterval(function () { if (document.visibilityState === 'visible') ping(); }, 15000);
  } catch (e) {}
})();
