---
layout: default
title: AI 与安全兵器谱
permalink: /tools/
---
<section id="tools">
  <div class="wrap">
    <div class="section-head">
      <div class="num">04 / ARSENAL</div>
      <h2>AI 与安全兵器谱</h2>
      <p class="desc">只收录试炼过的兵器：空间测绘、威胁情报、AI 安全、AI 提效四大门类，按天 / 地 / 玄 分级。FOFA 与 Shodan 两大测绘引擎首录，其余兵器正逐一试炼入库，长期维护。</p>
    </div>

    <div class="filter-bar">
      <div class="search-box">
        <span class="icon">⌕</span>
        <input id="tool-search" type="text" placeholder="搜索兵器 / 用途 / 标签…" autocomplete="off">
      </div>
      <div class="chips-rows">
        <div class="chips-row">
          <span class="chips-label">门类</span>
          <div class="tag-chips" id="tool-chips"></div>
        </div>
      </div>
    </div>

    <div class="tool-grid" id="tool-grid"></div>

    <div class="empty-result" id="tool-empty" hidden>
      <div class="glyph">兵</div>
      <span id="tool-empty-text">没有匹配的兵器，换个关键词试试</span>
    </div>

    <div class="tool-note">
      兵器谱持续试炼收录 · 分级：<b>天</b> 必备主力 ／ <b>地</b> 场景利器 ／ <b>玄</b> 备选兵器 · 欢迎推荐候选
    </div>
  </div>
</section>

<script>
/* ============================================================
   兵器谱维护入口：日常维护只改下面两个常量，其余全自动
   1) CATS  —— 门类骨架；新增门类加一行 key: '中文名'
   2) TOOLS —— 兵器条目；往数组追加对象即可上墙
   卡片、门类筛选、计数、搜索全部自动生成，无需动 HTML / CSS
   字段：name 名称 / sub 一句话别名 / url 官网 / cat 门类key
         rank 分级 s|a|b / access 访问门槛 / tags 标签 / desc 试炼心得
   ============================================================ */
(function () {
  var CATS = {
    cyberspace: '空间测绘',
    intel: '威胁情报',
    ai_sec: 'AI 安全',
    ai_tool: 'AI 提效'
  };

  var TOOLS = [
    {
      name: 'FOFA',
      sub: '网络空间测绘搜索引擎',
      url: 'https://fofa.info',
      cat: 'cyberspace',
      rank: 's',
      access: '免费注册 · 深度查询需会员',
      tags: ['资产测绘', '暴露面发现', '检索语法', '指纹识别'],
      desc: '白帽汇出品的网络空间测绘引擎，指纹规则库与检索语法强大，域名、证书、端口、组件皆可一句话定位，是国内红队资产收集与暴露面测绘的事实标准，配合 API 可批量拉取资产。'
    },
    {
      name: 'Shodan',
      sub: '万物互联搜索引擎',
      url: 'https://www.shodan.io',
      cat: 'cyberspace',
      rank: 's',
      access: '免费注册 · 进阶功能付费',
      tags: ['IoT 暴露', '工控协议', 'Banner 扫描', '全球测绘'],
      desc: '老牌全网设备搜索引擎，持续扫描全网端口并抓取服务 banner，长于发现 IoT、工控与数据库的意外暴露；Shodan Monitor 提供订阅式暴露面告警，是蓝军视角的资产巡逻兵。'
    }
  ];

  var RANK_CHAR = { s: '天', a: '地', b: '玄' };
  var RANK_LABEL = { s: '天字级 · 必备主力', a: '地字级 · 场景利器', b: '玄字级 · 备选兵器' };

  var grid = document.getElementById('tool-grid');
  if (!grid) return;
  var search = document.getElementById('tool-search');
  var chipsBox = document.getElementById('tool-chips');
  var empty = document.getElementById('tool-empty');
  var emptyText = document.getElementById('tool-empty-text');
  var state = { q: '', cat: '__all' };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function host(u) {
    try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return u; }
  }

  function renderChips() {
    var counts = {};
    TOOLS.forEach(function (t) { counts[t.cat] = (counts[t.cat] || 0) + 1; });
    var html = '<button class="chip active" data-cat="__all">全部 <i>' + TOOLS.length + '</i></button>';
    Object.keys(CATS).forEach(function (k) {
      html += '<button class="chip" data-cat="' + esc(k) + '">' + esc(CATS[k]) +
        (counts[k] ? ' <i>' + counts[k] + '</i>' : '') + '</button>';
    });
    chipsBox.innerHTML = html;
  }

  function matches(t) {
    if (state.cat !== '__all' && t.cat !== state.cat) return false;
    if (state.q) {
      var hay = [t.name, t.sub, t.desc, t.access, CATS[t.cat], (t.tags || []).join(' ')]
        .join(' ').toLowerCase();
      if (hay.indexOf(state.q.trim().toLowerCase()) === -1) return false;
    }
    return true;
  }

  function render() {
    var items = TOOLS.filter(matches);
    grid.innerHTML = items.map(function (t) {
      return '<a class="tool-card" href="' + esc(t.url) + '" target="_blank" rel="noopener" title="' + esc(RANK_LABEL[t.rank] || '') + '">' +
        '<div class="tool-head">' +
          '<span class="tool-rank ' + esc(t.rank) + '">' + (RANK_CHAR[t.rank] || '玄') + '</span>' +
          '<span class="tool-name">' + esc(t.name) + '</span>' +
          '<span class="tool-sub">' + esc(t.sub || '') + '</span>' +
          '<span class="tool-arrow">↗</span>' +
        '</div>' +
        '<p class="tool-desc">' + esc(t.desc) + '</p>' +
        '<div class="tool-tags">' + (t.tags || []).map(function (g) {
          return '<span class="mini-tag">' + esc(g) + '</span>';
        }).join('') + '</div>' +
        '<div class="tool-foot">' +
          '<span class="badge cat-badge">' + esc(CATS[t.cat] || '') + '</span>' +
          '<span class="tool-access">' + esc(t.access || '') + '</span>' +
          '<span class="tool-host">' + esc(host(t.url)) + '</span>' +
        '</div>' +
      '</a>';
    }).join('');

    var noMatch = items.length === 0;
    empty.hidden = !noMatch;
    if (noMatch) {
      emptyText.textContent = state.cat !== '__all'
        ? '「' + (CATS[state.cat] || '') + '」门类兵器整理入库中，敬请期待'
        : '没有匹配的兵器，换个关键词试试';
    }
  }

  if (search) {
    search.addEventListener('input', function () { state.q = search.value; render(); });
  }
  if (chipsBox) {
    chipsBox.addEventListener('click', function (e) {
      var b = e.target.closest('.chip');
      if (!b) return;
      chipsBox.querySelectorAll('.chip').forEach(function (c) { c.classList.remove('active'); });
      b.classList.add('active');
      state.cat = b.getAttribute('data-cat');
      render();
    });
  }

  renderChips();
  render();
})();
</script>
