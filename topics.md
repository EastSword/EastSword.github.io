---
layout: default
title: 研究话题
---
<section id="topics">
  <div class="wrap">
    <div class="section-head">
      <div class="num">01 / RESEARCH</div>
      <h2>研究话题</h2>
      <p class="desc">每个话题是一次完整的研究：从第一性原理拆解，配真实事件与可落地的检测基线，全平台形态入口聚合于话题页内，持续修订。</p>
    </div>

    {% assign topics = site.topics | sort: date | reverse %}
    {% if topics.size > 0 %}
    <div class="filter-bar">
      <div class="search-box">
        <span class="icon">⌕</span>
        <input id="topic-search" type="text" placeholder="搜索话题 / 关键词 / 简介…" autocomplete="off">
      </div>
      <div class="chips-rows">
        <div class="chips-row">
          <span class="chips-label">领域</span>
          <div class="tag-chips" id="cat-chips">
            <button class="chip cat active" data-cat="__all">全部</button>
            {% assign all_cats = topics | map: "category" | join: "," | split: "," | uniq | sort %}
            {% for c in all_cats %}
            <button class="chip cat" data-cat="{{ c }}">{{ c }}</button>
            {% endfor %}
          </div>
        </div>
        <div class="chips-row">
          <span class="chips-label">标签</span>
          <div class="tag-chips" id="tag-chips">
            <button class="chip active" data-tag="__all">全部</button>
            {% assign all_tags = topics | map: "tags" | join: "," | split: "," | uniq | sort %}
            {% for tg in all_tags %}
            <button class="chip" data-tag="{{ tg }}">{{ tg }}</button>
            {% endfor %}
          </div>
        </div>
      </div>
    </div>
    {% endif %}

    <div class="bento" id="topic-list">
      {% for t in topics %}
      {% assign t_tags = t.tags | join: "," %}
      <a class="tile" href="{{ t.url | relative_url }}"
         data-title="{{ t.title | escape }}"
         data-subtitle="{{ t.subtitle | escape }}"
         data-keyword="{{ t.keyword | escape }}"
         data-cat="{{ t.category | default: '未分类' }}"
         data-tags="{{ t_tags }}">
        <div class="row1">
          {% if t.status == "published" %}
            <span class="badge published">已发布</span>
          {% elsif t.status == "publishing" %}
            <span class="badge publishing">发布中</span>
          {% else %}
            <span class="badge drafting">撰写中</span>
          {% endif %}
          {% if t.category %}<span class="badge cat-badge">{{ t.category }}</span>{% endif %}
          {% if t.keyword %}<span class="badge keyword">{{ t.keyword }}</span>{% endif %}
          <h3>{{ t.title }}</h3>
          <span class="arrow">→</span>
        </div>
        <div class="row2">
          <span>{{ t.subtitle }}</span>
          <span class="dot">·</span>
          <span>{{ t.date | date: "%Y-%m-%d" }}</span>
          {% assign link_count = t.links | size %}
          <span class="dot">·</span>
          <span>{{ link_count }}+ 平台形态</span>
          {% for tg in t.tags %}<span class="mini-tag">{{ tg }}</span>{% endfor %}
        </div>
      </a>
      {% endfor %}
    </div>

    <div class="pager" id="pager"></div>
    <div class="empty-result" id="empty-result" hidden>
      <div class="glyph">空</div>
      没有匹配的话题，换个关键词试试
    </div>

    {% if topics.size == 0 %}
    <div class="placeholder-box">
      <div class="glyph">墨 · 俠</div>
      研究话题正整理入库，首发内容即将上线
    </div>
    {% endif %}
  </div>
</section>

<script>
(function () {
  var list = document.getElementById('topic-list');
  if (!list) return;
  var tiles = Array.prototype.slice.call(list.querySelectorAll('.tile'));
  var search = document.getElementById('topic-search');
  var catChips = document.getElementById('cat-chips');
  var tagChips = document.getElementById('tag-chips');
  var pager = document.getElementById('pager');
  var empty = document.getElementById('empty-result');
  var PER_PAGE = 6;
  var state = { q: '', cat: '__all', tag: '__all', page: 1 };

  function norm(s) { return (s || '').toLowerCase().trim(); }

  function filtered() {
    return tiles.filter(function (t) {
      if (state.cat !== '__all' && t.getAttribute('data-cat') !== state.cat) return false;
      var tags = (t.getAttribute('data-tags') || '').split(',');
      if (state.tag !== '__all' && tags.indexOf(state.tag) === -1) return false;
      if (state.q) {
        var hay = norm([t.getAttribute('data-title'), t.getAttribute('data-subtitle'),
                        t.getAttribute('data-keyword'), t.getAttribute('data-cat'), tags.join(' ')].join(' '));
        if (hay.indexOf(norm(state.q)) === -1) return false;
      }
      return true;
    });
  }

  function render() {
    var items = filtered();
    var pages = Math.max(1, Math.ceil(items.length / PER_PAGE));
    if (state.page > pages) state.page = pages;
    var start = (state.page - 1) * PER_PAGE;

    tiles.forEach(function (t) { t.style.display = 'none'; });
    items.slice(start, start + PER_PAGE).forEach(function (t) { t.style.display = ''; });
    empty.hidden = items.length !== 0;

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
  if (catChips) {
    catChips.addEventListener('click', function (e) {
      var b = e.target.closest('.chip');
      if (!b) return;
      catChips.querySelectorAll('.chip').forEach(function (c) { c.classList.remove('active'); });
      b.classList.add('active');
      state.cat = b.getAttribute('data-cat');
      state.page = 1;
      render();
    });
  }
  if (tagChips) {
    tagChips.addEventListener('click', function (e) {
      var b = e.target.closest('.chip');
      if (!b) return;
      tagChips.querySelectorAll('.chip').forEach(function (c) { c.classList.remove('active'); });
      b.classList.add('active');
      state.tag = b.getAttribute('data-tag');
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
      var top = document.getElementById('topics').getBoundingClientRect().top + window.pageYOffset - 90;
      window.scrollTo({ top: top, behavior: 'smooth' });
    });
  }
  render();
})();
</script>
