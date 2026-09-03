---
layout: default
---
<!-- HERO -->
<section class="hero">
  <div class="bg"></div>
  <div class="veil"></div>
  <div class="wrap">
    <div class="kicker">DFYX-SEC · Eastern Sword Cyber Security</div>
    <h1>
      <span class="teal">追踪攻击面的</span><br>
      <span class="gold">每一次迁移</span>
    </h1>
    <p class="lead">
      从 Web 安全到 AI Agent 时代，攻击者换了兵器，攻的仍是同一处命门。东方隐侠安全团队以研究话题为脉络，逐一拆解身份、供应链、AI 安全三大战场上的攻击路径。
    </p>
    <div class="cta">
      <a class="primary" href="{{ '/topics/' | relative_url }}">进入研究话题</a>
      <a class="ghost" href="{{ '/news/' | relative_url }}">今日安全资讯</a>
    </div>
  </div>
  <div class="scroll">SCROLL ▾</div>
</section>

<!-- MODULES -->
<section id="modules">
  <div class="wrap">
    <div class="section-head">
      <div class="num">00 / SECTORS</div>
      <h2>五大板块</h2>
      <p class="desc">研究话题纵深拆解，安全资讯每日同步内网情报源，兵器谱收录试炼过的工具，江湖留名汇聚同行足迹。</p>
    </div>
    <div class="modules">
      <a class="module m-teal" href="{{ '/topics/' | relative_url }}">
        <div class="glyph">研</div>
        <div class="m-title">研究话题</div>
        <div class="m-desc">每个话题是一次完整研究：第一性原理拆解 + 真实事件 + 检测基线</div>
        <div class="m-meta">{{ site.topics | size }} 个课题 · {{ site.articles | size }} 篇长文</div>
      </a>
      <a class="module m-gold" href="{{ '/news/' | relative_url }}">
        <div class="glyph">讯</div>
        <div class="m-title">安全资讯</div>
        <div class="m-desc">内网情报聚合服务直连，覆盖全球安全源与 AI 安全源，每日自动同步</div>
        <div class="m-meta">{% if site.data.news %}{{ site.data.news.items | size }} 条 · {{ site.data.news.generated_at }} 更新{% else %}情报源接入中{% endif %}</div>
      </a>
      <a class="module m-purple" href="{{ '/tools/' | relative_url }}">
        <div class="glyph">兵</div>
        <div class="m-title">兵器谱</div>
        <div class="m-desc">AI 与安全双修的兵器库，逐一试炼后收录：测绘、情报、AI 攻防</div>
        <div class="m-meta">首录 FOFA / Shodan · 持续入库</div>
      </a>
      <a class="module m-gold" href="{{ '/wall/' | relative_url }}">
        <div class="glyph">俠</div>
        <div class="m-title">江湖留名</div>
        <div class="m-desc">以 GitHub 身份签下你的 ID 和一句话，签名实时上墙，支持表情回应</div>
        <div class="m-meta">路过即缘分</div>
      </a>
      <a class="module m-teal" href="{{ '/about/' | relative_url }}">
        <div class="glyph">盟</div>
        <div class="m-title">关于团队</div>
        <div class="m-desc">AI 安全 / 身份安全 / 软件供应链三大方向，联系与合作入口</div>
        <div class="m-meta">团队微信 / 视频号 / 公众号</div>
      </a>
    </div>
  </div>
</section>

<!-- TOPICS PREVIEW -->
<section id="topics-preview">
  <div class="wrap">
    <div class="section-head">
      <div class="num">01 / RESEARCH</div>
      <h2>最新研究话题</h2>
      <p class="desc">全平台形态入口聚合于话题页内：公众号、CSDN、B站、视频号一站直达。</p>
    </div>
    <div class="bento">
      {% assign topics = site.topics | sort: date | reverse %}
      {% for t in topics limit: 3 %}
      {% assign t_tags = t.tags | join: "," %}
      <a class="tile" href="{{ t.url | relative_url }}"
         data-title="{{ t.title | escape }}" data-tags="{{ t_tags }}">
        <div class="row1">
          {% if t.status == "published" %}
            <span class="badge published">已发布</span>
          {% elsif t.status == "publishing" %}
            <span class="badge publishing">发布中</span>
          {% else %}
            <span class="badge drafting">撰写中</span>
          {% endif %}
          {% if t.category %}<span class="badge cat-badge">{{ t.category }}</span>{% endif %}
          <h3>{{ t.title }}</h3>
          <span class="arrow">→</span>
        </div>
        <div class="row2">
          <span>{{ t.subtitle }}</span>
          <span class="dot">·</span>
          <span>{{ t.date | date: "%Y-%m-%d" }}</span>
        </div>
      </a>
      {% endfor %}
    </div>
    <div class="more-link"><a href="{{ '/topics/' | relative_url }}">查看全部课题 →</a></div>
  </div>
</section>

<!-- ARTICLES PREVIEW -->
{% assign articles = site.articles | sort: date | reverse %}
{% if articles.size > 0 %}
<section id="articles-preview">
  <div class="wrap">
    <div class="section-head">
      <div class="num">02 / ARTICLES</div>
      <h2>最新技术文章</h2>
      <p class="desc">研究课题的完整版长文，先于全平台首发或同步刊登于此。</p>
    </div>
    <div class="bento">
      {% for a in articles limit: 3 %}
      <a class="tile" href="{{ a.url | relative_url }}">
        <div class="row1">
          {% if a.category %}<span class="badge cat-badge">{{ a.category }}</span>{% endif %}
          <h3>{{ a.title }}</h3>
          <span class="arrow">→</span>
        </div>
        <div class="row2">
          <span>{{ a.subtitle }}</span>
          <span class="dot">·</span>
          <span>阅读约 {{ a.reading_time }} 分钟</span>
        </div>
      </a>
      {% endfor %}
    </div>
    <div class="more-link"><a href="{{ '/articles/' | relative_url }}">全部文章 →</a></div>
  </div>
</section>
{% endif %}

<!-- NEWS PREVIEW -->
<section id="news-preview">
  <div class="wrap">
    <div class="section-head">
      <div class="num">03 / INTEL</div>
      <h2>最新安全资讯</h2>
      <p class="desc">内网情报聚合服务直连（安全源 83 个，含 CISA / Mandiant / FreeBuf 等），全量归档于独立仓库，可关键词检索全部历史。</p>
    </div>
    <div class="news-list preview" id="home-news-list"></div>
    <div class="more-link"><a href="{{ '/news/' | relative_url }}">进入资讯频道 · 全量检索 →</a></div>
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
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : '#'; }

  fetch(BASE + '/feed.json').then(function (r) { return r.json(); }).then(function (d) {
    var box = document.getElementById('home-news-list');
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
    box.innerHTML = html;
  }).catch(function () {});

  fetch(BASE + '/index.json').then(function (r) { return r.json(); }).then(function (d) {
    var m = document.getElementById('news-module-meta');
    if (m) m.textContent = '全量归档 ' + d.total + ' 条 · ' + d.months.length + ' 个月 · 每日同步';
  }).catch(function () {});
})();
</script>
