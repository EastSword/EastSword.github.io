(() => {
  const article = document.querySelector('.article');
  if (!article) return;
  const headings = [...article.querySelectorAll('.article-body h2, .article-body h3, .article-body h4')];
  if (!headings.length) return;
  const sidebar = article.querySelector('.article-jump-sidebar');
  const menu = sidebar.querySelector('details');
  const list = sidebar.querySelector('ol');
  const used = new Set([...document.querySelectorAll('[id]')].map(node => node.id));
  const links = headings.map((heading, index) => {
    if (!heading.id) {
      let id = 'article-section-' + (index + 1);
      while (used.has(id)) id += '-section';
      heading.id = id;
      used.add(id);
    }
    const item = document.createElement('li');
    item.className = 'level-' + heading.tagName.slice(1);
    const link = document.createElement('a');
    link.href = '#' + encodeURIComponent(heading.id);
    link.textContent = heading.textContent.trim();
    item.append(link);
    list.append(item);
    return link;
  });
  sidebar.hidden = false;
  article.classList.add('has-jump-navigation');
  const siteNav = document.querySelector('.nav');
  const measureNav = () => article.style.setProperty('--article-nav-offset', ((siteNav?.getBoundingClientRect().height || 76) + 12) + 'px');
  measureNav();
  if (siteNav) new ResizeObserver(measureNav).observe(siteNav);
  const desktop = matchMedia('(min-width: 1100px)');
  const adapt = () => { menu.open = desktop.matches; };
  adapt();
  desktop.addEventListener('change', adapt);
  list.addEventListener('click', event => {
    if (event.target.closest('a') && !desktop.matches) menu.open = false;
  });
  let pending = false;
  const highlight = () => {
    pending = false;
    let current = 0;
    headings.forEach((heading, index) => {
      if (heading.getBoundingClientRect().top <= 160) current = index;
    });
    links.forEach((link, index) => {
      if (index === current) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  };
  addEventListener('scroll', () => {
    if (!pending) { pending = true; requestAnimationFrame(highlight); }
  }, {passive: true});
  highlight();
})();
