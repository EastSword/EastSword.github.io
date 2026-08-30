---
layout: default
title: 技术文章
permalink: /articles/
---
<section id="articles">
  <div class="wrap">
    <div class="section-head">
      <div class="num">02 / ARTICLES</div>
      <h2>技术文章</h2>
      <p class="desc">研究课题的完整版长文：完整攻击面测量、全部提取路径、实测证据与防御基线，先于全平台首发或同步刊登于此。</p>
    </div>

    {% assign articles = site.articles | sort: date | reverse %}
    {% if articles.size > 0 %}
    <div class="bento">
      {% for a in articles %}
      <a class="tile article-tile" href="{{ a.url | relative_url }}">
        <div class="row1">
          {% if a.category %}<span class="badge cat-badge">{{ a.category }}</span>{% endif %}
          <h3>{{ a.title }}</h3>
          <span class="arrow">→</span>
        </div>
        <div class="row2">
          <span>{{ a.subtitle }}</span>
        </div>
        <div class="row3">
          <span>{{ a.date | date: "%Y-%m-%d" }}</span>
          <span class="dot">·</span>
          <span>阅读约 {{ a.reading_time }} 分钟</span>
          {% if a.updated and a.updated != a.date %}
          <span class="dot">·</span>
          <span>修订 {{ a.updated | date: "%m-%d" }}</span>
          {% endif %}
        </div>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="placeholder-box">
      <div class="glyph">文</div>
      文章模块已就绪，运行 scripts/publish_article.py 发布第一篇
    </div>
    {% endif %}
  </div>
</section>

<style>
.article-tile .row3 {
  margin-top: 10px;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--paper-dim);
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
