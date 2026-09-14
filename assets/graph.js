/* graph.js — 知识图谱页渲染
 * 数据源 /assets/graph/graph-data.json（kb_distill.py 每周日生成）。
 * 节点四类：课题（暗金）/ 文章（青）/ 概念（紫）/ 实践（红）。
 */
(function () {
  'use strict';

  var canvas = document.getElementById('graph-canvas');
  var fallback = document.getElementById('graph-fallback');
  if (!canvas) return;

  function showFallback(msg) {
    if (!fallback) return;
    fallback.innerHTML = '<span class="glyph">图</span>' + msg;
    fallback.hidden = false;
  }

  if (typeof echarts === 'undefined') {
    showFallback('可视化组件加载失败，请刷新重试。');
    return;
  }

  /* ---- 类型与关系元数据（对齐站点 CSS 变量色板） ---- */
  var TYPE_META = {
    topic:    { label: '研究课题', color: '#d4af6a' },
    article:  { label: '原创文章', color: '#3de8c9' },
    concept:  { label: '安全概念', color: '#a78bfa' },
    practice: { label: '实践反哺', color: '#ff4d6d' }
  };
  var LINK_META = {
    belongs: { label: '文章归属', color: 'rgba(61, 232, 201, .55)',  width: 1.6 },
    core:    { label: '领域核心', color: 'rgba(212, 175, 106, .32)', width: 1.0 },
    tag:     { label: '显式标签', color: 'rgba(61, 232, 201, .45)',  width: 1.3 },
    rel:     { label: '概念关联', color: 'rgba(167, 139, 250, .32)', width: 1.0 },
    applies: { label: '实践应用', color: 'rgba(255, 77, 109, .45)',  width: 1.3 }
  };
  var CONCEPT_LABEL_DEGREE = 150;  // 概念标签默认显示的连接度门槛

  /* ---- 拉取数据 ---- */
  var controller = new AbortController();
  var timeout = setTimeout(function () { controller.abort(); }, 10000);

  fetch('/assets/graph/graph-data.json', { signal: controller.signal })
    .then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    })
    .then(function (data) { clearTimeout(timeout); render(data); })
    .catch(function () {
      clearTimeout(timeout);
      showFallback('图谱数据暂时无法加载，请稍后重试。');
    });

  /* ---- 渲染 ---- */
  var chart = null;
  var nodeIndex = {};    // name -> dataIndex
  var adjacency = {};    // name -> [dataIndex]
  var allConcepts = false;

  function conceptSize(degree) {
    var d = Number(degree) || 0;
    return Math.max(12, Math.min(26, 11 + d / 34));
  }

  function tooltipHtml(p) {
    var d = p.data, meta = TYPE_META[d.kind];
    if (!meta) return '';
    var head = '<div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:2px;color:' +
               meta.color + '">' + meta.label +
               (d.level ? ' · ' + d.level : '') +
               (d.status ? ' · ' + d.status : '') + '</div>';
    var body = '<div style="font-size:14px;font-weight:700;margin:4px 0;color:#e9e4d8">' + d.name + '</div>';
    if (d.summary) {
      body += '<div style="max-width:300px;font-size:12px;line-height:1.7;color:#b9b3a4">' + d.summary + '</div>';
    }
    if (d.degree != null) {
      body += '<div style="margin-top:4px;font-size:11px;color:#8d8778">知识库连接度 ' + d.degree + '</div>';
    }
    if (d.url) {
      body += '<div style="margin-top:6px;font-size:11px;color:#3de8c9">点击进入页面 →</div>';
    }
    return head + body;
  }

  function buildOption(data, labelAll) {
    var nodes = [], links = [];
    var idToName = {};
    var i, n;
    for (i = 0; i < data.nodes.length; i++) {
      idToName[data.nodes[i].id] = data.nodes[i].name;
    }
    for (i = 0; i < data.nodes.length; i++) {
      n = data.nodes[i];
      var item = {
        name: n.name, kind: n.type, id: n.id,
        summary: n.summary || '', url: n.url || '',
        level: n.level || '', status: n.status || '',
        degree: n.degree != null ? n.degree : null,
        category: ['topic', 'article', 'concept', 'practice'].indexOf(n.type),
        symbolSize: n.type === 'topic' ? 46 : n.type === 'article' ? 30 :
                    n.type === 'practice' ? 30 : conceptSize(n.degree)
      };
      if (n.type === 'topic') {
        item.label = { show: true, color: '#e9e4d8', fontFamily: '"Noto Serif SC",serif',
                       fontSize: 13, fontWeight: 700 };
        item.symbol = 'roundRect';
      } else if (n.type === 'article') {
        item.label = { show: true, color: '#3de8c9', fontFamily: '"JetBrains Mono",monospace', fontSize: 10.5 };
      } else if (n.type === 'practice') {
        item.label = { show: true, color: '#ff8fa3', fontFamily: '"JetBrains Mono",monospace', fontSize: 10.5 };
      } else {
        var show = labelAll || (Number(n.degree) || 0) >= CONCEPT_LABEL_DEGREE;
        item.label = { show: show, color: '#cabdf7', fontFamily: '"JetBrains Mono",monospace', fontSize: 10 };
      }
      nodes.push(item);
    }
    var nameToIndex = {};
    for (i = 0; i < nodes.length; i++) { nameToIndex[nodes[i].name] = i; }
    for (i = 0; i < data.links.length; i++) {
      var l = data.links[i], meta = LINK_META[l.type] || LINK_META.rel;
      var sName = idToName[l.source], tName = idToName[l.target];
      if (sName == null || tName == null) continue;
      links.push({
        source: sName, target: tName, kind: l.type,
        lineStyle: { color: meta.color, width: meta.width, curveness: 0.08 }
      });
      (adjacency[sName] = adjacency[sName] || []).push(nameToIndex[tName]);
      (adjacency[tName] = adjacency[tName] || []).push(nameToIndex[sName]);
    }
    nodeIndex = nameToIndex;

    var categories = [];
    Object.keys(TYPE_META).forEach(function (k) {
      categories.push({ name: TYPE_META[k].label, itemStyle: { color: TYPE_META[k].color } });
    });

    return {
      backgroundColor: 'transparent',
      textStyle: { fontFamily: '"Noto Sans SC","PingFang SC",sans-serif' },
      tooltip: {
        confine: true, backgroundColor: 'rgba(14,17,22,.94)', borderColor: 'rgba(61,232,201,.25)',
        borderWidth: 1, padding: [12, 16], textStyle: { color: '#e9e4d8' },
        extraCssText: 'backdrop-filter:blur(10px);border-radius:10px;',
        formatter: function (p) {
          if (p.dataType === 'node') return tooltipHtml(p);
          var m = LINK_META[p.data.kind];
          return m ? '<span style="font-size:12px;color:#b9b3a4">' + m.label + ' · ' +
                 p.data.source + ' — ' + p.data.target + '</span>' : '';
        }
      },
      legend: {
        top: 14, left: 18, icon: 'circle', itemWidth: 10, itemHeight: 10,
        textStyle: { color: '#b9b3a4', fontFamily: '"JetBrains Mono",monospace', fontSize: 11.5 },
        inactiveColor: '#4a4a44', selectedMode: 'multiple'
      },
      series: [{
        type: 'graph', layout: 'force', roam: true, draggable: true,
        categories: categories, data: nodes, links: links,
        label: { position: 'bottom', distance: 5 },
        lineStyle: { opacity: 1 },
        emphasis: {
          focus: 'adjacency',
          scale: 1.25,
          label: { show: true },
          lineStyle: { width: 2.4 }
        },
        force: {
          repulsion: 260, edgeLength: [45, 125], gravity: 0.08,
          friction: 0.25, initLayout: 'circular', layoutAnimation: true
        },
        scaleLimit: { min: 0.4, max: 3.2 }
      }]
    };
  }

  function render(data) {
    chart = echarts.init(canvas, null, { renderer: 'canvas' });
    chart.setOption(buildOption(data, false));
    bindInteractions(data);
    window.addEventListener('resize', function () { chart.resize(); });
    fillMeta(data);
  }

  /* ---- 元信息条 ---- */
  function fillMeta(data) {
    var c = (data.meta && data.meta.counts) || {};
    var counts = document.getElementById('graph-meta-counts');
    var time = document.getElementById('graph-meta-time');
    if (counts) {
      counts.textContent = '课题 ' + (c.topics || 0) + ' · 文章 ' + (c.articles || 0) +
        ' · 概念 ' + (c.concepts || 0) + ' · 实践 ' + (c.practices || 0) +
        ' · 关联 ' + (c.links || 0);
    }
    if (time && data.meta && data.meta.generated_at) {
      time.textContent = '数据生成于 ' + String(data.meta.generated_at).replace('T', ' ');
    }
  }

  /* ---- 交互 ---- */
  function focusNode(name) {
    if (!chart || nodeIndex[name] == null) return;
    chart.dispatchAction({ type: 'downplay', seriesIndex: 0 });
    var ids = [nodeIndex[name]].concat(adjacency[name] || []);
    for (var i = 0; i < ids.length; i++) {
      chart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: ids[i] });
    }
    chart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: nodeIndex[name] });
  }

  function bindInteractions(data) {
    /* 点击课题/文章直达，点击概念聚焦 */
    chart.on('click', function (params) {
      if (params.dataType !== 'node') return;
      var d = params.data;
      if (d.url) { window.open(d.url, '_blank', 'noopener'); return; }
      focusNode(d.name);
    });
    /* 点击画布空白取消聚焦 */
    chart.getZr().on('click', function (e) {
      if (!e.target) chart.dispatchAction({ type: 'downplay', seriesIndex: 0 });
    });

    /* 搜索建议 */
    var input = document.getElementById('graph-search');
    var suggest = document.getElementById('graph-suggest');
    if (!input || !suggest) return;
    var nodes = data.nodes || [];
    var timer = null;

    function buildSuggest(keyword) {
      var kw = keyword.trim().toLowerCase();
      if (!kw) { suggest.hidden = true; suggest.replaceChildren(); return; }
      var hits = [];
      for (var i = 0; i < nodes.length && hits.length < 8; i++) {
        var n = nodes[i];
        if (n.name.toLowerCase().indexOf(kw) >= 0 ||
            (n.summary || '').toLowerCase().indexOf(kw) >= 0) {
          hits.push(n);
        }
      }
      suggest.replaceChildren();
      if (!hits.length) {
        var empty = document.createElement('div');
        empty.style.cssText = 'padding:10px 14px;font-size:12px;color:#8d8778';
        empty.textContent = '没有匹配的节点';
        suggest.appendChild(empty);
      } else {
        hits.forEach(function (n) {
          var btn = document.createElement('button');
          btn.type = 'button';
          var kind = document.createElement('span');
          kind.className = 'sg-kind';
          kind.textContent = (TYPE_META[n.type] || {}).label || n.type;
          kind.style.color = (TYPE_META[n.type] || {}).color || '#b9b3a4';
          kind.style.borderColor = 'rgba(255,255,255,.12)';
          var name = document.createElement('span');
          name.textContent = n.name;
          btn.append(kind, name);
          btn.addEventListener('click', function () {
            suggest.hidden = true;
            input.value = n.name;
            focusNode(n.name);
          });
          suggest.appendChild(btn);
        });
      }
      suggest.hidden = false;
    }

    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { buildSuggest(input.value); }, 180);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { suggest.hidden = true; input.blur(); }
    });
    document.addEventListener('click', function (e) {
      if (!suggest.hidden && !suggest.contains(e.target) && e.target !== input) {
        suggest.hidden = true;
      }
    });

    /* 概念标签开关 */
    var toggle = document.getElementById('graph-label-toggle');
    if (toggle) {
      toggle.addEventListener('click', function () {
        allConcepts = !allConcepts;
        toggle.setAttribute('aria-pressed', allConcepts ? 'true' : 'false');
        toggle.classList.toggle('active', allConcepts);
        toggle.textContent = allConcepts ? '仅显示枢纽概念标签' : '显示全部概念标签';
        chart.setOption(buildOption(data, allConcepts));
      });
    }
  }
})();
