---
layout: default
body_class: home-page
---
<header class="research-masthead">
  <div class="wrap">
    <p class="eyebrow">DFYX-SEC / AI & SECURITY RESEARCH</p>
    <h1>东方隐侠安全团队</h1>
    <p class="masthead-purpose">研究 AI 如何安全地进入真实工作。</p>
    <p class="masthead-description">从身份、权限到执行边界，积累可核查的研究、工程方法与精选资料。</p>
    <div class="masthead-bottom">
      <a class="author-line" href="{{ '/about/#qianli' | relative_url }}">千里 <span>创始人 · 安全 BP · AI 安全研究</span></a>
      <a class="text-link" href="{{ '/topics/' | relative_url }}">进入研究课题 <span aria-hidden="true">→</span></a>
    </div>
  </div>
</header>
<div class="archive-strip"><div class="wrap"><span>研究档案</span><a href="{{ '/topics/' | relative_url }}"><b>{{ site.topics.size }}</b> 个课题</a><a href="{{ '/articles/' | relative_url }}"><b>{{ site.articles.size }}</b> 篇原创长文</a><a href="{{ '/resources/' | relative_url }}"><b>{{ site.resources.size }}</b> 条精选资料</a><a class="strip-rss" href="{{ '/feed/articles.xml' | relative_url }}">RSS 订阅 ↗</a></div></div>

{% assign focus = site.topics | where: "slug", site.data.editorial.focus.topic | first %}
{% if focus %}
<section class="editorial-section" aria-labelledby="focus-heading">
  <div class="wrap">
    <div class="editorial-heading"><div><p class="eyebrow">01 / IN FOCUS</p><h2 id="focus-heading">当前重点研究</h2></div><span class="quiet">AI Agent · 身份与执行边界</span></div>
    <div class="focus-layout">
      <article class="focus-story">
        <div class="content-meta"><span class="label-original">原创研究</span><span>{{ site.data.editorial.focus.evidence }}</span><span>更新 {{ focus.updated | date: "%Y-%m-%d" }}</span></div>
        <h3><a href="{{ focus.url | relative_url }}">{{ site.data.editorial.focus.title }}</a></h3>
        <p>{{ site.data.editorial.focus.summary }}</p>
        <a class="research-figure" href="{{ site.data.editorial.focus.article | relative_url }}"><img src="{{ site.data.editorial.focus.image | relative_url }}" alt="企业 Agent 安全控制架构：身份与策略控制面、四类执行边界、中央审计与响应" width="1600" height="1040"></a>
        <div class="story-links"><a class="text-link" href="{{ site.data.editorial.focus.article | relative_url }}">阅读完整研究 →</a><a href="{{ focus.url | relative_url }}#findings">结论与待验证事项 →</a></div>
      </article>
      <aside class="research-routes" aria-labelledby="routes-heading">
        <p class="eyebrow">START WITH A QUESTION</p><h3 id="routes-heading">从你关心的问题开始</h3>
        {% for route in site.data.editorial.routes %}<a class="route-row" href="{{ route.url | relative_url }}"><span class="route-index">0{{ forloop.index }}</span><div><span class="route-label">{{ route.label }}</span><h4>{{ route.question }}</h4><p>{{ route.description }}</p></div><span aria-hidden="true">↗</span></a>{% endfor %}
        <a class="text-link route-all" href="{{ '/topics/' | relative_url }}">全部研究课题 →</a>
      </aside>
    </div>
  </div>
</section>
{% endif %}
<section class="editorial-section section-muted" aria-labelledby="articles-heading"><div class="wrap">
  <div class="editorial-heading"><div><p class="eyebrow">02 / ORIGINAL WORK</p><h2 id="articles-heading">原创研究与实践</h2></div><a class="text-link" href="{{ '/articles/' | relative_url }}">全部文章 →</a></div>
  <div class="article-index">{% assign articles = site.articles | sort: "date" | reverse %}{% for a in articles limit: 4 %}
    <article class="article-index-row"><time datetime="{{ a.date | date: '%Y-%m-%d' }}">{{ a.date | date: "%m-%d" }}<span>{{ a.date | date: "%Y" }}</span></time><div><div class="content-meta"><span class="label-original">原创</span><span>{{ a.category }}</span><span>{{ a.author }} · {{ a.reading_time }} 分钟</span></div><h3><a href="{{ a.url | relative_url }}">{{ a.title }}</a></h3><p>{{ a.subtitle }}</p></div><a class="row-arrow" aria-label="阅读：{{ a.title | escape }}" href="{{ a.url | relative_url }}">↗</a></article>
  {% endfor %}</div>
</div></section>
<section class="editorial-section" aria-labelledby="sources-heading"><div class="wrap">
  <div class="editorial-heading"><div><p class="eyebrow">03 / READING DESK</p><h2 id="sources-heading">值得细读的外部资料</h2></div><a class="text-link" href="{{ '/resources/' | relative_url }}">精选资料库 →</a></div>
  <div class="source-preview">{% for source_id in site.data.editorial.featured_resources %}{% assign r = site.resources | where: "slug", source_id | first %}{% if r %}{% include resource-entry.html resource=r compact=true %}{% endif %}{% endfor %}</div>
</div></section>
<section class="editorial-section section-muted" aria-labelledby="news-heading"><div class="wrap">
  <div class="editorial-heading"><div><p class="eyebrow">04 / ON THE RADAR</p><h2 id="news-heading">安全动态</h2></div><a class="text-link" href="{{ '/news/' | relative_url }}">资讯归档 →</a></div>
  <p class="section-note">外部资讯 · 自动聚合，原文观点归原作者；不代表本站已完成复现。</p>
  <div class="news-list preview" id="home-news-list" aria-live="polite"><p class="feed-status">正在加载资讯…</p></div>
  <noscript><p><a href="{{ '/news/' | relative_url }}">查看安全资讯归档</a></p></noscript>
</div></section>
<section class="editorial-section author-section" aria-labelledby="author-heading"><div class="wrap author-band">
  <img src="{{ '/assets/logo-full.png' | relative_url }}" alt="东方隐侠团队标志" width="112" height="112" loading="lazy"><div><p class="eyebrow">QIANLI / EASTERN SWORD</p><h2 id="author-heading">千里 · 从业务现场出发</h2><p>安全 BP，东方隐侠创始人。长期研究 Web 安全，当前关注 AI 应用的身份、权限、供应链与审计。把实际问题写成研究，也把研究带回实际工作。</p><div class="story-links"><a class="text-link" href="{{ '/about/#qianli' | relative_url }}">关于千里与团队 →</a><a href="https://github.com/EastSword" target="_blank" rel="noopener">GitHub ↗</a><a href="{{ '/wall/' | relative_url }}">交流与纠错 →</a></div></div>
</div></section>
<script src="{{ '/assets/home-news.js' | relative_url }}" defer></script>
