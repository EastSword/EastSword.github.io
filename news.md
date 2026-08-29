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
      <p class="desc">直连内网情报聚合服务，覆盖 CISA、Mandiant、MSRC、FreeBuf 等全球安全源与 AI 安全源，每日 10:00 自动同步前一天情报。</p>
    </div>

    {% if site.data.news %}
    <div class="news-meta">
      <span class="badge cat-sec">{{ site.data.news.source_count }} 个情报源</span>
      <span class="sep">/</span>
      <span>当前收录 <b>{{ site.data.news.items | size }}</b> 条</span>
      <span class="sep">/</span>
      <span>最近同步 <b>{{ site.data.news.generated_at }}</b></span>
    </div>

    <div class="filter-bar">
      <div class="search-box">
        <span class="icon">⌕</span>
        <input id="news-search" type="text" placeholder="搜索标题 / 来源…" autocomplete="off">
      </div>
      <div class="tag-chips" id="news-chips">
        <button class="chip active" data-cat="__all">全部</button>
        {% assign news_cats = site.data.news.items | map: "category" | uniq | sort %}
        {% for c in news_cats %}
        <button class="chip" data-cat="{{ c }}">{{ c }}</button>
        {% endfor %}
      </div>
    </div>

    <div class="news-list" id="news-list">
      {% for n in site.data.news.items %}
      <a class="news-item" href="{{ n.url }}" target="_blank" rel="noopener"
         data-cat="{{ n.category }}" data-source="{{ n.source }}"
         data-title="{{ n.title | escape }}">
        <span class="news-date">{{ n.published_date }}</span>
        <span class="badge {% if n.category == 'AI安全' %}cat-ai{% else %}cat-sec{% endif %}">{{ n.category }}</span>
        <span class="news-title">{{ n.title }}</span>
        <span class="news-source">{{ n.source }}</span>
      </a>
      {% endfor %}
    </div>

    <div class="pager" id="news-pager"></div>
    <div class="empty-result" id="news-empty" hidden>
      <div class="glyph">空</div>
      没有匹配的资讯，换个关键词试试
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
  var PER_PAGE = 20;
  var state = { q: '', cat: '__all', page: 1 };

  function norm(s) { return (s || '').toLowerCase().trim(); }

  function filtered() {
    return items.filter(function (t) {
      if (state.cat !== '__all' && t.getAttribute('data-cat') !== state.cat) return false;
      if (state.q) {
        var hay = norm([t.getAttribute('data-title'), t.getAttribute('data-source'), t.getAttribute('data-cat')].join(' '));
        if (hay.indexOf(norm(state.q)) === -1) return false;
      }
      return true;
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

    if (pages <= 1) { pager.innerHTML = ''; return; }
    var html = '';
    if (state.page > 1) html += '<button data-go="' + (state.page - 1) + '">‹</button>';
    for (var i = 1; i <= pages; i++) {
      html += '<button data-go="' + i + '"' + (i === state.page ? ' class="cur"' : '') + '>' + i + '</button>';
    }
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
      chips.querySelectorAll('.chip').forEach(function (c) { c.classList.remove('active'); });
      b.classList.add('active');
      state.cat = b.getAttribute('data-cat');
      state.page = 1;
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
  render();
})();
</script>
