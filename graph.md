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

    <div class="graph-frame">
      <div class="graph-cmdbar">
        <span class="cmd-prompt" aria-hidden="true">neo4j$</span>
        <div class="search-box graph-search">
          <input id="graph-search" type="search" aria-label="搜索知识图谱" autocomplete="off"
                 spellcheck="false"
                 placeholder="MATCH (t:课题)-[r]-(c:概念) RETURN t, r, c　·　输入关键词定位节点">
          <div id="graph-suggest" class="graph-suggest" hidden></div>
        </div>
        <span class="cmd-hint" aria-hidden="true">↵ 定位</span>
      </div>

      <div class="graph-body">
        <aside class="graph-sidebar" id="graph-sidebar">
          <div class="sb-card">
            <h4>Database information</h4>
            <div class="sb-kv"><span>Nodes</span><span id="sb-nodes">–</span></div>
            <div class="sb-kv"><span>Relationships</span><span id="sb-links">–</span></div>
            <div class="sb-kv"><span>Labels</span><span id="sb-labels">–</span></div>
          </div>
          <div class="sb-card">
            <h4>Node labels</h4>
            <div id="sb-node-labels"></div>
          </div>
          <div class="sb-card">
            <h4>Relationship types</h4>
            <div id="sb-rel-types"></div>
          </div>
          <div class="sb-card" id="sb-layers-card" hidden>
            <h4>概念分层 · 道法术器</h4>
            <div id="sb-layers"></div>
            <p class="ly-note">层级线（紫）：FOUNDS 奠基 · COVERS 涵盖<br>TARGETS 作用 · INSTANCE 实例</p>
          </div>
          <button id="graph-label-toggle" class="sb-toggle" type="button" aria-pressed="false">概念标签 · 悬停显示</button>
          <p class="sb-foot">单击节点查看详情 · 双击直达页面<br>悬停显示概念名 · 拖拽平移 · 按钮缩放</p>
        </aside>

        <div class="graph-view">
          <div id="graph-canvas" role="img" aria-label="以核心概念为中心的研究课题、文章与安全概念径向辐射关联图"></div>
          <div id="graph-fallback" class="graph-fallback" hidden></div>
          <div class="graph-zoom" role="group" aria-label="缩放控制">
            <button id="graph-zoom-in" type="button" aria-label="放大" title="放大">＋</button>
            <button id="graph-zoom-reset" type="button" aria-label="复位" title="复位缩放">⌂</button>
            <button id="graph-zoom-out" type="button" aria-label="缩小" title="缩小">－</button>
          </div>
          <div class="graph-statusbar" id="graph-statusbar"></div>
          <aside class="graph-inspector" id="graph-inspector" hidden></aside>
          <button id="sb-float-btn" class="sb-float" type="button" aria-expanded="false" aria-controls="graph-sidebar">☰ 图例</button>
        </div>
      </div>
    </div>

    <div class="graph-meta">
      <span id="graph-meta-time" class="graph-meta-item"></span>
      <span class="graph-meta-note">概念摘要经截断展示，完整知识图谱存于工作站内网，每周日自动提炼更新。</span>
    </div>
  </div>
</section>

<style>
/* ---------- 知识图谱页 · Neo4j Browser 布局 × 站点暗色主题（墨黑 + 青霓虹） ---------- */
#graph-page { padding-bottom: 90px; }
#graph-page .section-head { margin-top: 40px; }

.graph-frame {
  border: 1px solid rgba(61, 232, 201, .16);
  border-radius: 10px;
  overflow: hidden;
  background: #10161e;
  box-shadow: 0 18px 50px rgba(0, 0, 0, .6);
}

/* --- 顶部 Cypher 命令栏 --- */
.graph-cmdbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  background: rgba(10, 12, 16, .55);
  border-bottom: 1px solid rgba(61, 232, 201, .16);
}
.cmd-prompt {
  font-family: var(--mono);
  font-size: 13px;
  color: var(--teal-glow);
  white-space: nowrap;
  user-select: none;
}
.graph-search { position: relative; flex: 1; min-width: 0; }
.graph-search input {
  width: 100%;
  background: none;
  border: none;
  outline: none;
  color: var(--paper);
  font-family: var(--mono);
  font-size: 13px;
  letter-spacing: .3px;
  padding: 3px 0;
}
.graph-search input::placeholder { color: rgba(233, 228, 216, .35); }
.graph-search input:focus::placeholder { color: rgba(233, 228, 216, .22); }
.cmd-hint {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--paper-dim);
  border: 1px solid rgba(233, 228, 216, .14);
  border-radius: 5px;
  padding: 2px 8px;
  background: rgba(233, 228, 216, .05);
  white-space: nowrap;
  user-select: none;
}
.graph-suggest {
  position: absolute;
  top: calc(100% + 8px);
  left: 0; right: 0;
  z-index: 40;
  border: 1px solid rgba(61, 232, 201, .28);
  border-radius: 8px;
  background: rgba(18, 25, 33, .98);
  box-shadow: 0 14px 40px rgba(0, 0, 0, .55);
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
  letter-spacing: .3px;
}
.graph-suggest button:hover { background: rgba(61, 232, 201, .08); }
.graph-suggest .sg-kind {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 1px;
  padding: 1px 7px;
  border-radius: 4px;
  border: 1px solid rgba(233, 228, 216, .18);
  color: var(--paper-dim);
  flex-shrink: 0;
}

