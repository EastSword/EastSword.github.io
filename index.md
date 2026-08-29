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
      <h2>四大板块</h2>
      <p class="desc">研究话题纵深拆解，安全资讯每日同步内网情报源，江湖留名汇聚同行足迹。</p>
    </div>
    <div class="modules">
      <a class="module m-teal" href="{{ '/topics/' | relative_url }}">
        <div class="glyph">研</div>
        <div class="m-title">研究话题</div>
        <div class="m-desc">每个话题是一次完整研究：第一性原理拆解 + 真实事件 + 检测基线</div>
        <div class="m-meta">{{ site.topics | size }} 个课题 · 持续修订</div>
      </a>
      <a class="module m-gold" href="{{ '/news/' | relative_url }}">
        <div class="glyph">讯</div>
        <div class="m-title">安全资讯</div>
        <div class="m-desc">内网情报聚合服务直连，覆盖全球安全源与 AI 安全源，每日自动同步</div>
        <div class="m-meta">{% if site.data.news %}{{ site.data.news.items | size }} 条 · {{ site.data.news.generated_at }} 更新{% else %}情报源接入中{% endif %}</div>
      </a>
      <a class="module m-purple" href="{{ '/wall/' | relative_url }}">
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

<!-- NEWS PREVIEW -->
<section id="news-preview">
  <div class="wrap">
    <div class="section-head">
      <div class="num">03 / INTEL</div>
      <h2>最新安全资讯</h2>
      <p class="desc">每日 10:00 自动同步内网情报聚合服务（安全源 83 个，含 CISA / Mandiant / FreeBuf 等）。</p>
    </div>
    {% if site.data.news %}
    <div class="news-list preview">
      {% for n in site.data.news.items limit: 6 %}
      <a class="news-item" href="{{ n.url }}" target="_blank" rel="noopener">
        <span class="news-date">{{ n.published_date }}</span>
        <span class="badge {% if n.category == 'AI安全' %}cat-ai{% else %}cat-sec{% endif %}">{{ n.category }}</span>
        <span class="news-title">{{ n.title }}</span>
        <span class="news-source">{{ n.source }}</span>
      </a>
      {% endfor %}
    </div>
    <div class="more-link"><a href="{{ '/news/' | relative_url }}">进入资讯频道 →</a></div>
    {% else %}
    <div class="placeholder-box">
      <div class="glyph">讯</div>
      情报源接入中，运行 scripts/sync_news.py 首次同步
    </div>
    {% endif %}
  </div>
</section>
