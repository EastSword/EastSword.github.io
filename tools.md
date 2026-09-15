---
layout: default
title: 安全藏经阁
permalink: /tools/
---
<section id="tools">
  <div class="wrap wrap-wide">
    {% include section-head.html key="tools" %}

    <div class="topics-layout">
      <aside class="topics-side">
        <div class="side-search">
          <span class="icon">⌕</span>
          <input id="tool-search" type="search" aria-label="搜索资源" placeholder="搜索资源 / 描述 / 标签…" autocomplete="off">
        </div>
        <nav class="side-nav" id="cat-nav" aria-label="藏经分类">
          <div class="side-nav-title">藏经分类</div>
          <div id="tool-cat-links"></div>
        </nav>
        <nav class="side-nav" id="rank-nav" aria-label="试炼筛选">
          <div class="side-nav-title">试炼筛选</div>
          <div id="tool-rank-links"></div>
        </nav>
        <div class="side-note">
          带 <b>天 / 地 / 玄</b> 徽标的是本站试炼过的兵器，附实战心得：<b>天</b> 必备主力 ／ <b>地</b> 场景利器 ／ <b>玄</b> 备选兵器；其余为公开收录资源。<br>
          SRC 名录、漏洞平台等挖洞核心分类置顶；接码、匿名邮箱等灰色资源置底备查。<br>
          公开资源主要整理自 <a href="https://dh.aabyss.cn" target="_blank" rel="noopener">大海导航</a>，向原作者致谢。
        </div>
      </aside>

      <div class="topics-main">
        <div class="tool-stats" id="tool-stats" role="status" aria-label="收录统计"></div>
        <div class="topics-toolbar">
          <span class="tb-label" id="tool-count-label"></span>
          <span class="quiet">试炼兵器在前 · 按分类归档</span>
        </div>
        <div class="tool-grid" id="tool-grid"></div>
        <div class="empty-result" id="tool-empty" hidden>
          <div class="glyph">藏</div>
          <span id="tool-empty-text">没有匹配的资源，换个关键词试试</span>
        </div>
        <div class="tool-more-wrap" id="tool-more-wrap" hidden>
          <button class="tool-more" id="tool-more" type="button">继续展开</button>
          <div class="tool-sentinel" id="tool-sentinel" aria-hidden="true"></div>
        </div>
      </div>
    </div>

    <section class="block suggest-block">
      <h2>收录意见</h2>
      <p class="block-note">
        举荐好资源、纠正收录信息、催更某个分类，都欢迎在下面留言——GitHub 登录即可发言，被采纳的候选将试炼后上墙。
        <a class="admin-link" href="https://github.com/EastSword/EastSword.github.io/discussions" target="_blank" rel="noopener" title="仓库所有者可在 GitHub 上管理留言">留言管理</a>
      </p>
      <div class="wall-frame suggest-frame">
        <div class="wall-hint">GITHUB 留言 · 实时显示 · 支持表情回应</div>
        <div id="arsenal-giscus" class="giscus-mount"></div>
        <div class="wall-loading" id="suggest-loading"><span class="glyph">荐</span><span>意见箱展开中…</span></div>
      </div>
    </section>
  </div>
</section>

<script>
/* ============================================================
   藏经阁维护入口：日常维护只改 _data/tools.yml，其余全自动
   1) groups     —— 分组骨架（顺序即侧边栏顺序；灰色资源置底）
   2) categories —— 分类 key -> {name, group}
   3) items      —— 资源条目；试炼条目带 rank/date/access/tags/curated
   侧边栏分组导航、统计条、卡片、筛选、搜索、分页全部自动生成
   支持 URL 直达筛选：/tools/?cat=src_platform&group=hunt&rank=curated&q=src
   ============================================================ */
