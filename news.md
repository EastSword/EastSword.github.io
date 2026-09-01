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
      <p class="desc">直连内网情报聚合服务，覆盖 CISA、Mandiant、MSRC、FreeBuf 等全球安全源与 AI 安全源，每日 10:00 自动同步前一天情报。按时间倒序，标签可多选组合筛选。</p>
    </div>

    {% if site.data.news %}
    <div class="news-meta">
      <span class="badge cat-sec">{{ site.data.news.source_count }} 个情报源</span>
      <span class="sep">/</span>
      <span>当前收录 <b>{{ site.data.news.items | size }}</b> 条</span>
      <span class="sep">/</span>
      <span>最近同步 <b>{{ site.data.news.generated_at }}</b></span>
    </div>

    <div class="filter-bar filter-bar-col">
      <div class="search-box">
        <span class="icon">⌕</span>
        <input id="news-search" type="text" placeholder="搜索标题 / 来源…" autocomplete="off">
      </div>

      <div class="chips-rows" id="news-chips">
        {% assign news_cats = site.data.news.items | map: "category" | uniq | sort %}
        <div class="chips-row" data-group="cat">
          <span class="chips-label">分类</span>
          <button class="chip active" data-val="__all">全部</button>
          {% for c in news_cats %}
          <button class="chip" data-val="{{ c }}">{{ c }}</button>
          {% endfor %}
        </div>

        {% assign prios_present = site.data.news.items | map: "priority" | uniq %}
        {% assign prio_order = "P0,P1,P2" | split: "," %}
        <div class="chips-row" data-group="prio">
          <span class="chips-label">级别</span>
          <button class="chip active" data-val="__all">全部</button>
          {% for p in prio_order %}
          {% if prios_present contains p %}
          {% case p %}{% when "P0" %}{% assign pl = "P0 紧急" %}{% when "P1" %}{% assign pl = "P1 重要" %}{% else %}{% assign pl = "P2 常规" %}{% endcase %}
          <button class="chip" data-val="{{ p }}">{{ pl }}</button>
          {% endif %}
          {% endfor %}
        </div>

        {% assign news_srcs = site.data.news.items | map: "source" | uniq | sort %}
        <div class="chips-row" data-group="src">
          <span class="chips-label">来源</span>
          <button class="chip active" data-val="__all">全部</button>
          {% for s in news_srcs %}
          <button class="chip" data-val="{{ s }}">{{ s }}</button>
          {% endfor %}
        </div>
      </div>
      <div class="filter-count" id="news-count"></div>
    </div>

    <div class="news-list" id="news-list">
      {% for n in site.data.news.items %}
      <a class="news-item" href="{{ n.url }}" target="_blank" rel="noopener"
         data-cat="{{ n.category }}" data-prio="{{ n.priority }}" data-source="{{ n.source }}"
         data-ts="{{ n.published_at }}"
         data-title="{{ n.title | escape }}">
        <span class="news-date">{{ n.published_date }}</span>
        <span class="badge prio-{{ n.priority | downcase }}">{{ n.priority }}{% if n.priority == "P0" %} 紧急{% elsif n.priority == "P2" %} 常规{% endif %}</span>
        <span class="badge {% if n.category == 'AI安全' %}cat-ai{% else %}cat-sec{% endif %}">{{ n.category }}</span>
        <span class="news-title">{{ n.title }}</span>
        <span class="news-source">{{ n.source }}</span>
      </a>
      {% endfor %}
    </div>

    <div class="pager" id="news-pager"></div>
    <div class="empty-result" id="news-empty" hidden>
      <div class="glyph">空</div>
      没有匹配的资讯，换个关键词或放宽标签试试
    </div>
    {% else %}
    <div class="placeholder-box">
      <div class="glyph">讯</div>
      情报源接入中，运行 scripts/sync_news.py 首次同步
    </div>
    {% endif %}
  </div>
</section>

