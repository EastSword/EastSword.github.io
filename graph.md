---
layout: default
title: 知识图谱
permalink: /graph/
description: 研究课题、原创文章与安全概念的知识关联网络——工作站知识库的公开切片。
sitemap: true
---
<section id="graph-page">
  <div class="wrap wrap-wide">
    {% include section-head.html key="graph" %}

    <div class="graph-toolbar">
      <div class="search-box graph-search">
        <span class="icon">⌕</span>
        <input id="graph-search" type="search" aria-label="搜索知识图谱" placeholder="搜索课题 / 文章 / 概念…" autocomplete="off">
        <div id="graph-suggest" class="graph-suggest" hidden></div>
      </div>
      <button id="graph-label-toggle" class="chip" type="button" aria-pressed="false">显示全部概念标签</button>
      <span class="graph-hint">拖拽平移 · 滚轮缩放 · 悬停聚焦邻接 · 点击课题与文章直达</span>
    </div>

    <div class="graph-stage">
      <div id="graph-canvas" role="img" aria-label="研究课题、文章与安全概念的关联网络力导向图"></div>
      <div id="graph-fallback" class="graph-fallback" hidden></div>
    </div>

    <div class="graph-meta">
      <span id="graph-meta-counts" class="graph-meta-item"></span>
      <span id="graph-meta-time" class="graph-meta-item"></span>
      <span class="graph-meta-note">概念摘要经截断展示，完整知识图谱存于工作站内网，每周日自动提炼更新。</span>
    </div>
  </div>
</section>

<style>
/* ---------- 知识图谱页 ---------- */
#graph-page { padding-bottom: 90px; }
#graph-page .section-head { margin-top: 40px; }
.graph-toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin: 8px 0 16px;
}
.graph-search { position: relative; flex: 1; min-width: 240px; max-width: 420px; }
.graph-suggest {
  position: absolute;
  top: calc(100% + 6px);
  left: 0; right: 0;
  z-index: 30;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(14, 17, 22, .96);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 14px 40px rgba(0, 0, 0, .45);
  overflow: hidden;
}
.graph-suggest button {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  color: var(--paper);
  font-size: 13px;
  letter-spacing: .5px;
}
.graph-suggest button:hover { background: rgba(61, 232, 201, .07); }
.graph-suggest .sg-kind {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 1px;
  padding: 1px 7px;
  border-radius: 4px;
  border: 1px solid var(--line);
  color: var(--paper-dim);
  flex-shrink: 0;
}
.graph-hint {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 1px;
  color: var(--paper-dim);
  opacity: .75;
  margin-left: auto;
}
.graph-stage {
  position: relative;
  border: 1px solid var(--line);
  border-radius: 14px;
  background:
    radial-gradient(ellipse 60% 70% at 30% 40%, rgba(61, 232, 201, .05), transparent 70%),
    radial-gradient(ellipse 50% 60% at 75% 65%, rgba(167, 139, 250, .05), transparent 70%),
    var(--card);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  overflow: hidden;
}
#graph-canvas { width: 100%; height: min(74vh, 720px); min-height: 480px; }
.graph-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--paper-dim);
  font-size: 14px;
  letter-spacing: 1px;
  text-align: center;
  padding: 24px;
  line-height: 2;
}
.graph-fallback .glyph {
  display: block;
  font-family: var(--serif);
  font-size: 42px;
  color: var(--gold);
  opacity: .35;
  margin-bottom: 8px;
}
.graph-meta {
  display: flex;
  gap: 22px;
  flex-wrap: wrap;
  align-items: baseline;
  margin-top: 16px;
  font-family: var(--mono);
  font-size: 11.5px;
  letter-spacing: 1px;
  color: var(--paper-dim);
}
.graph-meta-item { color: var(--teal-glow); opacity: .9; }
.graph-meta-note { opacity: .7; }
@media (max-width: 720px) {
  .graph-hint { display: none; }
  #graph-canvas { height: 66vh; min-height: 420px; }
}
</style>

<script src="/assets/echarts.min.js"></script>
<script src="/assets/graph.js"></script>
