(function () {
  'use strict';
  var stats = document.getElementById('site-stats');
  if (!stats || location.protocol !== 'https:' || location.hostname !== stats.dataset.host) return;
  var observer = new MutationObserver(function () {
    var values = ['site_pv', 'site_uv'].map(function (key) {
      return document.getElementById('busuanzi_value_' + key).textContent.trim();
    });
    if (values.every(function (value) { return /^\d+$/.test(value); })) {
      stats.hidden = false;
      observer.disconnect();
      clearTimeout(timeout);
    }
  });
  observer.observe(stats, { childList: true, subtree: true, characterData: true });
  var timeout = setTimeout(function () { observer.disconnect(); }, 10000);
  var script = document.createElement('script');
  script.async = true;
  script.src = 'https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js';
  script.onerror = function () { observer.disconnect(); clearTimeout(timeout); };
  document.head.appendChild(script);
})();
