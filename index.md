---
layout: default
body_class: home-page
---
{% assign hero = site.data.editorial.hero %}
<header class="research-masthead" style="--hero-height: {{ hero.height | default: 350 }}px; --hero-feather: {{ hero.feather | default: 35 | times: 0.2857 }}%;">
  <img class="masthead-art" src="{{ hero.art | relative_url }}" width="1344" height="576" alt="{{ hero.alt | escape }}" fetchpriority="high">
  <div class="wrap">
    <p class="eyebrow">{{ hero.eyebrow | escape }}</p>
    <h1>{{ hero.title | escape }}</h1>
    <p class="masthead-purpose">{{ hero.purpose | escape }}</p>
    <p class="masthead-description">{{ hero.description | escape }}</p>
    <div class="masthead-bottom">
      <a class="author-line" href="{{ '/about/#qianli' | relative_url }}">{{ hero.author | escape }} <span>{{ hero.role | escape }}</span></a>
      <a class="text-link" href="{{ hero.action_url | relative_url }}">{{ hero.action_title | escape }} <span aria-hidden="true">→</span></a>
    </div>
  </div>
</header>
<div class="archive-strip"><div class="wrap"><span>研究档案</span><a href="{{ '/topics/' | relative_url }}"><b>{{ site.topics.size }}</b> 个课题</a><a href="{{ '/articles/' | relative_url }}"><b>{{ site.articles.size }}</b> 篇原创长文</a><a href="{{ '/resources/' | relative_url }}"><b>{{ site.resources.size }}</b> 条精选资料</a><a class="strip-rss" href="{{ '/feed/articles.xml' | relative_url }}">RSS 订阅 ↗</a></div></div>

{% assign section_number = 0 %}
{% for section in site.data.editorial.sections %}{% if section.visible %}
  {% assign section_number = section_number | plus: 1 %}
  {% case section.key %}
    {% when 'focus' %}{% include home/focus.html %}
    {% when 'articles' %}{% include home/articles.html %}
    {% when 'sources' %}{% include home/sources.html %}
    {% when 'news' %}{% include home/news.html %}
    {% when 'author' %}{% include home/author.html %}
  {% endcase %}
{% endif %}{% endfor %}
<script src="{{ '/assets/home-news.js' | relative_url }}" defer></script>
