---
layout: default
title: 安全资讯
permalink: /news/
---
<section id="news">
  <div class="wrap">
    <div class="section-head">
      <div class="num">03 / INTEL</div>
      <h2>安全资讯</h2>
      <p class="desc">直连内网情报聚合服务，覆盖 CISA、Mandiant、MSRC、FreeBuf 等全球安全源与 AI 安全源，每日 10:00 自动同步，全量归档无上限积累。数据存放于独立归档仓库，本页按需动态加载：下滑自动翻越更早月份，输入关键词自动全量检索历史。</p>
    </div>

    <div class="news-meta" id="news-meta"><span class="badge cat-sec">情报归档加载中…</span></div>

    <div class="filter-bar filter-bar-col">
      <div class="search-box">
        <span class="icon">⌕</span>
        <input id="news-search" type="text" placeholder="搜索标题 / 来源 / 摘要（自动全量检索归档）…" autocomplete="off">
      </div>

      <div class="chips-rows" id="news-chips"></div>
      <div class="filter-count" id="news-count"></div>
    </div>

    <div class="news-list" id="news-list"></div>
    <div class="news-more" id="news-more" hidden><span class="spin"></span><span id="news-more-text">下滑加载更早的资讯…</span></div>
    <div class="empty-result" id="news-empty" hidden>
      <div class="glyph">空</div>
      没有匹配的资讯，换个关键词或放宽标签试试
    </div>
    <noscript>
      <div class="placeholder-box">
        <div class="glyph">讯</div>
        资讯列表由前端动态加载，请启用 JavaScript 后查看
      </div>
    </noscript>
  </div>
</section>

