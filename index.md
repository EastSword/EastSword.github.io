---
layout: default
---
<!-- HERO -->
<section class="hero">
  <div class="bg"></div>
  <div class="veil"></div>
  <div class="wrap">
    <div class="kicker">DFYX-SEC · EASTERN RONIN SECURITY</div>
    <h1>
      <span class="teal">追踪攻击面的</span><br>
      <span class="gold">每一次迁移</span>
    </h1>
    <p class="lead">
      从 Web 安全到 AI Agent 时代，攻击者换了衣裳，走的是同一扇窗。东方隐侠安全团队以研究话题为单位，持续拆解身份、供应链与 AI 安的新战场。
    </p>
    <div class="cta">
      <a class="primary" href="#topics">进入研究话题</a>
      <a class="ghost" href="#about">关于团队</a>
    </div>
  </div>
  <div class="scroll">SCROLL ▾</div>
</section>

<!-- TOPICS -->
<section id="topics">
  <div class="wrap">
    <div class="section-head">
      <div class="num">01 / RESEARCH</div>
      <h2>研究话题</h2>
      <p class="desc">每个话题是一次完整的研究：从第一性原理拆解，配真实事件与可落地的检测基线，全平台形态入口聚合于话题页内，持续修订。</p>
    </div>

    {% assign topics = site.topics | sort: date | reverse %}
    {% for t in topics %}
    <a class="tile" href="{{ t.url | relative_url }}">
      <div class="row1">
        {% if t.status == "published" %}
          <span class="badge published">已发布</span>
        {% elsif t.status == "publishing" %}
          <span class="badge publishing">发布中</span>
        {% else %}
          <span class="badge drafting">撰写中</span>
        {% endif %}
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
      </div>
    </a>
    {% endfor %}

    {% if topics.size == 0 %}
    <div class="placeholder-box">
      <div class="glyph">墨 · 俠</div>
      研究话题正整理入库，首发内容即将上线
    </div>
    {% endif %}
  </div>
</section>

<!-- ABOUT -->
<section id="about">
  <div class="wrap">
    <div class="about">
      <img class="team-logo" src="{{ '/assets/logo-full.png' | relative_url }}" alt="东方隐侠安全团队">
      <h2>关于 <span>东方隐侠</span></h2>
      <p><strong>东方隐侠安全团队（DFYX-SEC）</strong>，专注于攻防前沿的安全研究团队。研究方向横跨 AI 安全（Agent / MCP / Skills 供应链）、身份安全（ITDR）、软件供应链三大领域，坚持「研究驱动、实战检验」——每个话题从第一性原理拆解，配真实事件与可落地的检测基线。</p>
      <p><strong>千里</strong>，团队创始人，安全 BP。深耕 Web 安全多年，当前主攻 AI Agent 时代的新攻击面，负责本站全部研究话题的选题与撰写。</p>
      <p>本站不按时间流更新，按<strong>研究主题</strong>组织：每个话题页聚合该研究在公众号、CSDN、FreeBuf、B站、知识大陆的全部形态入口与配套资产，地址持续修订。</p>
    </div>
  </div>
</section>
