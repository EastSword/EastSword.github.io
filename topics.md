---
layout: default
title: 研究课题
permalink: /topics/
---
<section id="topics">
  <div class="wrap wrap-wide">
    <div class="section-head">
      <div class="num">01 / RESEARCH</div>
      <h2>研究课题</h2>
      <p class="desc">研究 AI 如何安全地进入真实工作：技术拆解、实测复现与落地方法。每个课题长期维护，按道、法、术、器四层组织，聚合原创成果、精选外部资料与持续更新的情报。</p>
    </div>

    {% assign topics = site.topics | sort: date | reverse %}
    {% assign cats = "AI安全,身份安全,云安全,供应链安全,检测与响应,数据安全,运维安全" | split: "," %}

    <div class="topics-layout">
      <aside class="topics-side">
        <div class="side-search">
          <span class="icon">⌕</span>
          <input id="topic-search" type="text" placeholder="搜索课题 / 关键词 / 简介…" autocomplete="off">
        </div>
        <nav class="side-nav" id="cat-nav">
          <div class="side-nav-title">课题分类</div>
          <button class="side-link active" data-cat="全部" type="button">
            <span>全部课题</span><span class="side-count">{{ topics.size }}</span>
          </button>
          {% for cat in cats %}
          {% assign cat_n = topics | where_exp: "t", "t.categories contains cat" | size %}
          {% if cat_n > 0 %}
          <button class="side-link" data-cat="{{ cat }}" type="button">
            <span>{{ cat }}</span><span class="side-count">{{ cat_n }}</span>
          </button>
          {% endif %}
          {% endfor %}
        </nav>
        <nav class="side-nav" id="status-nav">
          <div class="side-nav-title">课题状态</div>
          {% assign st_done = topics | where: "status", "已结题" | size %}
          {% assign st_live = topics | where: "status", "研讨中" | size %}
          {% assign st_wait = topics | where: "status", "待开始" | size %}
          <button class="side-link active" data-status="全部" type="button">
            <span>全部状态</span><span class="side-count">{{ topics.size }}</span>
          </button>
          <button class="side-link" data-status="已结题" type="button">
            <span>已结题</span><span class="side-count">{{ st_done }}</span>
          </button>
          <button class="side-link" data-status="研讨中" type="button">
            <span>研讨中</span><span class="side-count">{{ st_live }}</span>
          </button>
          <button class="side-link" data-status="待开始" type="button">
            <span>待开始</span><span class="side-count">{{ st_wait }}</span>
          </button>
        </nav>
        <div class="side-note">
          一个课题可归属多个分类，从任一分类进入都能找到它。<br>
          课题详情页内按<b>道 · 法 · 术 · 器</b>四层组织：<em>道</em>是第一性原理的根本思考，<em>法</em>是抽象方法论，<em>术</em>是具体落地方法，<em>器</em>是工具与外部资源。
        </div>
      </aside>

      <div class="topics-main">
        <div class="topics-toolbar">
          <span class="tb-label" id="topic-count-label">全部课题 · {{ topics.size }} 个</span>
        </div>
        <div class="bento" id="topic-list">
          {% for t in topics %}
          {% include topic-tile.html t=t %}
          {% endfor %}
        </div>
        <div class="empty-result" id="empty-result" hidden>
          <div class="glyph">空</div>
          没有匹配的课题，换个分类或关键词试试
        </div>
        {% if topics.size == 0 %}
        <div class="placeholder-box">
          <div class="glyph">墨 · 俠</div>
          研究课题正整理入库，首发内容即将上线
        </div>
        {% endif %}
      </div>
    </div>

    {% assign resources = site.resources | sort: date | reverse %}
    {% if resources.size > 0 %}
    <section class="block res-block">
      <h2>精选外部资料</h2>
      <p class="block-note">只收核验过的来源：标注原作者、出处与推荐理由，以链接和自己的摘要为主，完整转载需取得授权。</p>
      <div class="resource-grid">
        {% for r in resources limit: 6 %}
        <a class="resource-card" href="{{ r.url }}" target="_blank" rel="noopener">
          <div class="rc-top">
            <span class="badge res-type">{{ r.type }}</span>
            <span class="rc-source">{{ r.source }}</span>
            {% if r.published %}<span class="rc-date">{{ r.published }}</span>{% endif %}
          </div>
          <div class="rc-title">{{ r.title }}</div>
          <div class="rc-reason">{{ r.reason }}</div>
          <div class="rc-topics">
            {% for tp in r.topics %}
            {% assign t_doc = site.topics | where: "slug", tp | first %}
            {% if t_doc %}<span class="rc-topic">{{ t_doc.title }}</span>{% endif %}
            {% endfor %}
          </div>
        </a>
        {% endfor %}
      </div>
      {% assign more_res = resources.size | minus: 6 %}
      {% if more_res > 0 %}
      <p class="block-more">另有 {{ more_res }} 条精选资料，按主题归档在各课题页内 → 从上方课题进入查看</p>
      {% else %}
      <p class="block-more">各课题页内还有按主题归类的完整资料清单 → 从上方课题进入查看</p>
      {% endif %}
    </section>
    {% endif %}

    <section class="block intel-block">
      <h2>最新情报</h2>
      <p class="block-note">来自每日同步的安全资讯归档，与课题主线相关的动态优先收录。</p>
      <div class="intel-list" id="topics-news-list">
        <noscript>
          <div class="placeholder-box slim">启用 JavaScript 可加载最新情报，或直接前往安全资讯频道。</div>
        </noscript>
      </div>
      <a class="block-more" href="{{ '/news/' | relative_url }}">进入安全资讯全量归档 →</a>
    </section>
  </div>