(function () {
  var GROUPS = {{ site.data.tools.groups | jsonify }};
  var CATS = {{ site.data.tools.categories | jsonify }};
  var TOOLS = {{ site.data.tools.items | jsonify }};

  var RANK_CHAR = { s: '天', a: '地', b: '玄' };
  var RANK_LABEL = { s: '天字级 · 必备主力', a: '地字级 · 场景利器', b: '玄字级 · 备选兵器' };
  var PAGE_SIZE = 60;

  var grid = document.getElementById('tool-grid');
  if (!grid) return;
  var search = document.getElementById('tool-search');
  var catBox = document.getElementById('tool-cat-links');
  var rankBox = document.getElementById('tool-rank-links');
  var statsBox = document.getElementById('tool-stats');
  var label = document.getElementById('tool-count-label');
  var empty = document.getElementById('tool-empty');
  var emptyText = document.getElementById('tool-empty-text');
  var moreWrap = document.getElementById('tool-more-wrap');
  var moreBtn = document.getElementById('tool-more');

  var params = new URLSearchParams(window.location.search);
  var state = {
    q: params.get('q') || '',
    cat: params.get('cat') || '__all',
    group: params.get('group') || '__all',
    rank: params.get('rank') || '__all',
    page: 1
  };
  if (!CATS[state.cat]) state.cat = '__all';
  if (!GROUPS[state.group]) state.group = '__all';
  if (['curated', 's', 'a', 'b'].indexOf(state.rank) === -1) state.rank = '__all';
  if (search) search.value = state.q;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function host(u) {
    try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return u; }
  }
  function countBy(arr, fn) {
    var m = {};
    arr.forEach(function (x) { var k = fn(x); m[k] = (m[k] || 0) + 1; });
    return m;
  }
  function shortDate(d) {
    d = String(d || '');
    return d.length >= 10 ? d.slice(5).replace('-', '/') : '';
  }

  /* ---- FOFA 风格统计条：总量 / 试炼 / 分类 / SRC / 最近收录 ---- */
  function renderStats() {
    if (!statsBox) return;
    var curated = TOOLS.filter(function (t) { return t.curated; }).length;
    var srcN = TOOLS.filter(function (t) { return t.cat === 'src_platform'; }).length;
    var latest = '';
    TOOLS.forEach(function (t) { var d = String(t.date || ''); if (d > latest) latest = d; });
    statsBox.innerHTML =
      '<div class="ts-cell ts-hero"><span class="ts-num">' + TOOLS.length + '</span><span class="ts-label">已藏资源</span></div>' +
      '<div class="ts-cell"><span class="ts-num rank-s">' + curated + '</span><span class="ts-label">试炼兵器 · 附心得</span></div>' +
      '<div class="ts-cell"><span class="ts-num rank-a">' + srcN + '</span><span class="ts-label">SRC 平台名录</span></div>' +
      '<div class="ts-cell"><span class="ts-num">' + Object.keys(CATS).length + '</span><span class="ts-label">藏经分类</span></div>' +
      '<div class="ts-cell"><span class="ts-num">' + Object.keys(GROUPS).length + '</span><span class="ts-label">资源分组</span></div>' +
      '<div class="ts-cell"><span class="ts-num ts-date">' + (shortDate(latest) || '—') + '</span><span class="ts-label">最近收录</span></div>';
  }

  /* ---- 侧边栏：分组导航（组标题可点整组筛选，分类缩进带计数） ---- */
  function renderNav() {
    if (!catBox) return;
    var cn = countBy(TOOLS, function (t) { return t.cat; });
    var gn = countBy(TOOLS, function (t) { return CATS[t.cat] ? CATS[t.cat].group : ''; });
    var html = '<button class="side-link active" data-cat="__all" type="button"><span>全部资源</span><span class="side-count">' + TOOLS.length + '</span></button>';
    Object.keys(GROUPS).forEach(function (gk) {
      if (!gn[gk]) return;
      html += '<button class="side-group' + (gk === 'gray' ? ' gray-group' : '') + '" data-group="' + esc(gk) + '" type="button">' +
        '<span>' + esc(GROUPS[gk]) + '</span><span class="side-count">' + gn[gk] + '</span></button>';
      Object.keys(CATS).forEach(function (ck) {
        if (CATS[ck].group !== gk || !cn[ck]) return;
        html += '<button class="side-link sub" data-cat="' + esc(ck) + '" type="button"><span>' + esc(CATS[ck].name) + '</span><span class="side-count">' + cn[ck] + '</span></button>';
      });
    });
    catBox.innerHTML = html;

    if (rankBox) {
      var rn = countBy(TOOLS, function (t) { return t.curated ? (t.rank || '') : ''; });
      var curatedN = TOOLS.filter(function (t) { return t.curated; }).length;
      var rh = '<button class="side-link active" data-rank="__all" type="button"><span>全部资源</span><span class="side-count">' + TOOLS.length + '</span></button>';
      rh += '<button class="side-link" data-rank="curated" type="button" title="本站亲自试炼过的兵器"><span>试炼精选</span><span class="side-count">' + curatedN + '</span></button>';
      ['s', 'a', 'b'].forEach(function (r) {
        rh += '<button class="side-link" data-rank="' + r + '" type="button" title="' + esc(RANK_LABEL[r] || '') + '"><span>' + RANK_CHAR[r] + '字级</span><span class="side-count">' + (rn[r] || 0) + '</span></button>';
      });
      rankBox.innerHTML = rh;
    }
  }

  function syncNav() {
    if (catBox) {
      catBox.querySelectorAll('.side-link').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-cat') === state.cat);
      });
      catBox.querySelectorAll('.side-group').forEach(function (b) {
        var gk = b.getAttribute('data-group');
        var on = state.group === gk && state.cat === '__all';
        b.classList.toggle('active', on);
      });
    }
    if (rankBox) {
      rankBox.querySelectorAll('.side-link').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-rank') === state.rank);
      });
    }
  }

  function matches(t) {
    if (state.cat !== '__all' && t.cat !== state.cat) return false;
    if (state.group !== '__all') {
      var meta = CATS[t.cat];
      if (!meta || meta.group !== state.group) return false;
    }
    if (state.rank === 'curated' && !t.curated) return false;
    if (state.rank !== '__all' && state.rank !== 'curated' && t.rank !== state.rank) return false;
    if (state.q) {
      var meta2 = CATS[t.cat] || {};
      var hay = [t.name, t.sub, t.desc, t.access, meta2.name, (t.tags || []).join(' ')]
        .join(' ').toLowerCase();
      if (hay.indexOf(state.q.trim().toLowerCase()) === -1) return false;
    }
    return true;
  }

  /* ---- 卡片：试炼兵器完整卡 / 公开收录紧凑卡 ---- */
  /* favicon 三级容错：favicon.im → Google s2 → 站名首字水墨占位 */
  window.__icoErr = function (img) {
    if (img.getAttribute('data-fb') === '1') {
      var span = document.createElement('span');
      span.className = 'tool-ico ico-fallback';
      span.textContent = img.getAttribute('data-letter') || '站';
      if (img.parentNode) img.parentNode.replaceChild(span, img);
      else img.remove();
    } else {
      img.setAttribute('data-fb', '1');
      img.src = 'https://www.google.com/s2/favicons?domain=' + img.getAttribute('data-host') + '&sz=64';
    }
  };
  function icoHtml(t) {
    var h = host(t.url);
    var letter = String(t.name || h || '站').trim().charAt(0).toUpperCase() || '站';
    return '<img class="tool-ico" src="https://favicon.im/' + esc(h) + '?larger=true" alt="" width="20" height="20" ' +
      'loading="lazy" decoding="async" referrerpolicy="no-referrer" ' +
      'data-host="' + esc(h) + '" data-letter="' + esc(letter) + '" onerror="__icoErr(this)">';
  }
  function cardHtml(t) {
    var ico = icoHtml(t);
    if (!t.curated) {
      return '<a class="tool-card plain" href="' + esc(t.url) + '" target="_blank" rel="noopener">' +
        '<div class="tool-head">' +
          ico +
          '<span class="tool-name">' + esc(t.name) + '</span>' +
          '<span class="tool-sub">' + esc(host(t.url)) + '</span>' +
          '<span class="tool-arrow">↗</span>' +
        '</div>' +
        (t.desc ? '<p class="tool-desc">' + esc(t.desc) + '</p>' : '') +
      '</a>';
    }
    var d = shortDate(t.date);
    return '<a class="tool-card curated" href="' + esc(t.url) + '" target="_blank" rel="noopener" title="' + esc(RANK_LABEL[t.rank] || '') + '">' +
      '<div class="tool-head">' +
        '<span class="tool-rank ' + esc(t.rank) + '">' + (RANK_CHAR[t.rank] || '玄') + '</span>' +
        ico +
        '<span class="tool-name">' + esc(t.name) + '</span>' +
        '<span class="tool-sub">' + esc(t.sub || '') + '</span>' +
        '<span class="tool-arrow">↗</span>' +
      '</div>' +
      '<p class="tool-desc">' + esc(t.desc) + '</p>' +
      '<div class="tool-tags">' + (t.tags || []).map(function (g) {
        return '<span class="mini-tag">' + esc(g) + '</span>';
      }).join('') + '</div>' +
      '<div class="tool-foot">' +
        '<span class="badge cat-badge">' + esc((CATS[t.cat] || {}).name || '') + '</span>' +
        '<span class="tool-access">' + esc(t.access || '') + '</span>' +
        (d ? '<span class="tool-date">' + d + ' 入谱</span>' : '') +
        '<span class="tool-host">' + esc(host(t.url)) + '</span>' +
      '</div>' +
    '</a>';
  }

  /* ---- 渲染：筛选 + 分页（每页 60，滚动到底自动展开） ---- */
  function render(reset) {
    if (reset) state.page = 1;
    var items = TOOLS.filter(matches);
    var shown = items.slice(0, state.page * PAGE_SIZE);
    grid.innerHTML = shown.map(cardHtml).join('');

    if (label) {
      var parts = [];
      if (state.cat !== '__all') parts.push((CATS[state.cat] || {}).name || state.cat);
      else if (state.group !== '__all') parts.push(GROUPS[state.group] || '');
      else parts.push('全部资源');
      if (state.rank === 'curated') parts.push('试炼精选');
      else if (state.rank !== '__all') parts.push(RANK_CHAR[state.rank] + '字级');
      if (state.q) parts.push('「' + state.q + '」');
      label.textContent = parts.join(' · ') + ' · ' + items.length + ' 条' +
        (shown.length < items.length ? '（已展开 ' + shown.length + '）' : '');
    }

    var noMatch = items.length === 0;
    empty.hidden = !noMatch;
    if (noMatch) {
      emptyText.textContent = (state.cat !== '__all' || state.group !== '__all' || state.rank !== '__all')
        ? '该条件下暂无资源，换个分类或筛选试试'
        : '没有匹配的资源，换个关键词试试';
    }

    if (moreWrap) {
      moreWrap.hidden = shown.length >= items.length;
      if (moreBtn) {
        var rest = items.length - shown.length;
        moreBtn.textContent = rest > 0 ? '继续展开 · 还剩 ' + rest + ' 条' : '已全部展开';
      }
    }
  }

  function loadMore() {
    var items = TOOLS.filter(matches);
    if (state.page * PAGE_SIZE >= items.length) return;
    state.page++;
    render();
  }

  if (search) {
    search.addEventListener('input', function () { state.q = search.value; render(true); });
  }
  if (catBox) {
    catBox.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      if (b.classList.contains('side-group')) {
        state.group = b.getAttribute('data-group');
        state.cat = '__all';
      } else {
        state.cat = b.getAttribute('data-cat');
        if (state.cat === '__all') state.group = '__all';
      }
      syncNav();
      render(true);
    });
  }
  if (rankBox) {
    rankBox.addEventListener('click', function (e) {
      var b = e.target.closest('.side-link');
      if (!b) return;
      state.rank = b.getAttribute('data-rank');
      syncNav();
      render(true);
    });
  }
  if (moreBtn) {
    moreBtn.addEventListener('click', loadMore);
  }

  renderStats();
  renderNav();
  syncNav();
  render(true);

  /* ---- 滚动到底自动展开下一页 ---- */
  var sentinel = document.getElementById('tool-sentinel');
  if (sentinel && 'IntersectionObserver' in window) {
    var busy = false;
    var io = new IntersectionObserver(function (entries) {
      if (!entries.some(function (e) { return e.isIntersecting; }) || busy) return;
      busy = true;
      loadMore();
      setTimeout(function () { busy = false; }, 250);
    }, { rootMargin: '400px' });
    io.observe(sentinel);
  }
})();

