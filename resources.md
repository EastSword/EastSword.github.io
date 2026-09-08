---
layout: default
title: 精选资料
permalink: /resources/
abstract: AI 安全、身份与供应链的外部资料索引：原始规范、工程实践、标准框架与社区清单，附来源、推荐理由与关联研究。
---
<section class="editorial-section library-page"><div class="wrap">
  <div class="editorial-heading"><div><p class="eyebrow">READING DESK / CURATED SOURCES</p><h1>精选资料</h1></div><a class="text-link" href="{{ '/topics/' | relative_url }}">研究课题 →</a></div>
  <p class="page-intro">规范提供边界，研究提供证据。收录 AI 应用、身份与供应链的原始资料，并记录它们与本站研究的关系。</p>
  <form class="library-filters" role="search" onsubmit="return false">
    <label class="search-field" for="resource-search">搜索资料<input id="resource-search" type="search" placeholder="标题、作者或关键词，例如 MCP" autocomplete="off"></label>
    <label for="resource-type">资料类型<select id="resource-type"><option value="">全部类型</option>{% assign types = site.resources | map: "type" | uniq | sort %}{% for type in types %}<option value="{{ type | escape }}">{{ type }}</option>{% endfor %}</select></label>
    <label for="resource-topic">关联课题<select id="resource-topic"><option value="">全部课题</option>{% for t in site.topics %}{% assign count = site.resources | where_exp: "r", "r.topics contains t.slug" | size %}{% if count > 0 %}<option value="{{ t.slug }}">{{ t.title }}</option>{% endif %}{% endfor %}</select></label>
    <button class="reset-filter" type="reset">重置筛选</button>
  </form>
  <div class="library-summary"><span id="resource-count" role="status">{{ site.resources.size }} 条资料</span><span>外部精选 · 保留原文链接</span></div>
  <div class="source-library">{% assign resources = site.resources | sort: "date" | reverse %}{% for r in resources %}{% include resource-entry.html resource=r %}{% endfor %}</div>
  <p id="resource-empty" class="empty-result" hidden>没有匹配的资料。</p>
  <noscript><p class="section-note">以下为全部资料，筛选需要启用 JavaScript。</p></noscript>
  <div class="editorial-policy"><h2>收录与修订</h2><p>外部资料以原文链接和本站摘要呈现，观点与著作权归原作者。收录日期不等于最近核验日期；规范适用版本以条目及原文为准。本站的研究判断与验证范围见关联课题。</p><a class="text-link" href="{{ '/wall/' | relative_url }}">推荐资料或反馈失效链接 →</a></div>
</div></section>
<script src="{{ '/assets/resources.js' | relative_url }}" defer></script>
