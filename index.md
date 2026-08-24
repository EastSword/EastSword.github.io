---
layout: default
---
<div class="status-line">SYSTEM ONLINE · 全平台资源索引持续更新</div>

<section id="topics">
  <div class="section-title">// RESEARCH TOPICS · 研究话题</div>

  {% assign topics = site.topics | sort: date | reverse %}
  {% for t in topics %}
  <div class="topic-card">
    <h2><a href="{{ t.url | relative_url }}">{{ t.title }}</a></h2>
    <div class="sub">{{ t.subtitle }}</div>
    <div class="meta">
      {% if t.status == "published" %}
        <span class="badge published">已发布</span>
      {% elsif t.status == "publishing" %}
        <span class="badge publishing">发布中</span>
      {% else %}
        <span class="badge drafting">撰写中</span>
      {% endif %}
      <span>{{ t.date | date: "%Y-%m-%d" }}</span>
      {% if t.keyword %}<span>KEYWORD</span><span class="badge keyword">{{ t.keyword }}</span>{% endif %}
      {% assign link_count = t.links | size %}
      <span>{{ link_count }} PLATFORMS</span>
    </div>
  </div>
  {% endfor %}

  {% if topics.size == 0 %}
  <div class="placeholder-box">
    <div class="glyph">▓▒░</div>
    研究话题正整理入库，首发内容即将上线
  </div>
  {% endif %}
</section>

<section class="block" id="about" style="margin-top:72px;">
  <h2>ABOUT · 关于</h2>
  <div class="body">
    <p><strong>东方隐侠安全团队（DFYX-SEC）</strong>，一支专注于攻防前沿的安全研究团队。研究方向横跨 AI 安全（Agent / MCP / Skills 供应链）、身份安全（ITDR）、软件供应链三大领域，坚持「研究驱动、实战检验」——每个话题从第一性原理拆解，配真实事件与可落地的检测基线。</p>
    <p><strong>千里</strong>，团队创始人，安全 BP。深耕 Web 安全多年，当前主攻 AI Agent 时代的新攻击面。负责本站全部研究话题的选题与撰写。</p>
    <p>本站不按时间流更新，按<strong>研究主题</strong>组织：每个话题页聚合该研究在公众号、CSDN、FreeBuf、B站、知识大陆的全部形态入口与配套资产，地址持续修订。</p>
  </div>
</section>
