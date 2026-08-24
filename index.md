---
layout: default
---
<section id="topics">
  <h1 style="font-size:24px;margin-bottom:8px;">研究话题</h1>
  <p style="color:var(--text-dim);font-size:14.5px;margin-bottom:28px;">
    每个话题是一份持续更新的研究，全平台各形态入口聚合在话题页内。
  </p>

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
      {% if t.keyword %}<span>关键词</span><span class="badge keyword">{{ t.keyword }}</span>{% endif %}
      {% assign link_count = t.links | size %}
      <span>{{ link_count }} 个平台入口</span>
    </div>
  </div>
  {% endfor %}
</section>

<section class="block" id="about" style="margin-top:64px;">
  <h2>关于</h2>
  <div class="body">
    <p><strong>千里</strong>，东方隐侠安全团队成员。安全 BP，深耕 Web 安全，当前主攻方向：<strong>AI 安全（Agent / MCP / Skills 供应链）、身份安全（ITDR）、软件供应链</strong>。</p>
    <p>这个站点不按时间流更新——它按<strong>研究主题</strong>组织。每个话题页聚合该研究在公众号、CSDN、FreeBuf、B站、知识大陆的全部形态入口与配套资产，地址失效或形态新增时持续修订。千里之堤，溃于蚁穴；本站专注找那些蚁穴。</p>
  </div>
</section>
