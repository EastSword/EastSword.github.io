---
layout: default
title: 江湖留名
permalink: /wall/
---
<section id="wall">
  <div class="wrap">
    <div class="section-head">
      <div class="num">02 / GUESTBOOK</div>
      <h2>江湖留名</h2>
      <p class="desc">路过即缘分。以 GitHub 身份签下你的 ID 和一句话，签名实时上墙；路过他人的签名，也可以点个表情回应。</p>
    </div>
    <div class="wall-frame">
      <div class="wall-hint">
        GITHUB 留名 · 实时上墙 · 支持表情回应
        <a class="admin-link" href="https://github.com/EastSword/EastSword.github.io/discussions/1" target="_blank" rel="noopener" title="仓库所有者可在 GitHub 上删除不当签名">签名管理</a>
      </div>
      <div id="giscus-mount" class="giscus-mount"></div>
      <div class="wall-loading" id="wall-loading"><span class="glyph">墨</span><span>签名墙展开中…</span></div>
    </div>
  </div>
</section>

<script>
(function () {
  var mount = document.getElementById('giscus-mount');
  if (!mount) return;
  var loaded = false;

  function loadWall() {
    if (loaded) return;
    loaded = true;
    var s = document.createElement('script');
    s.src = 'https://giscus.app/client.js';
    s.async = true;
    s.crossOrigin = 'anonymous';
    s.setAttribute('data-repo', 'EastSword/EastSword.github.io');
    s.setAttribute('data-repo-id', 'R_kgDOINsDXg');
    s.setAttribute('data-category', 'General');
    s.setAttribute('data-category-id', 'DIC_kwDOINsDXs4DEYFm');
    s.setAttribute('data-mapping', 'specific');
    s.setAttribute('data-term', '江湖留名 · 粉丝签名墙');
    s.setAttribute('data-strict', '1');
    s.setAttribute('data-reactions-enabled', '1');
    s.setAttribute('data-emit-metadata', '0');
    s.setAttribute('data-input-position', 'top');
    s.setAttribute('data-theme', 'https://eastsword.github.io/assets/giscus-theme.css');
    s.setAttribute('data-lang', 'zh-CN');
    mount.appendChild(s);

    var timer = setInterval(function () {
      if (mount.querySelector('iframe')) {
        clearInterval(timer);
        var l = document.getElementById('wall-loading');
        if (l) l.remove();
      }
    }, 400);
    setTimeout(function () { clearInterval(timer); }, 30000);
  }

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      if (entries.some(function (e) { return e.isIntersecting; })) {
        io.disconnect();
        loadWall();
      }
    }, { rootMargin: '300px' });
    io.observe(mount);
  } else {
    loadWall();
  }
})();
</script>
