/* graph.js — 知识图谱页渲染（商业图谱风格：高饱和彩圆 + 关系着色）
 * 数据源 /assets/graph/graph-data.json（kb_distill.py 每周日生成）。
 *
 * 布局：径向辐射（中心节点 + 环状扩散）——以连接度最高的节点为中心，
 *   其余节点按到中心的 BFS 跳数分层入环，同环按类型聚簇排列；
 *   点击 Inspector 中「以此节点为中心」可换任意节点重排。
 *
 * 视觉（参考 echarts 知识图谱实例）：
 *   · 节点：高饱和实心彩圆，白描边 + 轻阴影；圆径随本图连接度缩放
 *   · 连线：随关系类型着色（归属红 / 核心蓝 / 标签金 / 关联青 / 层级紫），
 *     数量少的结构性关系默认显示彩色标签，其余悬停显示
 *   · 概念按道法术器四层着色聚簇（紫四档），纵向知识骨架以紫色层级线串联
 *   · 中心节点：白描边 + 同色光晕强调
 * 交互：单击节点查看详情（Inspector），双击直达页面，悬停聚焦邻接。
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

  /* ---- 类型元数据（高饱和商业图谱色板；节点为实心彩圆 + 白描边阴影） ---- */
  var TYPE_META = {
    topic:    { label: '研究课题', color: '#C12E34', text: '#FFFFFF' },
    article:  { label: '原创文章', color: '#0098D9', text: '#FFFFFF' },
    concept:  { label: '安全概念', color: '#2B821D', text: '#FFFFFF' },
    practice: { label: '实践反哺', color: '#E6B600', text: '#4A3B00' }
  };
  var TYPE_ORDER = ['topic', 'article', 'concept', 'practice'];

  /* ---- 关系元数据：每类关系独立配色（连线与关系标签同色）；
       暗底画布采用站点霓虹色板（红/蓝/金/青/绿/紫），保证深底可读 ---- */
  var LINK_META = {
    belongs: { label: '归属',     color: '#FF4D6D', text: '#FF8A9B', width: 2.6, showLabel: true },
    core:    { label: '核心关联', color: '#4FC3F7', text: '#8FD8F8', width: 1.9, showLabel: true },
    tag:     { label: '标签',     color: '#F0CD8A', text: '#FFE3AE', width: 1.6, showLabel: true },
    rel:     { label: '关联',     color: '#3DE8C9', text: '#8AF5E3', width: 1.5, showLabel: true },
    applies: { label: '实践应用', color: '#7ED957', text: '#B8EC9E', width: 1.6, showLabel: true },
    layer:   { label: '层级',     color: '#A78BFA', text: '#C9B8FB', width: 2.2, showLabel: true }
  };
  var LINK_ORDER = ['belongs', 'core', 'tag', 'rel', 'applies', 'layer'];
  var REL_NAME = {
    'RELATES_TO': '关联', 'COUNTERS': '对立',
    'FOUNDS': '奠基', 'COVERS': '涵盖', 'TARGETS': '作用', 'INSTANCE': '实例'
  };

  /* ---- 尺寸规格：节点大小随本图连接度动态缩放（度数越高圆越大） ---- */
  var NODE_MIN = { topic: 38, article: 28, practice: 28, concept: 26 };
  var NODE_SPAN = { topic: 16, article: 10, practice: 10, concept: 12 }; // 最高连接度时的增量
  /* 概念道法术器四层节点配色（紫色四档：道最深 -> 器最浅） */
  var LAYER_NODE = {
    '道': { color: '#5C3FA8', text: '#FFFFFF' },
    '法': { color: '#7B5CD6', text: '#FFFFFF' },
    '术': { color: '#9D82E8', text: '#FFFFFF' },
    '器': { color: '#C0ADF2', text: '#4A3B70' }
  };

  /* ---- 运行状态 ---- */
  var chart = null;
  var nodeIndex = {};    // name -> dataIndex
  var adjacency = {};    // name -> [dataIndex]
  var allConcepts = false;
  var hiddenTypes = {};
  var hiddenLinks = {};
  var DATA = null;
  var nameToNode = {};
  var idToNode = {};
  var centerName = null;   // 用户指定的中心（null = 自动选连接度最高者）
  var currentCenter = null; // 本次布局实际生效的中心
  var baseZoom = 1;        // 初始自适应缩放（复位按钮目标）
  var viewZoom = 1;        // 当前缩放倍率（滚轮 roam 与按钮共同维护）
  /* 坐标口径：布局全部使用「屏幕设计像素」。ECharts layout:'none' 会把
     布局包围盒自动 fit 进视口（内部系数 × option zoom = 渲染缩放），
     任何「除以缩放」的补偿都会被内部系数反向抵消——补偿 symbolSize
     恰好等价于直接给设计值，而补偿字号/线宽会被放大数倍（label 的
     fontSize/lineWidth 渲染时不再乘渲染缩放，恒为屏幕像素）。
     因此：字号、线宽、间距一律直接写设计像素；fitAfterRender 渲染后
     用渲染层 transform 实测修正 zoom，使布局外缘恰好占满视口 94%。 */
  var userZoomed = false;    // 用户是否手动缩放过（resize 时保持视野）

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

  /* ---- 工具 ---- */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  /* 估算文本像素宽（CJK 按整个字号、西文按 0.56 字号） */
  function textWidth(s, fs) {
    var w = 0;
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      w += (c > 0x2E80) ? fs : (c === 32 ? fs * 0.32 : fs * 0.56);
    }
    return w;
  }

  /* 概念圆直径：按标签折两行所需的宽度反推，保证圆内文字放得下。
     返回屏幕设计直径（32-44px），所有布局尺寸同口径（直接设计像素） */
  function conceptSize(name) {
    var w = textWidth(name, 9.5);
    var d = Math.ceil((w / 2 + 5) / 0.8);
    return Math.max(32, Math.min(44, d));
  }

  function relLabel(l) {
    if (l.rel && REL_NAME[l.rel]) return REL_NAME[l.rel];
    return (LINK_META[l.type] || {}).label || l.type;
  }

  /* ---- 径向布局：中心节点 + 环状辐射 ---- */
  var RADIAL_GAP = 18;    // 相邻环节点圆之间的径向净空（屏幕设计像素）
  var ARC_FACTOR = 1.14;  // 环向弧长余量因子：本环节点直径和 × 1.14 / 2π 为所需半径
  var CENTER_SIZE = 56;   // 中心节点直径
  var layoutMaxR = 0;     // 本次布局最外环半径（用于初始缩放自适应）

  /* 选中心：优先用户指定；否则取可见节点中连接度最高者 */
  function pickCenter(items, links) {
    if (centerName) {
      for (var c = 0; c < items.length; c++) {
        if (items[c].name === centerName) return centerName;
      }
    }
    var deg = {};
    for (var j = 0; j < links.length; j++) {
      deg[links[j].source] = (deg[links[j].source] || 0) + 1;
      deg[links[j].target] = (deg[links[j].target] || 0) + 1;
    }
    var best = null, bestDeg = -1;
    for (var k = 0; k < items.length; k++) {
      var d = deg[items[k].name] || 0;
      if (d > bestDeg || (d === bestDeg && best != null && items[k].name < best)) {
        best = items[k].name; bestDeg = d;
      }
    }
    return best;
  }

  /* 计算各节点坐标：BFS 跳数定环，同环类型聚簇、度数降序排角度 */
  function radialPlace(items, links) {
    var adj = {};
    var i, l;
    for (i = 0; i < links.length; i++) {
      l = links[i];
      (adj[l.source] = adj[l.source] || []).push(l.target);
      (adj[l.target] = adj[l.target] || []).push(l.source);
    }
    var center = pickCenter(items, links);

    /* BFS：以中心为根求最短跳数 */
    var dist = {}; dist[center] = 0;
    var queue = [center], head = 0;
    while (head < queue.length) {
      var cur = queue[head++];
      var next = adj[cur] || [];
      for (i = 0; i < next.length; i++) {
        if (dist[next[i]] == null) {
          dist[next[i]] = dist[cur] + 1;
          queue.push(next[i]);
        }
      }
    }
    var maxD = 0;
    for (var key in dist) { if (dist[key] > maxD) maxD = dist[key]; }

    /* 分层入环（无连接的孤立节点并入最外环，避免多一层空环） */
    var layers = [];
    for (i = 0; i < items.length; i++) {
      if (items[i].name === center) continue;
      var dd = dist[items[i].name] != null ? dist[items[i].name] : maxD;
      (layers[dd] = layers[dd] || []).push(items[i]);
    }

    /* 自适应环半径：每环取「径向需求」与「弧长需求」的较大者。
       径向需求 = 内环半径 + 两侧最大节点半径 + 净空（避免环间圆重叠）；
       弧长需求 = 本环节点直径和 × 余量因子 / 2π（避免环向挤成一团）。
       所有尺寸均为屏幕设计像素，直接参与计算 */
    var ringMax = [CENTER_SIZE];
    var ringSum = [0];
    for (var L = 1; L < layers.length; L++) {
      var rr = layers[L] || [];
      var m = 0, s = 0;
      for (i = 0; i < rr.length; i++) {
        var sz = Number(rr[i].symbolSize) || 30;
        if (sz > m) m = sz;
        s += sz;
      }
      ringMax[L] = m; ringSum[L] = s;
    }
    var ringR = [CENTER_SIZE / 2];
    for (L = 1; L < layers.length; L++) {
      if (!layers[L] || !layers[L].length) { ringR[L] = ringR[L - 1]; continue; }
      var arcNeed = Math.ceil((ringSum[L] * ARC_FACTOR) / (Math.PI * 2));
      var radialNeed = ringR[L - 1] + (ringMax[L - 1] + ringMax[L]) / 2 + RADIAL_GAP;
      ringR[L] = Math.max(arcNeed, radialNeed);
    }
    /* layoutMaxR 含最外环节点半径：fit 视野按「外缘」而非「环心」计算，
       避免最外圈节点和标签被裁出画布 */
    var lastR = ringR[ringR.length - 1] || 0;
    var lastMax = ringMax[ringMax.length - 1] || 0;
    layoutMaxR = (lastR + lastMax / 2) || CENTER_SIZE / 2;

    /* 同环排序：类型聚簇（课题→文章→实践→概念），概念内按道法术器聚簇，组内连接度降序 */
    var TYPE_RANK = { topic: 0, article: 1, practice: 2, concept: 3 };
    var LEVEL_RANK = { '道': 0, '法': 1, '术': 2, '器': 3 };
    for (var L = 1; L < layers.length; L++) {
      var ring = layers[L];
      if (!ring || !ring.length) continue;
      ring.sort(function (a, b) {
        var ra = TYPE_RANK[a.kind] != null ? TYPE_RANK[a.kind] : 9;
        var rb = TYPE_RANK[b.kind] != null ? TYPE_RANK[b.kind] : 9;
        if (ra !== rb) return ra - rb;
        var la = LEVEL_RANK[a.level] != null ? LEVEL_RANK[a.level] : 9;
        var lb = LEVEL_RANK[b.level] != null ? LEVEL_RANK[b.level] : 9;
        if (la !== lb) return la - lb;
        var da = Number(a.degree) || 0, db = Number(b.degree) || 0;
        if (da !== db) return db - da;
        return a.name < b.name ? -1 : 1;
      });
      var r = ringR[L] || (CENTER_SIZE / 2 + 120);
      for (i = 0; i < ring.length; i++) {
        var ang = -Math.PI / 2 + (Math.PI * 2 * i) / ring.length;
        ring[i].x = Math.round(r * Math.cos(ang));
        ring[i].y = Math.round(r * Math.sin(ang));
        /* 圆外标签按角度改为径向朝外（左右上下分区），减少环向挤压 */
        var lb = ring[i].label;
        if (lb && lb.position === 'bottom') {
          var cosA = Math.cos(ang), sinA = Math.sin(ang);
          if (cosA > 0.5) lb.position = 'right';
          else if (cosA < -0.5) lb.position = 'left';
          else if (sinA < 0) lb.position = 'top';
          /* 其余保持 bottom */
        }
      }
    }

    /* 中心节点置于原点并放大 */
    for (i = 0; i < items.length; i++) {
      if (items[i].name === center) {
        items[i].x = 0;
        items[i].y = 0;
        styleCenter(items[i]);
      }
    }

    /* 包围盒重心平移到原点：ECharts 的 center:'50%' 对齐的是
       布局包围盒中心而非布局原点——环角度分布不均时两者不重合，
       中心节点会偏离视口中心（实测曾偏 146×98px）。平移后
       包围盒中心 ≡ 原点 ≡ 中心节点，对齐即居中 */
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (i = 0; i < items.length; i++) {
      var half = (Number(items[i].symbolSize) || 30) / 2;
      var nx = items[i].x || 0, ny = items[i].y || 0;
      if (nx - half < minX) minX = nx - half;
      if (nx + half > maxX) maxX = nx + half;
      if (ny - half < minY) minY = ny - half;
      if (ny + half > maxY) maxY = ny + half;
    }
    var offX = (minX + maxX) / 2, offY = (minY + maxY) / 2;
    if (isFinite(offX) && isFinite(offY)) {
      for (i = 0; i < items.length; i++) {
        items[i].x = Math.round((items[i].x || 0) - offX);
        items[i].y = Math.round((items[i].y || 0) - offY);
      }
    }
    return center;
  }

  /* 中心节点样式：大圆居中，白描边 + 同色光晕强调；短名圆内两行，长名置于圆下方 */
  function styleCenter(item) {
    var meta = TYPE_META[item.kind] || {};
    var lvMeta = LAYER_NODE[item.level];
    var color = (lvMeta && lvMeta.color) || meta.color || '#C12E34';
    item.symbolSize = CENTER_SIZE;
    item.z = 10;
    item.itemStyle = {
      color: color,
      borderColor: '#FFFFFF', borderWidth: 3,
      shadowBlur: 22, shadowColor: color,
      shadowOffsetX: 0, shadowOffsetY: 0
    };
    /* 中心标签：圆内约 11.5px / 圆外约 13px（屏幕设计像素） */
    var cfs = 11.5;
    var cw = CENTER_SIZE;
    var need = (textWidth(item.name, cfs) / 2 + 6) / 0.84;
    if (need <= cw) {
      item.label = {
        show: true, position: 'inside',
        color: (lvMeta && lvMeta.text) || meta.text || '#FFFFFF', fontWeight: 700,
        fontFamily: '"Noto Sans SC","PingFang SC",sans-serif',
        fontSize: cfs, lineHeight: 14,
        width: Math.round(cw * 0.84), overflow: 'break'
      };
    } else {
      item.label = {
        show: true, position: 'bottom', distance: 9,
        color: '#E9E4D8', fontWeight: 700,
        fontFamily: '"Noto Sans SC","PingFang SC",sans-serif',
        fontSize: 13,
        width: 210, overflow: 'truncate'
      };
    }
  }

  /* ---- 选项构建 ---- */
  function buildOption(data, labelAll) {
    adjacency = {};
    var i, n, l;
    var idToName = {};
    for (i = 0; i < data.nodes.length; i++) {
      idToName[data.nodes[i].id] = data.nodes[i].name;
    }

    /* 第一遍：过滤有效边并统计本图连接度（节点大小按度数缩放的依据） */
    var visibleName = {};
    for (i = 0; i < data.nodes.length; i++) {
      if (!hiddenTypes[data.nodes[i].type]) visibleName[data.nodes[i].name] = true;
    }
    var rawLinks = [];
    var degMap = {};
    for (i = 0; i < data.links.length; i++) {
      l = data.links[i];
      if (hiddenLinks[l.type]) continue;
      var s0 = idToName[l.source], t0 = idToName[l.target];
      if (s0 == null || t0 == null) continue;
      if (!visibleName[s0] || !visibleName[t0]) continue;
      rawLinks.push(l);
      degMap[s0] = (degMap[s0] || 0) + 1;
      degMap[t0] = (degMap[t0] || 0) + 1;
    }
    var maxDeg = 1;
    for (var dk in degMap) { if (degMap[dk] > maxDeg) maxDeg = degMap[dk]; }

    /* 度数 → 圆径：连接度 1 取下限、最高连接度取上限，线性插值。
       NODE_MIN/NODE_SPAN 与 conceptSize 均为屏幕设计直径，直接使用 */
    function degSize(type, name, deg) {
      var k = maxDeg > 1 ? (deg - 1) / (maxDeg - 1) : 1;
      k = Math.max(0, Math.min(1, k));
      var d = (NODE_MIN[type] != null ? NODE_MIN[type] : 34) +
              (NODE_SPAN[type] != null ? NODE_SPAN[type] : 14) * k;
      if (type === 'concept') d = Math.max(conceptSize(name), d);
      return Math.round(d);
    }

    var nodes = [];
    for (i = 0; i < data.nodes.length; i++) {
      n = data.nodes[i];
      if (hiddenTypes[n.type]) continue;

      var deg = degMap[n.name] || 0;
      /* 注意：不要给节点 item 带 id 字段。ECharts 对带显式 id 的节点，
         links 的 source/target 会按 id 匹配而非 name，导致连线被静默丢弃 */
      var item = {
        name: n.name, kind: n.type,
        summary: n.summary || '', url: n.url || '',
        level: n.level || '', status: n.status || '',
        domain: n.domain || '', date: n.date || '',
        updated: n.updated || '', topic: n.topic || '',
        categories: n.categories || [],
        degree: n.degree != null ? n.degree : null,
        localDegree: deg,
        category: TYPE_ORDER.indexOf(n.type),
        /* 实心彩圆 + 白描边（暗底上呈霓虹勾边，贴 Neo4j 暗色主题） */
        itemStyle: {
          borderColor: '#FFFFFF', borderWidth: 2,
          shadowBlur: 5, shadowColor: 'rgba(0, 0, 0, .55)'
        }
      };

      if (n.type === 'topic') {
        /* 课题名偏长（8-26 字），置于圆下方单行显示（屏幕设计像素）。
           框宽收敛到 120px：横幅远宽于环节点间距时会盖到邻节点 */
        item.symbolSize = degSize('topic', n.name, deg);
        item.label = {
          show: true, position: 'bottom', distance: 7,
          color: '#E9E4D8', fontFamily: '"Noto Sans SC","PingFang SC",sans-serif',
          fontSize: 12, fontWeight: 700,
          width: 120, overflow: 'truncate'
        };
      } else if (n.type === 'article' || n.type === 'practice') {
        item.symbolSize = degSize(n.type, n.name, deg);
        item.label = {
          show: true, position: 'bottom', distance: 5,
          color: '#9AA3AD', fontFamily: '"Noto Sans SC","PingFang SC",sans-serif',
          fontSize: 10.5,
          width: 110, overflow: 'truncate'
        };
      } else {
        /* 概念名较短，圆内白字居中；圆径取「文本所需」与「度数缩放」的较大者 */
        var size = degSize('concept', n.name, deg);
        item.symbolSize = size;
        /* 道法术器四层着色（紫四档），未标层级的概念保持默认绿 */
        var lvMeta = LAYER_NODE[n.level];
        if (lvMeta) item.itemStyle.color = lvMeta.color;
        item.label = {
          show: labelAll,
          position: 'inside',
          color: (lvMeta && lvMeta.text) || TYPE_META.concept.text,
          fontFamily: '"Noto Sans SC","PingFang SC",sans-serif',
          /* 圆内文字 9.5px，屏幕像素恒定 */
          fontSize: 9.5, lineHeight: 11,
          width: Math.round(size * 0.8), overflow: 'break'
        };
      }
      nodes.push(item);
    }

    var nameToIndex = {};
    for (i = 0; i < nodes.length; i++) { nameToIndex[nodes[i].name] = i; }

    var links = [];
    for (i = 0; i < rawLinks.length; i++) {
      l = rawLinks[i];
      var sName = idToName[l.source], tName = idToName[l.target];
      var lm = LINK_META[l.type] || {};
      links.push({
        source: sName, target: tName, kind: l.type, rel: l.rel || '',
        labelText: relLabel(l),
        /* 连线随关系类型着色；width = 目标屏幕像素（1.5-2.6px），
           ECharts 对线宽不做渲染缩放，直接给设计值即可 */
        lineStyle: {
          color: lm.color || '#9AA0A6',
          width: Math.max(1.2, lm.width || 1.5),
          opacity: .95
        },
        /* 内置边标签已弃用：ECharts 5.5.0 在 layout:'none' + 自动 fit
           下坐标系缺陷——边标签按世界坐标渲染（漏乘内部 fit 系数），
           实测「核心关联」画在视口左上角 (87,80)，距所属边屏幕中点
           300+px，且 graphRoam 缩放平移时不跟随。关系名改由 graphic
           层手动渲染（见 updateEdgeLabels），位置用 convertToPixel
           计算，口径已实测校准 */
        label: { show: false }
      });
      (adjacency[sName] = adjacency[sName] || []).push(nameToIndex[tName]);
      (adjacency[tName] = adjacency[tName] || []).push(nameToIndex[sName]);
    }
    nodeIndex = nameToIndex;

    /* 径向布局：就地写入 x/y，返回实际中心 */
    currentCenter = radialPlace(nodes, links);

    var categories = TYPE_ORDER.map(function (t) {
      return { name: TYPE_META[t].label, itemStyle: { color: TYPE_META[t].color } };
    });

    /* 初始缩放先沿用 viewZoom（首次为 1）。真实视野由 fitAfterRender()
       在渲染完成后实测修正：ECharts layout:'none' 会把布局包围盒自动
       fit 进视口，再乘 option zoom——必须在渲染层实测才知道总缩放。
       字号/线宽/箭头均为屏幕像素恒定，无需任何补偿 */
    var fitZoom = viewZoom || 1;
    baseZoom = fitZoom;
    viewZoom = fitZoom;

    return {
      backgroundColor: 'transparent',
      /* 禁用动画：入场动画期间渲染层 transform 处于中间态，会污染
         fitAfterRender 的实测缩放；且 fit 修正 zoom 时若动画在跑，
         实测值随帧漂移导致视野抖动 */
      animation: false,
      textStyle: { fontFamily: '"Noto Sans SC","PingFang SC",sans-serif' },
      tooltip: {
        confine: true,
        backgroundColor: 'rgba(18, 25, 33, .97)',
        borderColor: 'rgba(61, 232, 201, .35)',
        borderWidth: 1,
        padding: [9, 13],
        textStyle: { color: '#E9E4D8', fontSize: 12 },
        extraCssText: 'border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.5);',
        formatter: function (p) {
          if (p.dataType === 'edge') {
            return '<span style="color:#9AA3AD">' + esc(p.data.labelText) + '</span>' +
                   '<span style="color:#6E7884"> · </span>' +
                   '<span style="color:#E9E4D8">' + esc(p.data.source) + '</span>' +
                   '<span style="color:#6E7884"> → </span>' +
                   '<span style="color:#E9E4D8">' + esc(p.data.target) + '</span>';
          }
          var d = p.data;
          var meta = TYPE_META[d.kind] || {};
          var sub = [meta.label];
          if (d.level) sub.push(d.level);
          if (d.status) sub.push(d.status);
          if (d.degree != null) sub.push('连接度 ' + d.degree);
          var html = '<div style="font-size:13px;font-weight:700;color:#E9E4D8;line-height:1.5">' +
                     esc(d.name) + '</div>';
          html += '<div style="font-size:10.5px;color:#9AA3AD;margin-top:3px;letter-spacing:.5px">' +
                  esc(sub.filter(Boolean).join(' · ')) + '</div>';
          if (d.summary) {
            html += '<div style="max-width:280px;font-size:11.5px;line-height:1.7;color:#B6BDC7;margin-top:5px">' +
                    esc(d.summary) + '</div>';
          }
          return html;
        }
      },
      labelLayout: { hideOverlap: true },
      series: [{
        type: 'graph', layout: 'none', roam: true, draggable: true,
        /* center 用数值 [0,0]：锚定世界坐标原点（radialPlace 已把布局
           重心平移到原点）→ 原点映射到视口中心，径向图天然居中。
           注意：百分比 '50%' 会被解释为「世界坐标 (50%W, 50%H)」，
           该点远在 ±300 的布局范围之外 → 整图被推到左上角 */
        center: [0, 0], zoom: fitZoom,
        categories: categories, data: nodes, links: links,
        /* 布局：径向辐射，坐标由 radialPlace 预计算（中心 + 同心环） */
        /* 节点样式（白描边 + 阴影）与连线颜色均在 data 级按类型/关系设置 */
        lineStyle: { curveness: 0 },
        edgeSymbol: ['none', 'arrow'],
        /* 箭头大小 8px（屏幕像素恒定，避免缩成看不见的尖点） */
        edgeSymbolSize: 8,
        emphasis: {
          focus: 'adjacency',
          scale: 1.06,
          label: { show: true },
          /* 不固定 width：hover 高亮沿用补偿后的线宽（link 级已按屏幕像素算好） */
          lineStyle: { opacity: 1 }
        },
        blur: {
          itemStyle: { opacity: .18 },
          label: { opacity: .18 },
          lineStyle: { opacity: .06 }
        },
        scaleLimit: { min: 0.25, max: 4 }
      }]
    };
  }

  /* ---- 视野自适应（convertToPixel 实测） ----
     zoom 与节点屏幕跨度严格线性（实测 zoom×2 → 跨度精确×2），用
     convertToPixel 算节点 bbox（CSS 像素全局坐标，跨 DPR 稳定），
     按「当前跨度 → 目标跨度」线性外推 option zoom，一轮即收敛。
     注意：zrender displayList 元素 transform 是不含父级变换的局部
     坐标，不能当屏幕坐标用；convertToPixel 的「点位置映射」才是
     精确口径（其返回的缩放系数另有量纲问题，但位置可用）。
     字号/线宽/箭头渲染时不乘 transform，恒为屏幕像素，天然无需补偿；
     节点直径随缩放自然变化（放大看细节，缩小看全貌）。 */

  function measureNodeSpan() {
    try {
      /* 用官方 convertToPixel 计算节点屏幕 bbox（CSS 像素，全局坐标）。
         之前读 zrender displayList 元素 transform 的方案有致命缺陷：
         那是「不含父级容器变换的局部坐标」，与视口尺寸无关，
         拿它当画布像素算缩放必然失真（实测 fill 1.72 倍溢出） */
      var data = chart.getOption().series[0].data;
      var xs = [], ys = [];
      for (var i = 0; i < data.length; i++) {
        var d = data[i];
        if (d.x === undefined || d.y === undefined) continue;
        var p = chart.convertToPixel({ seriesIndex: 0 }, [d.x, d.y]);
        if (!p || !isFinite(p[0]) || !isFinite(p[1])) continue;
        xs.push(p[0]); ys.push(p[1]);
      }
      if (!xs.length) return null;
      var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
      var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
      /* CSS 像素口径，与 host.clientWidth 同单位，跨 DPR 稳定 */
      var dom = chart.getDom();
      return {
        spanX: x1 - x0, spanY: y1 - y0,
        cx: (x0 + x1) / 2, cy: (y0 + y1) / 2,
        cvW: dom.clientWidth, cvH: dom.clientHeight
      };
    } catch (err) { return null; }
  }

  function fitAfterRender() {
    if (!chart) return;
    /* zoom 与节点跨距严格线性（实测 zoom×2 → 跨距精确×2），因此用
       「当前跨距 → 目标跨距」线性外推 option zoom，一轮即收敛。
       目标跨距给节点半径与外圈标签留约 14% 边距（86% 铺满） */
    for (var k = 0; k < 3; k++) {
      var p = measureNodeSpan();
      if (!p) return;
      var targetSpan = Math.min(p.cvW, p.cvH) * 0.86;
      var curSpan = Math.max(p.spanX, p.spanY);
      if (curSpan <= 4) return;
      var curZoom = chart.getOption().series[0].zoom || 1;
      var z = curZoom * targetSpan / curSpan;
      z = Math.max(0.18, Math.min(2.8, z));
      if (Math.abs(z - curZoom) < curZoom * 0.02) {
        baseZoom = curZoom; viewZoom = curZoom; return;
      }
      chart.setOption({ series: [{ zoom: z }] });
      baseZoom = z; viewZoom = z;
    }
  }

  /* ---- 边标签手动渲染（graphic 层） ----
     ECharts 5.5.0 内置边标签在 layout:'none' + 自动 fit 下坐标系错乱
     （世界坐标直接当屏幕坐标渲染、漏乘内部 fit 系数、roam 时不跟随），
     因此 links.label 全部关闭，改由本函数用 convertToPixel（口径已
     实测校准）计算边中点，在 graphic 层绘制关系名：
     · 防重叠：每条边依次尝试 0.5 / 0.38 / 0.62 三个锚点，先到先得，
       仍放不下则隐藏该条（放大视野后空间变大，自动恢复显示）
     · 端点避让：标签不得压在节点圆上（留 6px 缓冲）
     · 视口裁剪：中点滚出视口的边不画标签
     · 跟随：graphRoam / 缩放按钮 / fit / resize / 节点拖拽后重算，
       rAF 合并同帧多次触发
     · 指纹比对：位置无变化则跳过 setOption，避免 finished 兜底与
       graphic 更新互相触发形成渲染死循环 */
  var edgeLabelHash = '';
  var edgeLabelsQueued = false;

  function scheduleEdgeLabels() {
    if (edgeLabelsQueued || !chart) return;
    edgeLabelsQueued = true;
    requestAnimationFrame(function () {
      edgeLabelsQueued = false;
      updateEdgeLabels();
    });
  }

  function updateEdgeLabels() {
    if (!chart) return;
    var opt = chart.getOption();
    var series = opt.series && opt.series[0];
    var links = (series && series.links) || [];
    if (!links.length) {
      chart.setOption({ graphic: [] }, { replaceMerge: ['graphic'] });
      edgeLabelHash = '';
      return;
    }
    var data = series.data || [];
    var byName = {};
    var i;
    for (i = 0; i < data.length; i++) byName[data[i].name] = data[i];

    var W = chart.getWidth(), H = chart.getHeight();
    var FS = 10, PADX = 4, PADY = 2;

    /* 候选收集：每条可见边的端点屏幕坐标 + 三个候选锚点 */
    var cands = [];
    for (i = 0; i < links.length; i++) {
      var lk = links[i];
      var s = byName[lk.source], t = byName[lk.target];
      if (!s || !t || s.x === undefined || t.x === undefined) continue;
      var txt = lk.labelText || ((LINK_META[lk.kind] || {}).label) || '';
      if (!txt) continue;
      var p1 = chart.convertToPixel({ seriesIndex: 0 }, [s.x, s.y]);
      var p2 = chart.convertToPixel({ seriesIndex: 0 }, [t.x, t.y]);
      if (!p1 || !p2) continue;
      cands.push({
        idx: i, text: txt, kind: lk.kind,
        color: (LINK_META[lk.kind] || {}).text || (LINK_META[lk.kind] || {}).color || '#9AA0A6',
        deg: Math.max(s.localDegree || 0, t.localDegree || 0),
        ends: [
          { x: p1[0], y: p1[1], r: (s.symbolSize || 16) / 2 },
          { x: p2[0], y: p2[1], r: (t.symbolSize || 16) / 2 }
        ]
      });
    }

    /* 权重排序：类型在 LINK_ORDER 中越靠前越优先（归属/核心最重要），
       同类型按端点度数降序——中心节点辐射出的关系名优先保留 */
    cands.sort(function (a, b) {
      var wa = LINK_ORDER.indexOf(a.kind), wb = LINK_ORDER.indexOf(b.kind);
      if (wa !== wb) return wa - wb;
      return b.deg - a.deg;
    });

    /* 贪心放置：矩形碰撞检测（含 2-3px 间隙） */
    var rects = [];
    var placed = {};
    var ANCHORS = [0.5, 0.38, 0.62];
    for (i = 0; i < cands.length; i++) {
      var c = cands[i];
      var w = textWidth(c.text, FS) + PADX * 2, h = FS + PADY * 2 + 2;
      var ok = null;
      for (var a = 0; a < ANCHORS.length && !ok; a++) {
        var ax = c.ends[0].x + (c.ends[1].x - c.ends[0].x) * ANCHORS[a];
        var ay = c.ends[0].y + (c.ends[1].y - c.ends[0].y) * ANCHORS[a];
        /* 视口裁剪（允许部分露出 60px） */
        if (ax < -60 || ay < -30 || ax > W + 60 || ay > H + 30) continue;
        /* 端点圆避让：标签中心距任一端点圆心不得小于 半径+标签半宽+6 */
        var clash = false;
        for (var e = 0; e < 2; e++) {
          var dx = ax - c.ends[e].x, dy = ay - c.ends[e].y;
          var lim = c.ends[e].r + Math.max(w, h) / 2 + 6;
          if (dx * dx + dy * dy < lim * lim) { clash = true; break; }
        }
        if (clash) continue;
        var x0 = ax - w / 2 - 3, y0 = ay - h / 2 - 2,
            x1 = ax + w / 2 + 3, y1 = ay + h / 2 + 2;
        var hit = false;
        for (var r = 0; r < rects.length; r++) {
          if (x0 < rects[r][2] && x1 > rects[r][0] &&
              y0 < rects[r][3] && y1 > rects[r][1]) { hit = true; break; }
        }
        if (!hit) ok = { x: ax, y: ay, w: w, h: h };
      }
      if (ok) {
        placed[c.idx] = { x: ok.x, y: ok.y, text: c.text, color: c.color };
        rects.push([ok.x - ok.w / 2, ok.y - ok.h / 2, ok.x + ok.w / 2, ok.y + ok.h / 2]);
      }
    }

    /* 生成 graphic 元素：未放置的也建元素（invisible 占位，id 稳定，
       replaceMerge 整体替换，筛选关系类型后不残留旧元素） */
    var els = [], fp = [];
    for (i = 0; i < links.length; i++) {
      var q = placed[i];
      if (q) {
        els.push({
          type: 'text', id: 'el_' + i, silent: true, z: 40,
          x: Math.round(q.x), y: Math.round(q.y),
          style: {
            text: q.text,
            font: FS + 'px "Noto Sans SC","PingFang SC",sans-serif',
            fill: q.color,
            textAlign: 'center', textVerticalAlign: 'middle',
            backgroundColor: 'rgba(11, 20, 24, .85)',
            padding: [PADY, PADX],
            borderRadius: 2
          }
        });
        fp.push(i + ':' + Math.round(q.x) + ',' + Math.round(q.y) + ':' + q.text);
      } else {
        els.push({ type: 'text', id: 'el_' + i, x: -999, y: -999,
                   invisible: true, silent: true, style: { text: '' } });
        fp.push(i + ':off');
      }
    }
    var hash = fp.join('|');
    if (hash === edgeLabelHash) return;
    edgeLabelHash = hash;
    chart.setOption({ graphic: els }, { replaceMerge: ['graphic'] });
  }

  /* ---- 渲染 ---- */
  function render(data) {
    DATA = data;
    nameToNode = {};
    idToNode = {};
    for (var i = 0; i < data.nodes.length; i++) {
      nameToNode[data.nodes[i].name] = data.nodes[i];
      idToNode[data.nodes[i].id] = data.nodes[i];
    }

    chart = echarts.init(canvas, null, { renderer: 'canvas' });
    chart.setOption(buildOption(data, false));
    fitAfterRender();   // 渲染层实测 → 修正默认视野占满视口 94%
    scheduleEdgeLabels();
    bindInteractions(data);
    window.addEventListener('resize', function () {
      if (!chart) return;
      chart.resize();
      /* 未手动缩放时重新自适应；已缩放则保持相对视野（ECharts 内部
         会按新视口重算自动 fit，option zoom 不变即视野等比保持） */
      if (!userZoomed) fitAfterRender();
      /* 视口尺寸变了，节点屏幕坐标全部变化，边标签必须重算 */
      scheduleEdgeLabels();
    });
    fillMeta(data);
    fillSidebar(data);
    fillStatusbar(data);
  }

  function rebuild() {
    if (!chart || !DATA) return;
    chart.setOption(buildOption(DATA, allConcepts), { notMerge: true });
    fillStatusbar(DATA);
    if (currentInspector && hiddenTypes[currentInspector.type]) closeInspector();
    /* 布局/中心已变（换中心、筛选），重新自适应视野 */
    fitAfterRender();
    scheduleEdgeLabels();
  }

  /* ---- 元信息条 ---- */
  function fillMeta(data) {
    if (data.meta && data.meta.generated_at) {
      setText('graph-meta-time', '数据生成于 ' + String(data.meta.generated_at).replace('T', ' '));
    }
  }

  /* ---- 状态栏 ---- */
  function fillStatusbar(data) {
    var txt = data.nodes.length + ' nodes · ' + data.links.length + ' relationships';
    if (currentCenter) txt += ' · ◉ 中心: ' + currentCenter;
    setText('graph-statusbar', txt);
  }

  /* ---- 换中心重排 ---- */
  function setCenter(name) {
    if (!name || name === centerName) return;
    centerName = name;
    rebuild();
    /* 刷新 Inspector，使「以此节点为中心」按钮状态与新中心同步 */
    if (currentInspector) openInspector(currentInspector.name);
  }

  /* ---- 侧栏 ---- */
  function fillSidebar(data) {
    var i;
    var typeCounts = {};
    for (i = 0; i < data.nodes.length; i++) {
      typeCounts[data.nodes[i].type] = (typeCounts[data.nodes[i].type] || 0) + 1;
    }
    var present = TYPE_ORDER.filter(function (t) { return typeCounts[t] > 0; });

    setText('sb-nodes', data.nodes.length);
    setText('sb-links', data.links.length);
    setText('sb-labels', present.length);

    /* Node labels：粉彩色块 + 标签文字（Neo4j 侧栏样式） */
    var nl = document.getElementById('sb-node-labels');
    if (nl) {
      nl.replaceChildren();
      present.forEach(function (t) {
        var row = document.createElement('button');
        row.type = 'button';
        row.className = 'sb-row';
        row.dataset.type = t;
        var chip = document.createElement('span');
        chip.className = 'sb-chip';
        chip.style.background = TYPE_META[t].color;
        chip.textContent = TYPE_META[t].label;
        var cnt = document.createElement('span');
        cnt.className = 'sb-count';
        cnt.textContent = typeCounts[t];
        row.append(chip, cnt);
        row.addEventListener('click', function () {
          hiddenTypes[t] = !hiddenTypes[t];
          row.classList.toggle('off', !!hiddenTypes[t]);
          rebuild();
        });
        nl.appendChild(row);
      });
    }

    /* Relationship types：细线色块（Neo4j 侧栏样式） */
    var linkCounts = {};
    for (i = 0; i < data.links.length; i++) {
      linkCounts[data.links[i].type] = (linkCounts[data.links[i].type] || 0) + 1;
    }
    var rt = document.getElementById('sb-rel-types');
    if (rt) {
      rt.replaceChildren();
      LINK_ORDER.forEach(function (t) {
        if (!linkCounts[t]) return;
        var row = document.createElement('button');
        row.type = 'button';
        row.className = 'sb-row';
        row.dataset.type = t;
        var sw = document.createElement('span');
        sw.className = 'sb-line';
        sw.style.background = (LINK_META[t] || {}).color || '#A5ABB6';
        var label = document.createElement('span');
        label.textContent = LINK_META[t].label;
        var cnt = document.createElement('span');
        cnt.className = 'sb-count';
        cnt.textContent = linkCounts[t];
        row.append(sw, label, cnt);
        row.addEventListener('click', function () {
          hiddenLinks[t] = !hiddenLinks[t];
          row.classList.toggle('off', !!hiddenLinks[t]);
          rebuild();
        });
        rt.appendChild(row);
      });
    }

    /* 道法术器层级图例：统计概念分层（紫四档与节点配色一致） */
    var lv = document.getElementById('sb-layers');
    var lvCard = document.getElementById('sb-layers-card');
    if (lv) {
      var levelCounts = {};
      for (i = 0; i < data.nodes.length; i++) {
        var nd = data.nodes[i];
        if (nd.type === 'concept' && nd.level) {
          levelCounts[nd.level] = (levelCounts[nd.level] || 0) + 1;
        }
      }
      var LAYER_DESC = { '道': '公理原则', '法': '方法论', '术': '技术手段', '器': '工具载体' };
      lv.replaceChildren();
      Object.keys(LAYER_DESC).forEach(function (k) {
        if (!levelCounts[k]) return;
        var row = document.createElement('div');
        row.className = 'sb-layer-row';
        var b = document.createElement('span');
        b.className = 'ly-badge';
        b.style.background = (LAYER_NODE[k] || {}).color || '#7B5CD6';
        b.textContent = k;
        var nm = document.createElement('span');
        nm.className = 'ly-name';
        nm.textContent = LAYER_DESC[k];
        var cnt = document.createElement('span');
        cnt.className = 'sb-count';
        cnt.textContent = levelCounts[k];
        row.append(b, nm, cnt);
        lv.appendChild(row);
      });
      if (lvCard) lvCard.hidden = !lv.children.length;
    }
  }

  /* ---- 节点 Inspector ---- */
  var inspector = document.getElementById('graph-inspector');
  var currentInspector = null;

  function nodeProps(node) {
    var props = [];
    if (node.degree != null) props.push(['连接度', node.degree]);
    if (node.level) props.push(['层级', node.level]);
    if (node.domain) props.push(['领域', node.domain]);
    if (node.status) props.push(['状态', node.status]);
    if (node.updated) props.push(['更新', node.updated]);
    if (node.date) props.push(['日期', node.date]);
    if (node.type === 'article' && node.topic) {
      var t = idToNode['topic:' + node.topic];
      if (t) props.push(['所属课题', t.name]);
    }
    return props;
  }

  function buildRelations(node) {
    var rels = [], seen = {}, i, l;
    for (i = 0; i < DATA.links.length; i++) {
      l = DATA.links[i];
      var otherId = null;
      if (l.source === node.id) otherId = l.target;
      else if (l.target === node.id) otherId = l.source;
      if (!otherId) continue;
      var other = idToNode[otherId];
      if (!other || other.name === node.name) continue;
      if (seen[other.name]) continue;
      seen[other.name] = true;
      rels.push({
        name: other.name,
        color: (TYPE_META[other.type] || {}).color || '#A5ABB6',
        kind: relLabel(l)
      });
    }
    return rels;
  }

  function openInspector(name) {
    var node = nameToNode[name];
    if (!node || !inspector) return;
    currentInspector = node;
    var meta = TYPE_META[node.type] || {};

    var badges = [{ text: meta.label, cls: 'type-badge', bg: meta.color }];
    if (node.level) badges.push({ text: node.level });
    if (node.status) badges.push({ text: node.status });
    if (node.domain) badges.push({ text: node.domain });
    if (node.categories && node.categories.length) {
      node.categories.forEach(function (c) { badges.push({ text: c }); });
    }

    var props = nodeProps(node);
    var rels = buildRelations(node);

    var html = '';
    html += '<div class="insp-head">';
    html += '<span class="insp-dot" style="background:' + meta.color + '"></span>';
    html += '<span class="insp-name"></span>';
    html += '<button class="insp-close" type="button" aria-label="关闭">×</button>';
    html += '</div>';

    if (badges.length) {
      html += '<div class="insp-labels">';
      badges.forEach(function (b) {
        var style = b.bg ? ' style="background:' + b.bg + '"' : '';
        html += '<span class="insp-badge ' + (b.cls || '') + '"' + style + '>' + esc(b.text) + '</span>';
      });
      html += '</div>';
    }

    if (node.summary) {
      html += '<div class="insp-sec">摘要</div>';
      html += '<div class="insp-summary"></div>';
    }

    if (props.length) {
      html += '<div class="insp-sec">属性</div>';
      props.forEach(function () {
        html += '<div class="insp-prop"><span class="k"></span><span class="v"></span></div>';
      });
    }

    if (rels.length) {
      html += '<div class="insp-sec">关联（' + rels.length + '）</div>';
      rels.forEach(function (r) {
        html += '<button class="insp-rel" type="button" data-name="' + esc(r.name) + '">' +
                '<span class="r-dot" style="background:' + r.color + '"></span>' +
                '<span class="r-name"></span>' +
                '<span class="r-kind">' + esc(r.kind) + '</span></button>';
      });
    }

    if (node.name !== currentCenter) {
      html += '<button class="insp-center" type="button">◎ 以此节点为中心</button>';
    }

    if (node.url) {
      html += '<a class="insp-open" href="' + esc(node.url) + '" target="_blank" rel="noopener">打开页面 →</a>';
    }

    inspector.innerHTML = html;
    inspector.hidden = false;

    inspector.querySelector('.insp-name').textContent = node.name;
    var sum = inspector.querySelector('.insp-summary');
    if (sum) sum.textContent = node.summary;
    var ks = inspector.querySelectorAll('.insp-prop .k');
    var vs = inspector.querySelectorAll('.insp-prop .v');
    props.forEach(function (p, idx) {
      if (ks[idx]) ks[idx].textContent = p[0];
      if (vs[idx]) vs[idx].textContent = String(p[1]);
    });
    var rnames = inspector.querySelectorAll('.insp-rel .r-name');
    rels.forEach(function (r, idx) {
      if (rnames[idx]) rnames[idx].textContent = r.name;
    });

    var closeBtn = inspector.querySelector('.insp-close');
    if (closeBtn) closeBtn.addEventListener('click', closeInspector);
    var centerBtn = inspector.querySelector('.insp-center');
    if (centerBtn) {
      centerBtn.addEventListener('click', function () {
        setCenter(node.name);
      });
    }
    inspector.querySelectorAll('.insp-rel').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var n = btn.dataset.name;
        focusNode(n);
        openInspector(n);
      });
    });
  }

  function closeInspector() {
    currentInspector = null;
    if (inspector) inspector.hidden = true;
  }

  /* ---- 交互 ---- */
  function focusNode(name) {
    if (!chart || nodeIndex[name] == null) return;
    chart.dispatchAction({ type: 'downplay', seriesIndex: 0 });
    var ids = [nodeIndex[name]].concat(adjacency[name] || []);
    for (var i = 0; i < ids.length; i++) {
      chart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: ids[i] });
    }
  }

  function bindInteractions(data) {
    /* 单击节点 -> Inspector */
    chart.on('click', function (params) {
      if (params.dataType !== 'node') return;
      openInspector(params.data.name);
    });
    /* 双击节点 -> 直达页面 */
    chart.on('dblclick', function (params) {
      if (params.dataType !== 'node') return;
      if (params.data.url) window.open(params.data.url, '_blank', 'noopener');
    });
    /* 点击画布空白取消聚焦 + 关闭 Inspector */
    chart.getZr().on('click', function (e) {
      if (!e.target) {
        chart.dispatchAction({ type: 'downplay', seriesIndex: 0 });
        closeInspector();
      }
    });

    /* 搜索建议 */
    var input = document.getElementById('graph-search');
    var suggest = document.getElementById('graph-suggest');
    if (input && suggest) {
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
          empty.style.cssText = 'padding:10px 14px;font-size:12px;color:#8B9199';
          empty.textContent = '没有匹配的节点';
          suggest.appendChild(empty);
        } else {
          hits.forEach(function (n) {
            var btn = document.createElement('button');
            btn.type = 'button';
            var kind = document.createElement('span');
            kind.className = 'sg-kind';
            kind.textContent = (TYPE_META[n.type] || {}).label || n.type;
            var name = document.createElement('span');
            name.textContent = n.name;
            btn.append(kind, name);
            btn.addEventListener('click', function () {
              suggest.hidden = true;
              input.value = n.name;
              focusNode(n.name);
              openInspector(n.name);
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
    }

    /* 概念标签开关（默认悬停显示，开启后全部常显） */
    var toggle = document.getElementById('graph-label-toggle');
    if (toggle) {
      toggle.addEventListener('click', function () {
        allConcepts = !allConcepts;
        toggle.setAttribute('aria-pressed', allConcepts ? 'true' : 'false');
        toggle.classList.toggle('active', allConcepts);
        toggle.textContent = allConcepts ? '概念标签 · 全部显示' : '概念标签 · 悬停显示';
        rebuild();
      });
    }

    /* 画布缩放按钮：放大 / 缩小 / 复位（与滚轮 roam 互通）。
       字号/线宽恒为屏幕像素，缩放只影响节点直径与视野，无需重建样式 */
    chart.on('graphRoam', function (e) {
      if (e.zoom != null && e.zoom !== 1) {
        viewZoom *= e.zoom;
        userZoomed = true;
      }
      /* 滚轮缩放 / 拖拽平移后节点屏幕坐标变化，边标签跟随重算 */
      scheduleEdgeLabels();
    });
    /* 节点拖拽没有专门事件，用 finished 兜底重算边标签。
       updateEdgeLabels 内部有指纹比对（位置无变化即跳过 setOption），
       不会与 graphic 更新触发的 finished 互相喂形成死循环 */
    chart.on('finished', scheduleEdgeLabels);
    function applyZoom(z) {
      z = Math.max(0.25, Math.min(4, z));
      viewZoom = z;
      chart.setOption({ series: [{ zoom: z }] });
      userZoomed = true;
      scheduleEdgeLabels();
    }
    var zin = document.getElementById('graph-zoom-in');
    if (zin) zin.addEventListener('click', function () { applyZoom(viewZoom * 1.35); });
    var zout = document.getElementById('graph-zoom-out');
    if (zout) zout.addEventListener('click', function () { applyZoom(viewZoom / 1.35); });
    var zreset = document.getElementById('graph-zoom-reset');
    if (zreset) zreset.addEventListener('click', function () {
      /* 复位 = 回到自适应默认视野：取消用户标记，按当前布局重新 fit */
      userZoomed = false;
      fitAfterRender();
      scheduleEdgeLabels();
    });

    /* 移动端侧栏浮层 */
    var floatBtn = document.getElementById('sb-float-btn');
    var sidebar = document.getElementById('graph-sidebar');
    if (floatBtn && sidebar) {
      floatBtn.addEventListener('click', function () {
        var open = sidebar.classList.toggle('open');
        floatBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }
  }
})();
