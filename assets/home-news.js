(function () {
  'use strict';
  var box = document.getElementById('home-news-list');
  if (!box) return;
  var controller = new AbortController();
  var timeout = setTimeout(function () { controller.abort(); }, 10000);
  function label(className, value) {
    var span = document.createElement('span');
    span.className = className;
    span.textContent = value || '';
    return span;
  }
  fetch('https://eastsword.github.io/news-archive/feed.json', { signal: controller.signal })
    .then(function (response) {
      if (!response.ok) throw new Error('Feed unavailable');
      return response.json();
    }).then(function (data) {
      var items = (Array.isArray(data.items) ? data.items : []).filter(function (item) {
        return item && typeof item.url === 'string' && /^https?:\/\//i.test(item.url) && item.title;
      }).slice(0, 4);
      box.replaceChildren();
      if (!items.length) {
        box.appendChild(label('feed-status', '暂无资讯，稍后再来看看。'));
        return;
      }
      items.forEach(function (item) {
        var link = document.createElement('a');
        link.className = 'news-item';
        link.href = item.url;
        link.target = '_blank';
        link.rel = 'noopener';
        var meta = label('news-item-meta', '');
        meta.append(label('news-date', item.published_date), label('news-source', item.source));
        link.append(meta, label('news-title', item.title));
        if (item.title_zh) link.appendChild(label('news-title-zh', item.title_zh));
        box.appendChild(link);
      });
    }).catch(function () {
      box.replaceChildren(label('feed-status', '资讯暂时无法加载，请稍后重试或前往资讯归档。'));
    }).finally(function () { clearTimeout(timeout); });
})();