<script>
(function () {
  var BASE = 'https://eastsword.github.io/news-archive';
  var PER_BATCH = 40;
  var CONCURRENCY = 3;

  var list = document.getElementById('news-list');
  if (!list) return;
  var meta = document.getElementById('news-meta');
  var search = document.getElementById('news-search');
  var chipsBox = document.getElementById('news-chips');
  var count = document.getElementById('news-count');
  var more = document.getElementById('news-more');
  var moreText = document.getElementById('news-more-text');
  var empty = document.getElementById('news-empty');

  var idx = null;
  var monthsQueue = [];    // 未加载月份（倒序，队首最新）
  var loadedMonths = [];   // 已加载月份（倒序）
  var items = [];          // 已加载条目（全局时间倒序）
  var state = { q: '', cat: new Set(), prio: new Set(), src: new Set(), limit: PER_BATCH };
  var fullScan = { done: false, running: false, msg: '' };
  var loading = false;
  var renderTimer = null;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : '#'; }
  function norm(s) { return (s || '').toLowerCase(); }
  function tsOf(it) { var t = Date.parse(it.published_at || ''); return isNaN(t) ? 0 : t; }

  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ' ' + r.status);
      return r.json();
    });
  }
  function fetchRetry(url) {
    return fetchJSON(url).catch(function () {
      return new Promise(function (res) { setTimeout(res, 800); }).then(function () { return fetchJSON(url); });
    });
  }

  function merge(month, arr) {
    if (!arr || !arr.length) return;
    arr.forEach(function (it) { it._t = tsOf(it); });
    items = items.concat(arr).sort(function (a, b) { return b._t - a._t; });
    loadedMonths.push(month);
    loadedMonths.sort().reverse();
  }

  function loadMonth(m) {
    return fetchRetry(BASE + '/months/' + m + '.json').then(function (d) { merge(m, d.items || []); });
  }

  // 从队列取 n 个月（Infinity = 全量），并发加载，单月失败不中断
  function loadMonths(n) {
    var take = monthsQueue.splice(0, n);
    var i = 0;
    function worker() {
      if (i >= take.length) return Promise.resolve();
      var m = take[i++];
      return loadMonth(m).catch(function () {}).then(function () {
        afterMonthLoaded(m);
        return worker();
      });
    }
    var ws = [];
    for (var k = 0; k < CONCURRENCY && k < take.length; k++) ws.push(worker());
    return Promise.all(ws).then(function () {
      if (n === Infinity || monthsQueue.length === 0) { fullScan.done = true; fullScan.running = false; }
    });
  }

  function afterMonthLoaded(m) {
    if (fullScan.running) {
      fullScan.msg = monthsQueue.length
        ? '全量检索中：已扫至 ' + m + '，还剩 ' + monthsQueue.length + ' 个月…'
        : '已完成全量检索';
    }
    scheduleRender();
  }

  function scheduleRender() {
    if (renderTimer) return;
    renderTimer = setTimeout(function () { renderTimer = null; render(); }, 250);
  }

  function startFullScan() {
    if (fullScan.done || fullScan.running) return;
    if (!monthsQueue.length) { fullScan.done = true; return; }
    fullScan.running = true;
    fullScan.msg = '全量检索中：还剩 ' + monthsQueue.length + ' 个月…';
    loadMonths(Infinity).then(function () { fullScan.msg = ''; render(); });
  }

  function match(it) {
    if (state.cat.size && !state.cat.has(it.category)) return false;
    if (state.prio.size && !state.prio.has(it.priority)) return false;
    if (state.src.size && !state.src.has(it.source)) return false;
    if (state.q) {
      var hay = norm([it.title, it.source, it.category, it.digest].join(' '));
      if (hay.indexOf(norm(state.q)) === -1) return false;
    }
    return true;
  }

  function prioLabel(p) {
    if (p === 'P0') return 'P0 紧急';
    if (p === 'P2') return 'P2 常规';
    return p;
  }

  function itemHTML(n) {
    return '<a class="news-item" href="' + esc(safeUrl(n.url)) + '" target="_blank" rel="noopener" title="' + esc(n.digest || '') + '">' +
      '<span class="news-date">' + esc(n.published_date) + '</span>' +
      '<span class="badge prio-' + esc((n.priority || '').toLowerCase()) + '">' + esc(prioLabel(n.priority)) + '</span>' +
      '<span class="badge ' + (n.category === 'AI安全' ? 'cat-ai' : 'cat-sec') + '">' + esc(n.category) + '</span>' +
      '<span class="news-title">' + esc(n.title) + '</span>' +
      '<span class="news-source">' + esc(n.source) + '</span></a>';
  }

  function render() {
    var rows = items.filter(match);
    var visible = rows.slice(0, state.limit);
    var html = '';
    for (var i = 0; i < visible.length; i++) html += itemHTML(visible[i]);
    list.innerHTML = html;
    empty.hidden = rows.length !== 0;

    var range = loadedMonths.length
      ? ' ｜ 已加载 ' + loadedMonths[loadedMonths.length - 1] + ' ~ ' + loadedMonths[0] + ' 共 ' + items.length + ' 条'
      : '';
    var parts = [];
    if (state.cat.size) parts.push('分类 ' + Array.from(state.cat).join('、'));
    if (state.prio.size) parts.push('级别 ' + Array.from(state.prio).join('、'));
    if (state.src.size) parts.push('来源 ' + Array.from(state.src).join('、'));
    count.textContent = '命中 ' + rows.length + ' 条' + (parts.length ? ' ｜ ' + parts.join(' · ') : '') + range;

    if (fullScan.running) {
      more.hidden = false;
      moreText.textContent = fullScan.msg;
      return;
    }
    if (rows.length > state.limit) {
      more.hidden = false;
      moreText.textContent = '继续下滑加载更多（' + (rows.length - state.limit) + ' 条已就绪）';
    } else if (monthsQueue.length) {
      more.hidden = false;
      moreText.textContent = '下滑加载更早的资讯（可至 ' + monthsQueue[monthsQueue.length - 1] + '）';
    } else {
      more.hidden = true;
    }
  }

  function renderMeta() {
    meta.innerHTML =
      '<span class="badge cat-sec">' + idx.source_count + ' 个情报源</span>' +
      '<span class="sep">/</span><span>归档收录 <b>' + idx.total + '</b> 条（' + idx.months.length + ' 个月）</span>' +
      '<span class="sep">/</span><span>最近同步 <b>' + esc(idx.generated_at) + '</b></span>';
  }

  function chipRow(groupKey, label, facet, order, labelMap) {
    var keys = order
      ? order.filter(function (k) { return facet[k]; })
      : Object.keys(facet);
    var html = '<div class="chips-row" data-group="' + groupKey + '"><span class="chips-label">' + label + '</span>' +
      '<button class="chip active" data-val="__all">全部</button>';
    keys.forEach(function (k) {
      var t = labelMap ? labelMap(k) : k;
      html += '<button class="chip" data-val="' + esc(k) + '">' + esc(t) + '<i>' + facet[k] + '</i></button>';
    });
    return html + '</div>';
  }

  function renderChips() {
    var f = idx.facets || {};
    chipsBox.innerHTML =
      chipRow('cat', '分类', f.categories || {}) +
      chipRow('prio', '级别', f.priorities || {}, ['P0', 'P1', 'P2'], function (k) {
        return k === 'P0' ? 'P0 紧急' : (k === 'P2' ? 'P2 常规' : k);
      }) +
      chipRow('src', '来源', f.sources || {});
  }

  function syncChips() {
    chipsBox.querySelectorAll('.chips-row').forEach(function (row) {
      var set = state[row.getAttribute('data-group')];
      row.querySelectorAll('.chip').forEach(function (c) {
        var v = c.getAttribute('data-val');
        c.classList.toggle('active', v === '__all' ? set.size === 0 : set.has(v));
      });
    });
  }

  var io = new IntersectionObserver(function (entries) {
    if (!entries[0].isIntersecting) return;
    var rows = items.filter(match);
    if (rows.length > state.limit) {
      state.limit += PER_BATCH;
      render();
    } else if (monthsQueue.length && !fullScan.running && !loading) {
      loading = true;
      loadMonths(1).then(function () { loading = false; render(); });
    }
  }, { rootMargin: '500px' });
  io.observe(more);

  var deb = null;
  search.addEventListener('input', function () {
    state.q = search.value.trim();
    state.limit = PER_BATCH;
    render();
    clearTimeout(deb);
    deb = setTimeout(function () { if (state.q) startFullScan(); }, 300);
  });

  chipsBox.addEventListener('click', function (e) {
    var b = e.target.closest('.chip');
    if (!b) return;
    var set = state[b.closest('.chips-row').getAttribute('data-group')];
    var v = b.getAttribute('data-val');
    if (v === '__all') set.clear();
    else if (set.has(v)) set.delete(v);
    else set.add(v);
    state.limit = PER_BATCH;
    syncChips();
    render();
  });

  fetchRetry(BASE + '/index.json').then(function (d) {
    idx = d;
    monthsQueue = d.months.map(function (m) { return m.month; });
    renderMeta();
    renderChips();
    return loadMonths(2);
  }).then(function () {
    render();
    var q = new URLSearchParams(location.search).get('q');
    if (q) {
      search.value = q;
      state.q = q;
      startFullScan();
      render();
    }
  }).catch(function () {
    meta.innerHTML = '<span class="badge prio-p0">情报归档服务暂不可达，稍后刷新重试</span>';
    more.hidden = true;
  });
})();
</script>