/* --- 主体：侧栏 + 画布 --- */
.graph-body { display: flex; position: relative; }
.graph-sidebar {
  width: 232px;
  flex-shrink: 0;
  background: rgba(10, 12, 16, .4);
  border-right: 1px solid rgba(61, 232, 201, .16);
  padding: 16px 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
  max-height: min(74vh, 720px);
}
.sb-card h4 {
  margin: 0 0 8px;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--paper-dim);
}
.sb-kv {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--paper-dim);
  padding: 5px 4px;
  border-bottom: 1px solid rgba(233, 228, 216, .08);
}
.sb-kv:last-child { border-bottom: none; }
.sb-kv span:last-child { color: var(--paper); }

/* 节点类型图例：粉彩色块（chip）+ 计数 */
.sb-row {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 5px 4px;
  background: none;
  border: none;
  border-bottom: 1px solid rgba(233, 228, 216, .08);
  border-radius: 0;
  color: var(--paper);
  font-size: 12.5px;
  cursor: pointer;
  text-align: left;
  transition: opacity .15s;
}
.sb-row:last-child { border-bottom: none; }
.sb-row:hover { background: rgba(61, 232, 201, .07); }
.sb-row.off { opacity: .5; }
.sb-row.off .sb-chip {
  background: transparent !important;
  box-shadow: inset 0 0 0 1.5px rgba(233, 228, 216, .3);
  color: var(--paper-dim);
}
.sb-chip {
  display: inline-block;
  max-width: 132px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11.5px;
  line-height: 1.5;
  color: #2A2C34;
  flex-shrink: 0;
}
.sb-line {
  width: 18px;
  height: 2px;
  border-radius: 1px;
  background: rgba(233, 228, 216, .35);
  flex-shrink: 0;
}
.sb-row.off .sb-line { background: rgba(233, 228, 216, .15); }
.sb-count { margin-left: auto; color: var(--paper-dim); font-size: 11px; font-family: var(--mono); }

/* 道法术器层级图例行（紫四档圆徽 + 说明 + 计数） */
.sb-layer-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 4px;
  border-bottom: 1px solid rgba(233, 228, 216, .08);
  font-size: 12.5px;
  color: var(--paper);
}
.sb-layer-row:last-of-type { border-bottom: none; }
.ly-badge {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #FFFFFF;
  font-size: 11.5px;
  font-weight: 700;
  flex-shrink: 0;
}
.ly-name { flex: 1; }
.ly-note {
  margin: 8px 0 0;
  font-family: var(--mono);
  font-size: 9.5px;
  line-height: 1.9;
  color: var(--paper-dim);
  letter-spacing: .3px;
}
.sb-toggle {
  font-family: var(--mono);
  font-size: 11.5px;
  letter-spacing: .5px;
  color: var(--teal-glow);
  background: transparent;
  border: 1px solid rgba(61, 232, 201, .35);
  border-radius: 7px;
  padding: 7px 10px;
  cursor: pointer;
  transition: background .15s;
}
.sb-toggle:hover { background: rgba(61, 232, 201, .1); }
.sb-toggle.active { background: rgba(61, 232, 201, .18); }
.sb-foot {
  margin: 0;
  font-family: var(--mono);
  font-size: 10.5px;
  line-height: 2;
  color: var(--paper-dim);
  letter-spacing: .5px;
}

.graph-view { position: relative; flex: 1; min-width: 0; background: #0b1418; }
#graph-canvas { width: 100%; height: min(74vh, 720px); min-height: 480px; background: #0b1418; }

/* --- 画布缩放控件（左下角竖排） --- */
.graph-zoom {
  position: absolute;
  left: 12px;
  bottom: 10px;
  z-index: 6;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.graph-zoom button {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-size: 15px;
  color: var(--paper-dim);
  background: rgba(16, 22, 30, .85);
  border: 1px solid rgba(61, 232, 201, .28);
  border-radius: 6px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, .4);
  transition: border-color .15s, color .15s;
}
.graph-zoom button:hover { border-color: var(--teal-glow); color: var(--teal-glow); }

.graph-statusbar {
  position: absolute;
  right: 12px;
  bottom: 10px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--paper-dim);
  background: rgba(16, 22, 30, .85);
  border: 1px solid rgba(61, 232, 201, .2);
  border-radius: 4px;
  padding: 4px 10px;
  pointer-events: none;
  z-index: 5;
}

.graph-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0b1418;
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
  color: var(--teal-glow);
  opacity: .3;
  margin-bottom: 8px;
}