<script>
(function () {
  var list = document.getElementById('news-list');
  if (!list) return;
  var items = Array.prototype.slice.call(list.querySelectorAll('.news-item'));
  var search = document.getElementById('news-search');
  var chips = document.getElementById('news-chips');
  var pager = document.getElementById('news-pager');
  var empty = document.getElementById('news-empty');
  var count = document.getElementById('news-count');
  var PER_PAGE = 20;
  var state = { q: '', cat: new Set(), prio: new Set(), src: new Set(), page: 1 };

  function norm(s) { return (s || '').toLowerCase().trim(); }

  // 防御性按真实时间倒序：数据侧已按时间戳排序，这里兜底（混时区的 RFC822 串不能字符串比较）
  function ts(el) {
    var t = Date.parse(el.getAttribute('data-ts') || '');
    return isNaN(t) ? 0 : t;
  }
  items.sort(function (a, b) { return ts(b) - ts(a); });
  items.forEach(function (el) { list.appendChild(el); });

  function inGroup(set, val) { return set.size === 0 || set.has(val); }

  function filtered() {
    return items.filter(function (t) {
      if (!inGroup(state.cat, t.getAttribute('data-cat'))) return false;
      if (!inGroup(state.prio, t.getAttribute('data-prio'))) return false;
      if (!inGroup(state.src, t.getAttribute('data-source'))) return false;
      if (state.q) {
        var hay = norm([t.getAttribute('data-title'), t.getAttribute('data-source'), t.getAttribute('data-cat')].join(' '));
        if (hay.indexOf(norm(state.q)) === -1) return false;
      }
      return true;
    });
  }

  function syncChips() {
    chips.querySelectorAll('.chips-row').forEach(function (row) {
      var group = row.getAttribute('data-group');
      var set = state[group];
      row.querySelectorAll('.chip').forEach(function (c) {
        var v = c.getAttribute('data-val');
        c.classList.toggle('active', v === '__all' ? set.size === 0 : set.has(v));
      });
    });
  }

  function render() {
    var rows = filtered();
    var pages = Math.max(1, Math.ceil(rows.length / PER_PAGE));
    if (state.page > pages) state.page = pages;
    var start = (state.page - 1) * PER_PAGE;

    items.forEach(function (t) { t.style.display = 'none'; });
    rows.slice(start, start + PER_PAGE).forEach(function (t) { t.style.display = ''; });
    empty.hidden = rows.length !== 0;
    if (count) {
      var parts = [];
      if (state.cat.size) parts.push('分类 ' + Array.from(state.cat).join('、'));
      if (state.prio.size) parts.push('级别 ' + Array.from(state.prio).join('、'));
      if (state.src.size) parts.push('来源 ' + Array.from(state.src).join('、'));
      count.textContent = '命中 ' + rows.length + ' 条' + (parts.length ? ' ｜ ' + parts.join(' · ') : '');
    }

    if (pages <= 1) { pager.innerHTML = ''; return; }
    var html = '';
    if (state.page > 1) html += '<button data-go="' + (state.page - 1) + '">‹</button>';
    var lo = Math.max(1, state.page - 3), hi = Math.min(pages, state.page + 3);
    if (lo > 1) html += '<button data-go="1">1</button><span class="dots">…</span>';
    for (var i = lo; i <= hi; i++) {
      html += '<button data-go="' + i + '"' + (i === state.page ? ' class="cur"' : '') + '>' + i + '</button>';
    }
    if (hi < pages) html += '<span class="dots">…</span><button data-go="' + pages + '">' + pages + '</button>';
    if (state.page < pages) html += '<button data-go="' + (state.page + 1) + '">›</button>';
    pager.innerHTML = html;
  }

  if (search) {
    search.addEventListener('input', function () { state.q = search.value; state.page = 1; render(); });
  }
  if (chips) {
    chips.addEventListener('click', function (e) {
      var b = e.target.closest('.chip');
      if (!b) return;
      var row = b.closest('.chips-row');
      var group = row.getAttribute('data-group');
      var set = state[group];
      var v = b.getAttribute('data-val');
      if (v === '__all') { set.clear(); }
      else if (set.has(v)) { set.delete(v); }
      else { set.add(v); }
      state.page = 1;
      syncChips();
      render();
    });
  }
  if (pager) {
    pager.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-go]');
      if (!b) return;
      state.page = parseInt(b.getAttribute('data-go'), 10);
      render();
      var top = document.getElementById('news').getBoundingClientRect().top + window.pageYOffset - 90;
      window.scrollTo({ top: top, behavior: 'smooth' });
    });
  }
  syncChips();
  render();
})();
</script>