/* ---- 收录意见箱：giscus 独立讨论串，滚动到可视区再加载 ---- */
(function () {
  var mount = document.getElementById('arsenal-giscus');
  if (!mount) return;
  var loaded = false;

  function loadBox() {
    if (loaded) return;
    loaded = true;
    var s = document.createElement('script');
    s.src = 'https://giscus.app/client.js';
    s.async = true;
    s.crossOrigin = 'anonymous';
    s.setAttribute('data-repo', 'EastSword/EastSword.github.io');
    s.setAttribute('data-repo-id', 'R_kgDOINsDXg');
    s.setAttribute('data-category', 'General');
    s.setAttribute('data-category-id', 'DIC_kwDOINsDXs4DEYFm');
    s.setAttribute('data-mapping', 'specific');
    s.setAttribute('data-term', '藏经阁 · 收录意见');
    s.setAttribute('data-strict', '1');
    s.setAttribute('data-reactions-enabled', '1');
    s.setAttribute('data-emit-metadata', '0');
    s.setAttribute('data-input-position', 'top');
    s.setAttribute('data-theme', 'https://eastsword.github.io/assets/giscus-theme.css');
    s.setAttribute('data-lang', 'zh-CN');
    mount.appendChild(s);

    var timer = setInterval(function () {
      if (mount.querySelector('iframe')) {
        clearInterval(timer);
        var l = document.getElementById('suggest-loading');
        if (l) l.remove();
      }
    }, 400);
    setTimeout(function () { clearInterval(timer); }, 30000);
  }

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      if (entries.some(function (e) { return e.isIntersecting; })) {
        io.disconnect();
        loadBox();
      }
    }, { rootMargin: '300px' });
    io.observe(mount);
  } else {
    loadBox();
  }
})();
</script>