/* --- 右侧节点 Inspector --- */
.graph-inspector {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 300px;
  max-height: calc(100% - 26px);
  overflow-y: auto;
  background: rgba(18, 25, 33, .97);
  border: 1px solid rgba(61, 232, 201, .28);
  border-radius: 8px;
  padding: 16px 16px 14px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, .55);
  z-index: 10;
  animation: insp-in .18s ease-out;
}
@keyframes insp-in {
  from { opacity: 0; transform: translateX(10px); }
  to   { opacity: 1; transform: none; }
}
@media (prefers-reduced-motion: reduce) {
  .graph-inspector { animation: none; }
}
.insp-head { display: flex; align-items: flex-start; gap: 10px; }
.insp-dot { width: 13px; height: 13px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }
.insp-name {
  flex: 1;
  font-size: 15px;
  font-weight: 700;
  color: var(--paper);
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.insp-close {
  background: none;
  border: none;
  color: var(--paper-dim);
  font-size: 17px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 4px;
  flex-shrink: 0;
}
.insp-close:hover { color: var(--paper); }
.insp-labels { display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0 4px; }
.insp-badge {
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: .5px;
  padding: 2px 8px;
  border-radius: 20px;
  background: rgba(233, 228, 216, .07);
  color: var(--paper-dim);
}
.insp-badge.type-badge { color: var(--gold-bright); font-weight: 700; }
.insp-sec {
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--paper-dim);
  margin: 14px 0 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(233, 228, 216, .08);
}
.insp-prop {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  font-family: var(--mono);
  font-size: 11.5px;
  padding: 2.5px 0;
}
.insp-prop .k { color: var(--paper-dim); flex-shrink: 0; }
.insp-prop .v { color: var(--paper); text-align: right; overflow-wrap: anywhere; }
.insp-summary {
  font-size: 12.5px;
  line-height: 1.8;
  color: #B6BDC7;
}
.insp-center {
  display: block;
  width: 100%;
  margin-top: 14px;
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: .5px;
  color: var(--teal-glow);
  background: transparent;
  border: 1px solid rgba(61, 232, 201, .35);
  border-radius: 6px;
  padding: 8px;
  cursor: pointer;
  text-align: center;
  transition: background .15s ease, border-color .15s ease;
}
.insp-center:hover { background: rgba(61, 232, 201, .12); border-color: var(--teal-glow); }
.insp-open {
  display: block;
  width: 100%;
  margin-top: 12px;
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: .5px;
  color: var(--teal-glow);
  background: rgba(61, 232, 201, .14);
  border: 1px solid rgba(61, 232, 201, .45);
  border-radius: 6px;
  padding: 8px;
  cursor: pointer;
  text-align: center;
  text-decoration: none;
  transition: background .15s ease, border-color .15s ease;
}
.insp-open:hover { background: rgba(61, 232, 201, .24); border-color: var(--teal-glow); }
.insp-rel {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  background: none;
  border: none;
  border-radius: 4px;
  padding: 4px 6px;
  cursor: pointer;
  text-align: left;
  font-size: 12px;
  color: var(--paper);
}
.insp-rel:hover { background: rgba(233, 228, 216, .07); }
.insp-rel .r-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.insp-rel .r-name { flex: 1; overflow-wrap: anywhere; line-height: 1.45; }
.insp-rel .r-kind { font-family: var(--mono); font-size: 9.5px; color: var(--paper-dim); flex-shrink: 0; }

.sb-float { display: none; }

/* --- 底部 meta 条 --- */
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

/* --- 响应式：小屏侧栏收起为浮层 --- */
@media (max-width: 960px) {
  .graph-sidebar {
    position: absolute;
    top: 10px; left: 10px;
    z-index: 20;
    width: 214px;
    max-height: calc(100% - 20px);
    background: rgba(18, 25, 33, .98);
    border: 1px solid rgba(61, 232, 201, .28);
    border-radius: 8px;
    display: none;
    box-shadow: 0 16px 44px rgba(0, 0, 0, .6);
  }
  .graph-sidebar.open { display: flex; }
  .sb-float {
    display: block;
    position: absolute;
    top: 10px; left: 10px;
    z-index: 15;
    font-family: var(--mono);
    font-size: 11.5px;
    color: var(--paper);
    background: rgba(16, 22, 30, .9);
    border: 1px solid rgba(61, 232, 201, .28);
    border-radius: 6px;
    padding: 6px 11px;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, .4);
  }
  .sb-float[aria-expanded="true"] { color: var(--teal-glow); border-color: rgba(61, 232, 201, .5); }
  .graph-inspector {
    top: auto; right: 0; left: 0; bottom: 0;
    width: auto;
    max-height: 46%;
    border-radius: 8px 8px 0 0;
    border-left: none; border-right: none; border-bottom: none;
    animation: insp-up .2s ease-out;
  }
  @keyframes insp-up {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: none; }
  }
  #graph-canvas { height: 68vh; min-height: 430px; }
  .cmd-hint { display: none; }
}
</style>

<script src="/assets/echarts.min.js"></script>
<script src="/assets/graph.js"></script>