</section>

<script>
(function () {
  /* ---- 课题过滤：分类 × 状态 × 搜索 组合 ---- */
  var list = document.getElementById('topic-list');
  if (!list) return;
  var search = document.getElementById('topic-search');
  var empty = document.getElementById('empty-result');
  var label = document.getElementById('topic-count-label');
  var tiles = Array.prototype.slice.call(list.querySelectorAll('.tile'));
  var catLinks = Array.prototype.slice.call(document.querySelectorAll('#cat-nav .side-link'));
  var statusLinks = Array.prototype.slice.call(document.querySelectorAll('#status-nav .side-link'));
  var state = { cat: '全部', status: '全部', q: '' };

  function norm(s) { return (s || '').toLowerCase().trim(); }

  function apply() {
    var total = 0;
    tiles.forEach(function (t) {
      var cats = (t.getAttribute('data-cats') || '').split('|');
      var st = t.getAttribute('data-status') || '待开始';
      var hay = norm([t.getAttribute('data-title'), t.getAttribute('data-subtitle'),
                      t.getAttribute('data-keyword'),
                      (t.getAttribute('data-tags') || '').replace(/,/g, ' ')].join(' '));
      var okCat = state.cat === '全部' || cats.indexOf(state.cat) !== -1;
      var okSt = state.status === '全部' || st === state.status;
      var okQ = !state.q || hay.indexOf(norm(state.q)) !== -1;
      var show = okCat && okSt && okQ;
      t.style.display = show ? '' : 'none';
      if (show) total++;
    });
    if (empty) empty.hidden = total !== 0;
    if (label) {
      var catName = state.cat === '全部' ? '全部课题' : state.cat;
      var stName = state.status === '全部' ? '' : ' · ' + state.status;
      label.textContent = catName + stName + ' · ' + total + ' 个';
    }
  }

  catLinks.forEach(function (b) {
    b.addEventListener('click', function () {
      catLinks.forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active');
      state.cat = b.getAttribute('data-cat');
      apply();
    });
  });
  statusLinks.forEach(function (b) {
    b.addEventListener('click', function () {
      statusLinks.forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active');
      state.status = b.getAttribute('data-status');
      apply();
    });
  });
  if (search) {
    search.addEventListener('input', function () { state.q = search.value; apply(); });
  }
  apply();

  /* ---- 最新情报：复用资讯归档 feed ---- */
  var BASE = 'https://eastsword.github.io/news-archive';
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : '#'; }

  fetch(BASE + '/feed.json').then(function (r) { return r.json(); }).then(function (d) {
    var box = document.getElementById('topics-news-list');
    if (!box) return;
    var html = '';
    (d.items || []).slice(0, 6).forEach(function (n) {
      html += '<a class="news-item" href="' + esc(safeUrl(n.url)) + '" target="_blank" rel="noopener">' +
        '<span class="news-item-meta">' +
          '<span class="news-date">' + esc(n.published_date) + '</span>' +
          '<span class="badge ' + (n.category === 'AI安全' ? 'cat-ai' : 'cat-sec') + '">' + esc(n.category) + '</span>' +
          '<span class="news-source">' + esc(n.source) + '</span>' +
        '</span>' +
        '<span class="news-title">' + esc(n.title) + '</span>' +
        (n.title_zh ? '<span class="news-title-zh">' + esc(n.title_zh) + '</span>' : '') +
        '</a>';
    });
    if (html) box.innerHTML = html;
  }).catch(function () {});
})();
</script>
