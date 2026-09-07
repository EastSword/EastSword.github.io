---
layout: default
title: 研究课题
permalink: /topics/
---
<section id="topics">
  <div class="wrap">
    <div class="section-head">
      <div class="num">01 / RESEARCH</div>
      <h2>研究课题</h2>
      <p class="desc">研究 AI 如何安全地进入真实工作：技术拆解、实测复现与落地方法。每个课题长期维护，聚合原创成果、精选外部资料与持续更新的情报。</p>
    </div>

    <div class="topic-charter">
      <div class="charter-brand">千里 · 东方隐侠</div>
      <p class="charter-line">研究 AI 如何安全地进入真实工作，提供技术拆解、实测与落地方法。</p>
      <div class="charter-aud">
        <span class="ca-label">服务对象</span>
        <em>正在使用 AI 的研发人员</em>
        <span class="ca-dot">·</span>
        <em>负责企业 AI 接入的安全负责人</em>
      </div>
    </div>

    <div class="column-cards">
      <a class="column-card" href="#col-hot">
        <span class="cc-name">热点拆解</span>
        <span class="cc-q">新工具、新功能、新事件，对实际使用有什么影响？</span>
        <span class="cc-go">进入课题 →</span>
      </a>
      <a class="column-card" href="#col-lab">
        <span class="cc-name">实测与复现</span>
        <span class="cc-q">它到底能做什么、在哪里失败、控制措施是否有效？</span>
        <span class="cc-go">进入课题 →</span>
      </a>
      <a class="column-card" href="#col-gov">
        <span class="cc-name">接入与治理</span>
        <span class="cc-q">企业应该怎样配置、评估和管理？</span>
        <span class="cc-go">进入课题 →</span>
      </a>
    </div>

    {% assign topics = site.topics | sort: date | reverse %}

    <div class="filter-bar simple">
      <div class="search-box">
        <span class="icon">⌕</span>
        <input id="topic-search" type="text" placeholder="搜索课题 / 关键词 / 简介…" autocomplete="off">
      </div>
    </div>

    {% assign col_hot = topics | where: "column", "热点拆解" %}
    {% assign col_lab = topics | where: "column", "实测与复现" %}
    {% assign col_gov = topics | where: "column", "接入与治理" %}

    <div class="column-group" id="col-hot">
      <div class="column-head">
        <h3><span class="ch-num">壹</span>热点拆解</h3>
        <p>新工具、新功能、新事件，对实际使用有什么影响</p>
      </div>
      <div class="bento">
        {% for t in col_hot %}
        {% include topic-tile.html t=t %}
        {% endfor %}
        {% if col_hot.size == 0 %}
        <div class="placeholder-box slim">本栏目课题整理中</div>
        {% endif %}
      </div>
    </div>

    <div class="column-group" id="col-lab">
      <div class="column-head">
        <h3><span class="ch-num">贰</span>实测与复现</h3>
        <p>它到底能做什么、在哪里失败、控制措施是否有效</p>
      </div>
      <div class="bento">
        {% for t in col_lab %}
        {% include topic-tile.html t=t %}
        {% endfor %}
        {% if col_lab.size == 0 %}
        <div class="placeholder-box slim">本栏目课题整理中</div>
        {% endif %}
      </div>
    </div>

    <div class="column-group" id="col-gov">
      <div class="column-head">
        <h3><span class="ch-num">叁</span>接入与治理</h3>
        <p>企业应该怎样配置、评估和管理</p>
      </div>
      <div class="bento">
        {% for t in col_gov %}
        {% include topic-tile.html t=t %}
        {% endfor %}
        {% if col_gov.size == 0 %}
        <div class="placeholder-box slim">本栏目课题整理中</div>
        {% endif %}
      </div>
    </div>

    <div class="empty-result" id="empty-result" hidden>
      <div class="glyph">空</div>
      没有匹配的课题，换个关键词试试
    </div>

    {% if topics.size == 0 %}
    <div class="placeholder-box">
      <div class="glyph">墨 · 俠</div>
      研究课题正整理入库，首发内容即将上线
    </div>
    {% endif %}

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
  /* ---- 课题搜索：跨栏目过滤 ---- */
  var search = document.getElementById('topic-search');
  var empty = document.getElementById('empty-result');
  var groups = Array.prototype.slice.call(document.querySelectorAll('.column-group'));
  var tiles = Array.prototype.slice.call(document.querySelectorAll('.column-group .tile'));

  function norm(s) { return (s || '').toLowerCase().trim(); }

  function filterTiles(q) {
    var total = 0;
    tiles.forEach(function (t) {
      var hay = norm([t.getAttribute('data-title'), t.getAttribute('data-subtitle'),
                      t.getAttribute('data-keyword'), t.getAttribute('data-cat'),
                      (t.getAttribute('data-tags') || '').replace(/,/g, ' ')].join(' '));
      var show = !q || hay.indexOf(norm(q)) !== -1;
      t.style.display = show ? '' : 'none';
      if (show) total++;
    });
    groups.forEach(function (g) {
      var visible = g.querySelectorAll('.tile:not([style*="none"])').length;
      g.style.display = visible ? '' : 'none';
    });
    if (empty) empty.hidden = total !== 0;
  }

  if (search) {
    search.addEventListener('input', function () { filterTiles(search.value); });
    filterTiles('');
  }

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
